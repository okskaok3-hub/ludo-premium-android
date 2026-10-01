# Ludo King LAN local-play build

Game package: `com.ludo.king.lan`, displayed as **Ludo King LAN**. Companion package: `com.localdice.remote`, displayed as **Local Dice Remote**. Game version: 10.6.0.416, ARM64, Android 7.0/API 24 or newer, primary Android user profile.

This is a separate local-play copy. The original `com.ludo.king` installation and its saved data remain separate. The startup identity guard has been bypassed for this development package. Automatic online guest login and profile requests are disabled: the guest-login HTTP 403 callback was the second source of the tamper warning.

Ad requests, displays, rewarded video offers, in-house ad popups and the local remove-ads promotion are disabled. Ad callbacks report unavailable, so they do not award ad rewards. Ad SDK startup providers are removed. Paid inventory and features are not unlocked. The pre-game ad offer continues into ordinary local play automatically.

## Install

**Recommended:** Install `Ludo-King-LAN-Standalone.apk` directly as a normal APK. It contains the base application, both asset packs and the ARM64 libraries, so no split installer is needed. Install `Local-Dice-Remote.apk` separately on the controlling phone.

The original four-split format remains available. Install all four together; installing its `base.apk` alone is insufficient. `LudoKing-LAN-Control.apks` is a ZIP containing these four splits, suitable for a compatible split-APK installer.

For the connected emulator, run `Install-Emulator.ps1` with ADB on PATH. It installs the standalone APK when present, otherwise the four game splits, followed by the companion, then launches the game. For a second physical phone, install `Local-Dice-Remote.apk` there.

## Send the next number

1. Open **Ludo King LAN** and start local pass-and-play with human players.
2. Open **Local Dice Remote** on the controlling phone.
3. Opening the companion starts a full-screen animated five-second scan.
4. Tap a device card to open its separate dice-control page. Wait for **Connected**.
5. Select a number from 1 through 6, then press **Send number**. Selecting a tile updates the dice preview without sending a command.
6. Roll the next dice in the game. That command is consumed once. Subsequent rolls use the existing game logic unless another number is queued.

One number can be pending at a time. The send button waits while a command is pending and becomes available when automatic status refresh confirms it was consumed. Another command receives HTTP 409 until the first command is consumed. Commands are accepted only with the access token. The override is gated to the local mode flag and human player slot. A pending command survives restarting the game until it is consumed; it is not a queue of commands for multiple turns. Back or **Change** returns to device selection; **Scan again** starts a new scan.

This companion includes the matching development-build token, so ordinary connection needs no typing. Anyone with this companion APK can control matching builds on a reachable network. Discovery does not publish the token. For a different build or blocked Wi-Fi broadcast, use **Connect manually** on the device page, enter `IP:8765` and the token from that build's `controller-config.json`, then press **Connect**.

The scanner discovers only running copies of **Ludo King LAN** advertising this protocol. It cannot inspect installed APKs on arbitrary nearby phones, discover the original game, or connect over Bluetooth. Device entries show the Android device name (model as fallback) and its address. Scan again after changing Wi-Fi or reopening the game.

## Emulator on the host's LAN

The Android emulator's private IP generally cannot be reached directly from another phone. On the host, run `Start-LanRelay.ps1` and leave that terminal open. It establishes ADB forwarding, relays commands on TCP 8765, and answers discovery on UDP 8766 using the game's own installation ID and device name. The emulator and relay therefore appear as one game entry. The companion prefers the relay route when both are seen. If discovery is blocked, use the host computer's Wi-Fi/Ethernet IPv4 address and `:8765` manually. Restart an older running relay after updating these files.

Both devices must be on a network that permits communication between clients. If Windows Firewall blocks the relay, allow the Python relay on the private network for TCP 8765 and UDP 8766. The relay does not alter firewall rules automatically. Guest Wi-Fi/client isolation can block both discovery and commands.

Discovery uses a five-second UDP broadcast scan on port 8766. Each response echoes a random scan nonce and provides a stable installation ID, device name and control port. Duplicate network-interface and relay replies are merged. The companion verifies the authenticated `/status` response before enabling sending. Technical addresses and access tokens are kept in manual connection settings. No internet service is used.

## Interface for another APK or script

Send HTTP `POST /next`, with a one-byte plain-text body `1` through `6`, to port 8765. Include `Authorization: Bearer YOUR_TOKEN` and the correct Content-Length. `GET /status` uses the same authorization header.

```text
POST http://GAME_OR_HOST_IP:8765/next
Authorization: Bearer YOUR_TOKEN
Content-Type: text/plain

6
```

A successful response is `{"queued":6,"appliesTo":"next local roll"}`. Status reports whether a command is pending and the last value applied by the native hook. Android HTTP clients targeting modern Android must permit cleartext HTTP for this LAN connection, as the supplied companion does.

## Behavior and limitations

The native patch replaces both the stored ObscuredInt dice result and its dice-name entry before starting the existing animation. The existing movement code reads that stored result. Without a pending command, the hook returns to the original roll path without changing its result. The existing consecutive-six counter is updated afterward using the final value. Commanded sixes also clear the player's drought counter and set its opening-six flag.

Other assistance counters have already evaluated the preliminary result before an override, so forcing numbers can affect later counter history. Existing extra-turn, capture, and three-sixes gameplay handling still applies. This does not directly select a winner.

This package and development signature are intended for local pass-and-play. Online login and profile flow are disabled. The LAN override excludes computer and online turns. Ad-dependent optional actions cannot earn rewards. Purchases and other modes have not been validated. Physical-device LAN operation needs a reachable Wi-Fi network; emulator verification uses ADB forwarding and a host relay.

Build sources are in `../lan-control/`. `build-manifest.json` records SHA-256 hashes; `behavior-patches.json` records original and replacement instructions for startup and ad changes. `http-verification.json` records listener checks. `premium-ui-verification.json` records emulator discovery deduplication, screen navigation, selection, authenticated connection, queuing and pending-button checks. Screen previews are `premium-scanner.png`, `premium-devices.png` and `premium-control.png`. Physical phones have not been tested. Gameplay verification is recorded separately after emulator testing.

`standalone-manifest.json` records the merged APK and its checksum. `standalone-verification.json` records a one-APK install, startup and local-board loading, companion checks, and a commanded six read back from the runtime. The native library matches the tested split build byte for byte. Existing app data was retained during the emulator update.
