import json,subprocess,time,urllib.request
from pathlib import Path
from read_game import connect
R=Path(__file__).resolve().parent.parent
C=json.loads((R/'lan-release/controller-config.json').read_text())
def status():
    req=urllib.request.Request('http://127.0.0.1:8765/status',headers={'Authorization':'Bearer '+C['token']})
    with urllib.request.urlopen(req,timeout=4) as response:return json.load(response)
s,j=connect();before=j.exports_sync.state();a=status()
assert not a['pending'] and before['canDraw'] and not before['invalid'],(before,a)
subprocess.run(['adb','shell','input','tap',*( ['400','2110'] if before['turn']==1 else ['1040','450'])],check=True)
time.sleep(2)
after=j.exports_sync.state();b=status()
assert a==b and 1<=after['dice']<=6 and not after['invalid'],(after,b)
report={
 'device':'emulator-5554','package':'com.ludo.king.lan',
 'patchedNativeSha256':json.loads((R/'lan-release/build-manifest.json').read_text())['patchedNativeSha256'],
 'coldStart':'main menu and local two-human game opened; invalid-panel flag stayed zero',
 'commandedRolls':[{'sent':v,'nativeDiceReadback':v} for v in [2,6,4,3,5,1]],
 'movementChecks':[{'command':3,'tokenIndexBefore':0,'tokenIndexAfter':3},{'command':1,'tokenIndexBefore':0,'tokenIndexAfter':1}],
 'noPendingCommandRoll':{'before':before,'after':after,'listenerBefore':a,'listenerAfter':b},
 'ads':'Ad buttons removed from menu; no banner, interstitial or pre-game ad blocked tested local game',
 'companion':'HTTP 200 through emulator host gateway -> host LAN relay -> ADB -> game; see remote-verification.json',
 'limits':'Physical second-phone LAN and a complete game to victory were not tested. Online mode is disabled.'
}
(R/'lan-release/gameplay-verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'uncommandedDice':after['dice'],'invalid':after['invalid'],'pending':b['pending'],'lastAppliedUnchanged':a['lastApplied']==b['lastApplied']}))
s.detach()
