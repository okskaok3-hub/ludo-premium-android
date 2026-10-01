import json, subprocess, time, hashlib, urllib.request, urllib.error, atexit
from pathlib import Path
import frida,frida_tools
R=Path(__file__).resolve().parent.parent;OUT=R/'lan-release'
def adb(*args):return subprocess.check_output(['adb',*args]).decode(errors='replace')
# Both apps share one emulator during instrumentation; restore this setting on exit.
prior_freezer=adb('shell','settings','get','global','cached_apps_freezer').strip()
def restore_freezer():
    if prior_freezer=='null':adb('shell','settings','delete','global','cached_apps_freezer')
    else:adb('shell','settings','put','global','cached_apps_freezer',prior_freezer)
atexit.register(restore_freezer)
adb('shell','settings','put','global','cached_apps_freezer','disabled')
def foreground(package,activity):adb('shell','am','start','-n',package+'/'+activity)
def screenshot(name):
    adb('shell','screencap','-p','/sdcard/'+name+'.png');adb('pull','/sdcard/'+name+'.png',str(OUT/(name+'.png')))
foreground('com.ludo.king.lan','com.gametion.ludoking.LudoKingPlayerActivity');time.sleep(2)
adb('shell','am','force-stop','com.localdice.remote')
foreground('com.localdice.remote','local.dice.RemoteActivity');time.sleep(.8);screenshot('premium-scanner');time.sleep(.7);screenshot('premium-scanner-frame2');time.sleep(5)
pid=int(adb('shell','pidof','com.localdice.remote').split()[0]);session=frida.get_usb_device().attach(pid)
source=r'''
function activity(action){return new Promise(resolve=>Java.perform(()=>Java.choose('local.dice.RemoteActivity',{onMatch(a){Java.scheduleOnMainThread(()=>{try{resolve(action(a));}catch(e){resolve({error:e.toString()});}});},onComplete(){}})));}
rpc.exports={
 state(){return activity(a=>{let list=[],it=a.found.value.values().iterator();while(it.hasNext()){let d=Java.cast(it.next(),Java.use('local.dice.RemoteActivity$Device'));list.push({id:d.id.value,name:d.name.value,address:d.address.value,relay:d.relay.value});}return{page:a.page.value,devices:list,status:a.status.value?a.status.value.getText().toString():null,connected:a.connected.value,pending:a.pending.value,busy:a.busy.value,selected:a.selected.value,sendEnabled:a.sendButton.value?a.sendButton.value.isEnabled():false,button:a.sendButton.value?a.sendButton.value.getText().toString():null};});},
 choose(){return activity(a=>{a.devices.value.getChildAt(0).performClick();return true;});},
 select(){return activity(a=>{Java.cast(a.diceButtons.value.get(1),Java.use('android.view.View')).performClick();return true;});},
 queue(){return activity(a=>{a.sendButton.value.performClick();return true;});},
 refresh(){return activity(a=>{a.send('GET','/status',null,false);return true;});},
 back(){return activity(a=>{a.onBackPressed();return true;});},
 scan(){return activity(a=>{a.scan();return true;});}
};
'''
bridge=(Path(frida_tools.__file__).parent/'bridges/java.js').read_text(encoding='utf-8')
script=session.create_script(bridge+'\nglobalThis.Java=bridge;\n'+source);script.load()
results=script.exports_sync.state();print('Results:',json.dumps(results,indent=2));assert results['page']==1;assert len(results['devices'])==1,results;assert results['devices'][0]['relay'];screenshot('premium-devices')
foreground('com.localdice.remote','local.dice.RemoteActivity');time.sleep(.5);script.exports_sync.choose();time.sleep(2)
control=script.exports_sync.state();print('Control:',json.dumps(control,indent=2));assert control['page']==2;assert control['connected'];assert control['sendEnabled'] or control['pending']
config=json.loads((OUT/'controller-config.json').read_text())
def request(path='/status',body=None,auth=True):
    req=urllib.request.Request('http://127.0.0.1:18765'+path,data=body,headers={'Authorization':'Bearer '+config['token']} if auth else {})
    try:
        with urllib.request.urlopen(req,timeout=4) as response:return response.status,json.load(response)
    except urllib.error.HTTPError as e:return e.code,json.load(e)
assert request(auth=False)[0]==401
script.exports_sync.select();selection=script.exports_sync.state();assert selection['selected']==2
if not control['pending']:
    assert not request()[1]['pending'],'Selecting a tile must not send the command'
    script.exports_sync.queue();time.sleep(2);queued=script.exports_sync.state();print('Queued:',json.dumps(queued,indent=2));assert queued['pending'] and not queued['sendEnabled'];assert request()[1]['pending'];assert request('/next',b'5')[0]==409
    adb('shell','su','0','rm','-f','/data/user/0/com.ludo.king.lan/files/nextdice')
    script.exports_sync.refresh();time.sleep(2);assert script.exports_sync.state()['sendEnabled']
else:queued={'skipped':'An existing pending command was preserved'}
foreground('com.localdice.remote','local.dice.RemoteActivity');time.sleep(.5);screenshot('premium-control')
script.exports_sync.back();back=script.exports_sync.state();assert back['page']==1;assert len(back['devices'])==1
script.exports_sync.choose();time.sleep(2);assert script.exports_sync.state()['connected']
result={'deviceList':results,'connectedScreen':control,'queued':queued,'backNavigation':back,'unauthorizedStatus':401,'selectionDoesNotSend':True,'physicalPhonesTested':False,'testEnvironment':'Both apps on one emulator, with cached-app freezing temporarily disabled and restored after testing','companionSha256':hashlib.sha256((OUT/'Local-Dice-Remote.apk').read_bytes()).hexdigest()}
(OUT/'premium-ui-verification.json').write_text(json.dumps(result,indent=2));(OUT/'discovery-verification.json').write_text(json.dumps(result,indent=2));session.detach()
