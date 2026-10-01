# Ludo King: how dice numbers work

For the deeper, all-human local Classic analysis, see [LOCAL_MODE_DEEP_DIVE.md](LOCAL_MODE_DEEP_DIVE.md). It traces pool construction and the exact order of the six rules.

Analyzed `com.ludo.king` **10.6.0.416**, versionCode 416, installed on `emulator-5554`, on 1 October 2026. Findings apply to this build.

## Result

The inspected local dice path uses **random selection plus state-dependent overrides**. It is not always an independent, equally likely choice of 1–6. The native code contains opening-six assistance, six drought counters, consecutive-six restrictions, tutorial scripting, and optional computer-mode adjustments. Online multiplayer receives a separate `iDiceValue` through a socket response. The server's number-generation algorithm is not contained in this APK.

These findings are based on actual ARM64 instructions mapped to Unity IL2CPP metadata, not just method names or diagnostic strings. Current runtime activation and remote configuration were not measured.

## Extraction

All four installed APKs were pulled again to `pulled/` and unpacked under `extracted/`:

| APK | Bytes |
|---|---:|
| base.apk | 100,270,629 |
| split_AddressablesAssetPack.apk | 49,866 |
| split_UnityDataAssetPack.apk | 126,397,559 |
| split_config.arm64_v8a.apk | 42,448,847 |

Their SHA-256 hashes match the existing workspace acquisition and are recorded in `acquisition.json`.

Main implementation: `extracted/split_config.arm64_v8a/lib/arm64-v8a/libil2cpp.so`.

Unity metadata: `extracted/base/assets/bin/Data/Managed/Metadata/global-metadata.dat`, version 31.

`tools/Il2CppDumper/dump.cs` contains recovered declarations and method addresses. Its empty method bodies are **not recovered C# source**. Annotated method bodies are saved as ARM64 disassemblies in `native-evidence/`.

## Initial random choice

`GameController.ActivateDice` normally constructs `NEW_DICE_LIST` from 1–6 and removes values using token-position checks. `DiceController.OnDiceRoll`, RVA `0x209D268`, has a separate empty-list fallback containing only 1–5. Its ordinary selection is equivalent to:

```text
index = floor(UnityEngine.Random.Range(0.0f, 1.0f) * NEW_DICE_LIST.Count)
value = NEW_DICE_LIST[index]
```

Evidence: `0x209D8C0–0x209D928` in `native-evidence/DiceController__OnDiceRoll.asm`.

The candidate list can change before selection. `Shuffle`, RVA `0x209E6A4`, randomly reorders it using integer `Random.Range`, removes 6 under a turn-counter condition, and includes a special branch that reduces it to a single 5 or 6. Thus, the list contents affect probabilities.

`GetDiceValue`, RVA `0x209E674`, simply reads stored `DICE_VALUE` through `ObscuredInt`. It does not generate a roll; ObscuredInt is the storage wrapper, not the RNG.

## Six rules

**Consecutive-six restriction:** when `GameController.totalSixValue == 2`, `OnDiceRoll` removes 6 from the list (`0x209D3CC–0x209D43C`). This is the consecutive-six counter at field offset `0x570`, not `TurnCounter`. The computer replacement routine likewise builds candidates 1–5 when its consecutive-six parameter is 2, otherwise 1–6.

**Six drought counter:** applicable local branches track `curRollCount` and `counterToGetSix`, with per-player arrays for local 2/3/4-player mode. A six resets the counter and chooses the next threshold using integer `Random.Range(8, 11)`: **8, 9, or 10**. When subsequent non-six rolls reach the threshold and the candidate list still contains 6, the code overwrites the chosen number with 6.

Evidence: `0x209DA34–0x209DABC`, `0x209DB14–0x209DBE0`, and `0x209DC60–0x209DD00` in `DiceController__OnDiceRoll.asm`. This is not a guarantee of six every ten rolls in all modes: mode gates, candidate availability, and later overrides still apply.

**Opening-six assistance:** `Awake`, RVA `0x209C1E4`, initializes per-player `maxLimit` values using integer `Random.Range(3, 7)`: **3 through 6**. Later branches use `b_myBlank`, `myBlank`, and equivalent player fields to replace a non-six with 6 once the opening counter reaches its limit. See `0x209DE78–0x209DF28` and corresponding later player branches. Counter initialization and comparison order matter; this does not establish an unconditional six on exactly roll 3–6 in every mode.

## Computer-mode adjustments

`OnDiceRoll` invokes adjustment only when `GameManager.b_isComVsMe` and `DiceController.assistMode` are true (`0x209E450–0x209E4C0`). `GetProbableDiceValue`, RVA `0x209EC1C`, leaves human turn 1 unchanged and invokes the computer routine for turns 2/3/4 only with `TOTAL_PALYERS == 2`.

