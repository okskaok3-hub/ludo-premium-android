"""Verify colour controls on an already connected four-human Classic test match."""
import atexit,json,subprocess,time,urllib.request,urllib.error
from pathlib import Path
import frida,frida_tools
R=Path(__file__).resolve().parent.parent;OUT=R/'lan-release'
def adb(*args):return subprocess.check_output(['adb',*args],text=True).strip()
prior=adb('shell','settings','get','global','cached_apps_freezer')
def restore():
    if prior=='null':adb('shell','settings','delete','global','cached_apps_freezer')
    else:adb('shell','settings','put','global','cached_apps_freezer',prior)
atexit.register(restore);adb('shell','settings','put','global','cached_apps_freezer','disabled')
adb('shell','am','start','-n','com.ludo.king.lan/com.gametion.ludoking.LudoKingPlayerActivity');time.sleep(1)
adb('shell','am','start','-n','com.localdice.remote/local.dice.RemoteActivity');time.sleep(3)
session=frida.get_usb_device().attach(int(adb('shell','pidof','com.localdice.remote').split()[0]))
bridge=(Path(frida_tools.__file__).parent/'bridges/java.js').read_text(encoding='utf-8')
script=session.create_script(bridge+'''\nglobalThis.Java=bridge;
function activity(action){return new Promise(resolve=>Java.perform(()=>Java.choose('local.dice.RemoteActivity',{onMatch(a){Java.scheduleOnMainThread(()=>{try{resolve(action(a));}catch(e){resolve({error:e.toString()});}});},onComplete(){}})));}
rpc.exports={state(){return activity(a=>({busy:a.busy.value,connected:a.connected.value,winner:JSON.parse(a.winnerState.value.toString()),manualEnabled:a.sendButton.value.isEnabled()}));},choose(n){return activity(a=>{if(a.busy.value)return false;let b=Java.cast(a.colourButtons.value.get(n===0?4:n-1),Java.use('android.widget.Button'));if(!b.isEnabled())return false;b.performClick();return true;});}};
''');script.load()
config=json.loads((OUT/'controller-config.json').read_text())
def request(path='/status',body=None):
    data=json.dumps(body).encode() if isinstance(body,dict) else body
    req=urllib.request.Request('http://127.0.0.1:18765'+path,data=data,headers={'Authorization':'Bearer '+config['token']})
    try:
        with urllib.request.urlopen(req,timeout=4) as r:return r.status,json.load(r)
    except urllib.error.HTTPError as e:return e.code,json.load(e)
def choose(n):
    for attempt in range(12):
        if script.exports_sync.choose(n):break
        time.sleep(.5)
    else:raise AssertionError('Colour control unavailable')
    for attempt in range(16):
        time.sleep(.5);s=script.exports_sync.state()
        if s.get('connected') and s.get('winner',{}).get('selectedColour')==n and not s.get('busy'):break
    else:raise AssertionError(s)
    assert s['manualEnabled']==(n==0),s
    return s
initial=script.exports_sync.state();assert initial.get('winner',{}).get('activeColours')==[1,2,3,4],initial
results={}
try:
    for n in [1,2,3,4]:results[str(n)]=choose(n)
    assert request('/next',b'3')[0]==409
    assert request('/winner',{'colour':1,'matchId':'0000000000000000'})[0]==409
    assert request('/winner',{'colour':5,'matchId':initial['winner']['matchId']})[0]==400
    results['off']=choose(0);results['blue']=choose(1)
    adb('shell','screencap','-p','/sdcard/colour-control.png');adb('pull','/sdcard/colour-control.png',str(OUT/'colour-control.png'))
    results['manualRollRejectedDuringAssist']=True;results['staleMatchRejected']=True;results['invalidColourRejected']=True
    (OUT/'colour-ui-verification.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
finally:session.detach()
