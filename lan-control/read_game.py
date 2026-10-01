import frida,json,subprocess
def connect():
    pid=int(subprocess.check_output(['adb','shell','pidof','com.ludo.king.lan']).split()[0])
    maps=subprocess.check_output(['adb','shell','su','0','cat',f'/proc/{pid}/maps'],text=True)
    base=next(l.split('-')[0] for l in maps.splitlines() if 'libil2cpp.so' in l and '00000000' in l and int(l.split('-')[1].split()[0],16)-int(l.split('-')[0],16)<0x2000000)
    session=frida.get_usb_device().attach(pid)
    code="""
    const base=ptr('BASE');
    function instance(slot,offset){ return base.add(slot).readPointer().readPointer().add(0xb8).readPointer().add(offset).readPointer(); }
    rpc.exports={ state(){
      const gm=instance(0x4e59058,0x48), gc=instance(0x4e591d8,0x10), dc=instance(0x4e5afb0,0);
      const a=gc.add(0x520).readPointer(); const size=a.add(0x18).readU32();
      const positions=[];for(let i=0;i<Math.min(size,80);i++)positions.push(a.add(0x20+i*4).readS32());
      const name=dc.add(0xb0).readPointer();
      return {invalid:gm.add(0x118).readU8(),turn:gc.add(0x548).readS32(),canDraw:gc.add(0x498).readU8(),dice:dc.add(0x20).readS32()^dc.add(0x24).readS32(),diceName:name.isNull()?null:name.add(0x14).readUtf16String(name.add(0x10).readS32()),positions};
    }};
    """.replace('BASE','0x'+base)
    script=session.create_script(code);script.load()
    return session,script
if __name__=='__main__':
    session,script=connect();print(json.dumps(script.exports_sync.state()));session.detach()