`GetProbableDiceValueForLKComp`, RVA `0x20A1184`, performs these steps:

1. Builds candidates 1–5 after two consecutive sixes, otherwise 1–6.
2. Shuffles them and removes the original roll through `GetShuffleTempList`, RVA `0x20A1DD8`.
3. If three computer tokens are home and the last is at position 50 or later, a roll that lands exactly at position 56 is replaced by a random alternative (`0x20A17CC–0x20A1910`).
4. Removes candidate moves that would land on another computer token before the home path. It checks distinct token IDs and matches path-cell names. See `GetCompTokenDoublingDiceList`, RVA `0x20A1FE8`.
5. Checks whether the current computer move would land on an eligible human token. The human token must be out, not home, not on a checkpoint, and at position 50 or earlier. When destination cell names match, it chooses another candidate, removes that choice from the remaining candidates, and checks again (`0x20A19B8–0x20A1D88`).
6. Returns the original or replacement as appropriate. `OnDiceRoll` writes a changed result back into `DICE_VALUE` (`0x209E4E4–0x209E540`).

This can disadvantage the computer by avoiding captures, stacking, or a finishing move. It does not prove that a player is guaranteed to win.

## When assistance turns on

`GetCompModeLogicStatus`, RVA `0x20A2434`, loads the Ludo computer-assistance configuration and calls `AssistInfoConfig.IsActive`. Configuration fields include `isOnOff`, country inclusion/exclusion, `CW`, and `CL`.

`GameController.CheckCompAssitMode`, RVA `0x20C8B7C`, checks two-player mode and configuration activation. Within that enabled branch, its decision is:

```text
if consecutiveWins < config.CW:
    assistMode = true
else if consecutiveLosses < config.CL:
    assistMode = false
else:
    assistMode = true
    reset consecutive win/loss counters
```

The getters named `GetConsecutiveWinCount` and `GetConsecutiveLostCount` actually return configuration thresholds `CW` and `CL`. Recorded history comes from `GameProperties.LK_COMP_CONSECUTIVE_WON/LOST`.

The current numeric CW/CL values and activation state were not established. They must not be replaced with guessed thresholds.

## Tutorial

`OnDiceRoll` checks `IsTutorialShow` and `tutorialState` before ordinary random selection. Certain tutorial states select fixed dice-name entries (`0x209D834–0x209D974`). Tutorial rolls should not be treated as samples of ordinary dice probabilities.

## Online multiplayer

The normal online path runs through `SendMyDiceValueToServer` → `SocketCallManager.EmitMyDiceRoll` → `ThrowDiceLKOnEmit.EmitMyDiceRoll`, RVA `0x27791D8`.

Despite the first method's name, the inspected normal `throwDice` request builds a dictionary containing `iTurnCounter`, `_tableId`, and optional `bUndoAction`; that method does not send the locally selected dice number. It encrypts the dictionary and emits the socket event. Quick and kill modes use separate event names.

`ThrowDiceLKOnEmit.OnThrowDice`, RVA `0x2779540`, reads **`iDiceValue` from received data** and stores it in the socket manager (`0x2779690–0x27796E4`). This supports server-delivered online outcomes. It does not reveal whether the server generates, validates, or relays the number, nor its RNG or seed.

## What this establishes

- Applicable local/computer results depend on randomness, candidate lists, counters, token positions, configuration, and game history. A universal 1/6 probability cannot be assumed.
- No fixed repeatable sequence or tap-timing formula was established. This analysis does not provide a reliable next-roll predictor.
- The Unity engine's underlying PRNG implementation/state and online server algorithm were not recovered. No gameplay distribution or fairness measurement was performed.
- Purchase-related identifiers alone do not establish that paid dice change outcomes.
- `DiceControllerSNL` belongs to Snakes and Ladders; it is separate from the Ludo analysis.

## Verification and reproduction

Il2CppDumper 6.7.46 recovered CodeRegistration `0x4C2AEC8` and MetadataRegistration `0x4D7FD88`, then completed the dump and declaration generation. Its initial protection warning did not prevent recovery; its final console-key exception happened after output generation.

`analyze_native.py` unpacks the APKs, records hashes, maps method RVAs to ELF load segments, resolves metadata labels through ELF relocations, and writes Capstone ARM64 disassemblies. Optional arguments select extra method-name substrings. `assist-callers.json` records direct branch references to assistance getters. Labels are navigation aids; documented conditions were checked against instructions and field offsets in `dump.cs`.

Validation: all four APK hashes match the previous acquisition; mapped addresses contain coherent ARM64 instructions and calls consistent with their metadata signatures. This was static native-code verification, not a live execution trace. No APK patches or multiplayer manipulation were performed.
