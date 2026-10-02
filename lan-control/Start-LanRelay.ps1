$ErrorActionPreference = 'Stop'
adb forward tcp:18765 tcp:8765
if ($LASTEXITCODE -ne 0) { throw 'ADB forwarding failed. Connect the emulator first.' }
Write-Host 'Use this computer Wi-Fi/Ethernet IPv4 address and port 8765 in Local Dice Remote.'
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254.*' } | Select-Object InterfaceAlias,IPAddress
python "$PSScriptRoot\lan_relay.py"
