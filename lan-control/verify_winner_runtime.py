"""Emulator integration on a fresh owned four-human Classic match with Blue assisted.

Moves each Blue token out normally, then stages its index two steps from home.
This is an endgame fixture, not evidence of a complete unmodified match.
"""
import json,subprocess,time
from pathlib import Path
import frida
R=Path(__file__).resolve().parent.parent;OUT=R/'lan-release'
def adb(*a):return subprocess.check_output(['adb',*a],text=True).strip()
adb('shell','am','start','-n','com.ludo.king.lan/com.gametion.ludoking.LudoKingPlayerActivity');time.sleep(1)
pid=int(adb('shell','pidof','com.ludo.king.lan').split()[0]);maps=adb('shell','su','0','cat',f'/proc/{pid}/maps')
base=next(l.split('-')[0] for l in maps.splitlines() if 'libil2cpp.so' in l and '00000000' in l and int(l.split('-')[1].split()[0],16)-int(l.split('-')[0],16)<0x2000000)
session=frida.get_usb_device().attach(pid)
script=session.create_script('''
const base=ptr('BASE');
function instance(slot,offset){return base.add(slot).readPointer().readPointer().add(0xb8).readPointer().add(offset).readPointer();}
const gc=instance(0x4e591d8,0x10), dc=instance(0x4e5afb0,0),gm=instance(0x4e59058,0x48);
rpc.exports={state(){let a=gc.add(0x520).readPointer(),positions=[];for(let i=0;i<28;i++)positions.push(a.add(0x20+i*4).readS32());let counts=gc.add(0x510).readPointer(),list=gc.add(0x3f0).readPointer(),items=list.add(0x10).readPointer(),winners=[];for(let i=0;i<list.add(0x18).readS32();i++)winners.push(items.add(0x20+i*4).readS32());return {turn:gc.add(0x548).readS32(),canDraw:gc.add(0x498).readU8(),dice:dc.add(0x20).readS32()^dc.add(0x24).readS32(),six:gc.add(0x570).readS32(),blueHomes:counts.add(0x24).readS32(),blueWon:gc.add(0x3e8).readPointer().add(0x21).readU8(),winners,invalid:gm.add(0x118).readU8(),positions};},stage(value){for(let i=4;i<8;i++){let p=gc.add(0x520).readPointer().add(0x20+i*4);if(p.readS32()!=56)p.writeS32(value);}return true;}};
'''.replace('BASE','0x'+base));script.load()
try:
    initial=script.exports_sync.state();assert initial['turn']==1 and initial['canDraw']==1 and not any(initial['positions']),initial
    steps=[]
    for count,(x,y) in enumerate([(206,1544),(386,1544),(206,1740),(386,1740)],1):
        script.exports_sync.stage(0)
        adb('shell','input','tap','403','2100');time.sleep(2);opening=script.exports_sync.state();assert opening['dice']==6 and opening['invalid']==0 and opening['turn']==1,opening
        adb('shell','input','tap',str(x),str(y));time.sleep(2);out=script.exports_sync.state();assert out['canDraw']==1 and out['turn']==1,out
        script.exports_sync.stage(54);adb('shell','input','tap','403','2100');time.sleep(3);home=script.exports_sync.state();assert home['dice']==2 and home['blueHomes']==count and home['invalid']==0,home
        steps.append({'opening':opening,'afterTokenOut':out,'afterHome':home})
    assert home['blueWon']==1 and home['winners'][0]==1,home
    result={'initial':initial,'tokens':steps,'firstPlaceVerified':True,'fixture':'Blue non-home token indices staged to 54 after each normal opening; unused base indices restored to 0 before the next opening. No home count, win flag or ranking was written. Original game processed movement and first place.','completeNaturalMatchTested':False,'physicalPhonesTested':False}
    (OUT/'winner-runtime-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
finally:session.detach()
