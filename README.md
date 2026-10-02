# Local Dice LAN 4.0

Android companion with a colour picker and local Classic dice assistance. Select Blue, Red, Green or Yellow on the connected control screen. The selected colour receives opening sixes, useful advances and exact home rolls; players move their tokens normally and the original game awards first place. The picker is Android only. The iPhone companion retains manual number control.

## Downloads and installation

Download **Ludo-King-LAN-Standalone.apk** for the game phone and **Local-Dice-Remote.apk** for the controller from [v4.0](https://github.com/okskaok3-hub/ludo-premium-android/releases/tag/v4.0). Update both apps together. The standalone game installs as one normal APK. **Ludo-King-LAN-v4.0.zip** includes both APKs, matching controller configuration, relay, install scripts and current verification records.

Both devices must share reachable Wi-Fi, or the controller can join the game phone's hotspot. Keep the game open. For an emulator, run `Start-LanRelay.ps1` on its host; update and restart an older relay. Internet is not required. Detailed instructions and API details are in [the release guide](lan-release/README.md).

## Colour assistance

Start Classic Pass N Play with 2–4 human players, connect the Android companion and choose a participating colour. Manual number sending is disabled while assistance is active. **Use normal rolls** switches it off. The selection belongs to the current match; new matches and process restarts clear it. First place is detected on the next roll and clears assistance for the remaining players. Team Up, Quick, computer/bot games, 5/6-player games and online play are excluded.

## Interface

| Scanner | Devices | Dice and colour control |
| --- | --- | --- |
| ![Scanner](docs/screenshots/scanner.png) | ![Devices](docs/screenshots/devices.png) | ![Control](docs/screenshots/control.png) |

## Source and builds

`lan-control/` contains Java UI and bridge sources, freestanding ARM64 C and assembly patches, build scripts, relay and verification utilities. Original APKs, controller credentials and signing keys are outside Git. Release packages contain the matching controller configuration.

Builds target Windows with Android SDK platform 35, build-tools 36.0.0, NDK 30.0.14904198, Java tooling, Python, capstone, pyelftools and Apktool. Update machine-specific paths for another workstation. Supply original version 10.6.0.416 APK splits under `pulled/` and extracted `extracted/split_config.arm64_v8a/lib/arm64-v8a/libil2cpp.so`. Run `python lan-control/build.py`, `python lan-control/build_remote.py`, then `python lan-control/build_standalone.py`. Retain the local signing key and controller configuration to update existing installations.

## Verification

The final standalone APK hash matches the sole installed game APK. All four Android colour buttons, Off, stale-match rejection and conflicting manual-send rejection passed. Scanner deduplication, navigation and manual number controls passed on the matching companion.

The emulator awarded Blue first place after all four original home moves in a staged endgame fixture. Only token position indices were staged; the game processed movement, home counts and rankings. A complete unstaged match remains untested. The actual C decision passed 13 host cases, including all six opponent finishing distances; opponent-endgame runtime integration remains untested. New-match, next-roll first-place detection and process-restart resets passed. See `lan-release/standalone-verification.json` and the winner reports.

Physical Android game devices and hotspot combinations remain untested. The user reported iPhone discovery working on Wi-Fi; the installed IPA revision is unconfirmed. The game copy uses the separate package `com.ludo.king.lan`; online guest login is disabled.
