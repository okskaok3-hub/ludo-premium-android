$ErrorActionPreference = 'Stop'
$standaloneApk = Join-Path $PSScriptRoot 'Ludo-King-LAN-Standalone.apk'
if (Test-Path -LiteralPath $standaloneApk) {
    adb install --no-incremental -r $standaloneApk
} else {
    $gameApks = @('base.apk', 'split_AddressablesAssetPack.apk', 'split_UnityDataAssetPack.apk', 'split_config.arm64_v8a.apk') | ForEach-Object { Join-Path $PSScriptRoot $_ }
    adb install-multiple --no-incremental -r @gameApks
}
if ($LASTEXITCODE -ne 0) { throw 'Game installation failed.' }
adb install -r (Join-Path $PSScriptRoot 'Local-Dice-Remote.apk')
if ($LASTEXITCODE -ne 0) { throw 'Remote installation failed.' }
adb shell am start -n com.ludo.king.lan/com.gametion.ludoking.LudoKingPlayerActivity
