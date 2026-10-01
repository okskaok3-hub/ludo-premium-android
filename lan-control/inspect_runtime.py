import frida,json,subprocess
pid=int(subprocess.check_output(['adb','shell','pidof','com.ludo.king.lan']).split()[0])
maps=subprocess.check_output(['adb','shell','su','0','cat',f'/proc/{pid}/maps'],text=True)
base=next(l.split('-')[0] for l in maps.splitlines() if 'libil2cpp.so' in l and '00000000' in l and int(l.split('-')[1].split()[0],16)-int(l.split('-')[0],16)<0x2000000)
session=frida.get_usb_device().attach(pid)
code="""
const base=ptr('BASE');
const t=base.add(0x4e59058).readPointer().readPointer();
const gm=t.add(0xb8).readPointer().add(0x48).readPointer();
console.log('base',base,'gm',gm,'invalid',gm.add(0x118).readU8(),'panel',gm.add(0x110).readPointer());
console.log('startup',hexdump(base.add(0x2104a3c),{length:4}));
console.log('popup',hexdump(base.add(0x2104ce0),{length:16}));
""".replace('BASE','0x'+base)
script=session.create_script(code)
script.on('message',lambda m,d:print(m))
script.load()
session.detach()
