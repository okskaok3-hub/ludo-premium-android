import hashlib, json, os, secrets, shutil, struct, subprocess, sys, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'lan-control'
WORK = ROOT / 'lan-build'
OUT = ROOT / 'lan-release'
SDK = Path(os.environ['LOCALAPPDATA']) / 'Android/Sdk'
BT = SDK / 'build-tools/36.0.0'
NDK = SDK / 'ndk/30.0.14904198/toolchains/llvm/prebuilt/windows-x86_64/bin'
APKTOOL = Path('C:/Users/user/Downloads/Telegram Desktop/apktool_2.12.0.jar')
ANDROID = '{http://schemas.android.com/apk/res/android}'
ET.register_namespace('android', 'http://schemas.android.com/apk/res/android')
sys.path.insert(0, str(ROOT / 'tools/python'))
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN

def run(*args):
    print('Running:', Path(str(args[0])).name, *map(str, args[1:3]), flush=True)
    subprocess.run(list(map(str,args)), check=True)

WORK.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
config = SRC / 'controller-config.json'
if not config.exists():
    config.write_text(json.dumps({'package':'com.ludo.king.lan','port':8765,'token':secrets.token_hex(24)},indent=2))
settings = json.loads(config.read_text())

# Compile the bootstrapping provider into an additional dex without touching original classes.
java_source = WORK / 'java/local/dice/LanBootstrap.java'
java_source.parent.mkdir(parents=True,exist_ok=True)
java_source.write_text((SRC/'src/local/dice/LanBootstrap.java').read_text().replace('TOKEN_REPLACED_AT_BUILD',settings['token']))
classes = WORK/'classes'; classes.mkdir(exist_ok=True)
run('javac','-source','8','-target','8','-classpath',SDK/'platforms/android-35/android.jar','-d',classes,java_source)
dex = WORK/'dex'; dex.mkdir(exist_ok=True)
run('java','-cp',BT/'lib/d8.jar','com.android.tools.r8.D8','--min-api','24','--lib',SDK/'platforms/android-35/android.jar','--output',dex,*classes.rglob('*.class'))

# Add one RX segment by replacing the nonessential PT_NOTE program header.
original = ROOT/'extracted/split_config.arm64_v8a/lib/arm64-v8a/libil2cpp.so'
with original.open('rb') as stream:
    elf = ELFFile(stream)
    segments = [dict(s.header) for s in elf.iter_segments()]
    phoff, phsize = elf['e_phoff'], elf['e_phentsize']
loads = [s for s in segments if s['p_type']=='PT_LOAD']
align = lambda n: (n+16383) & ~16383
va = align(max(s['p_vaddr']+s['p_memsz'] for s in loads))
offset = align(original.stat().st_size)
run(NDK/'clang.exe','--target=aarch64-linux-android24','-c',SRC/'hook.S','-o',WORK/'hook.o')
run(NDK/'ld.lld.exe','-Ttext='+hex(va),'--defsym=gamemanager_slot=0x4e59058','--defsym=gamecontroller_slot=0x4e591d8','--defsym=encode_int=0x1fc9b3c','--defsym=get_game_object=0x494ee44','--defsym=set_active=0x4951a2c','--defsym=dismiss_local_offer=0x2586c58','--oformat=binary',WORK/'hook.o','-o',WORK/'hook.bin')
with (WORK/'hook.o').open('rb') as f:
    hook_symbols = {s.name:va+s['st_value'] for s in ELFFile(f).get_section_by_name('.symtab').iter_symbols() if s.name.startswith(('hide_','dismiss_local_ad_'))}
stub = (WORK/'hook.bin').read_bytes()
raw = bytearray(original.read_bytes())
site = 0x209e544
segment = next(s for s in loads if s['p_vaddr'] <= site < s['p_vaddr']+s['p_filesz'])
site_offset = segment['p_offset'] + site - segment['p_vaddr']
assert raw[site_offset:site_offset+4] == bytes.fromhex('e00313aa'), 'Unexpected patch instruction'
delta = va - site
assert delta % 4 == 0 and -(1<<27) <= delta < (1<<27)
raw[site_offset:site_offset+4] = struct.pack('<I',0x94000000 | ((delta//4)&0x3ffffff))
# The independent package/signature cannot pass the original startup identity guard.
# Keep startup initialization, then enter its normal main-menu continuation.
startup_site, startup_continue = 0x2104a3c, 0x2104b6c
startup_segment = next(s for s in loads if s['p_vaddr'] <= startup_site < s['p_vaddr']+s['p_filesz'])
startup_offset = startup_segment['p_offset'] + startup_site - startup_segment['p_vaddr']
assert raw[startup_offset:startup_offset+4] == bytes.fromhex('e0031faa'), 'Unexpected startup guard instruction'
struct.pack_into('<I',raw,startup_offset,0x14000000 | (((startup_continue-startup_site)//4)&0x3ffffff))
note_index = next(i for i,s in enumerate(segments) if s['p_type']=='PT_NOTE')
patches = []
def patch(rva, code, reason):
    seg = next(s for s in loads if s['p_vaddr'] <= rva < s['p_vaddr']+s['p_filesz'])
    pos = seg['p_offset'] + rva-seg['p_vaddr']
    patches.append({'rva':hex(rva),'reason':reason,'before':raw[pos:pos+len(code)].hex(),'after':code.hex()})
    raw[pos:pos+len(code)] = code
def words(*ops): return struct.pack('<'+'I'*len(ops),*ops)
def branch(site,target,link=False): return (0x94000000 if link else 0x14000000)|(((target-site)//4)&0x3ffffff)
run(NDK/'clang.exe','--target=aarch64-linux-android24','-c',SRC/'menu.S','-o',WORK/'menu.o')
run(NDK/'ld.lld.exe','-Ttext=0x2104ce0','--defsym=get_game_object=0x494ee44','--defsym=set_active=0x4951a2c','--defsym=load_main_menu=0x21057fc','--defsym=init_ads=0x2103d0c','--oformat=binary',WORK/'menu.o','-o',WORK/'menu.bin')
patch(0x2104ce0,(WORK/'menu.bin').read_bytes(),'Close startup warning panel and load menu')
patch(0x2104b94,words(branch(0x2104b94,0x2104ce0,True),branch(0x2104b98,0x2104ba8)),'Open menu without startup advertisement coroutine')
ret = words(0xd65f03c0)
false = words(0x52800000,0xd65f03c0)
for rva in [0x21beec0,0x21c0390,0x23a9f44]:
    patch(rva,ret,'Disable online authentication and profile requests in local build')
patch(0x2285b18,false,'Use offline game flow while Java LAN listener stays available')
patch(0x2281cf8,words(0xb9000000|(9<<10)|(19<<5)|31),'Ignore stale local cracked preference')
patch(0x22a3164,false,'Hide rewarded video button')
for rva in [0x226a110,0x226a51c]: patch(rva,false,'Hide rewarded video availability')
patch(0x2476d88,false,'Disable local remove-ads promotional popup')
patch(0x2585a88,words(branch(0x2585a88,hook_symbols['dismiss_local_ad_offer'])),'Continue ordinary local play past pre-game ad offer')
for rva in [0x22a2590,0x22a2818,0x22a2b1c]:
    patch(rva,words(branch(rva,hook_symbols['hide_gems_ads'])),'Hide rewarded gems button and strip')
patch(0x226994c,words(branch(0x226994c,hook_symbols['hide_coins_ads'])),'Hide rewarded coins and timer buttons')
for rva,target in [(0x206d984,0x206e0a0),(0x206d230,0x206e0a0),(0x256f0b8,0x256efbc),(0x256e7e8,0x256efbc),(0x26b76e0,0x26b76b8)]:
    patch(rva,words(branch(rva,target)),'Hide advertisement or rewarded video promotion')
patch(0x267b6cc,words(0x52800028,0x39000008|(0xc1<<10),0x39000008|(0xf2<<10),0xd65f03c0),'Mark ad initialization complete without initializing ad SDKs')
for rva in [0x267c26c,0x267ca1c,0x267f914,0x267fb7c,0x26807c8,0x26808b8,0x26808bc,0x2283dc8,0x2284204,0x228419c,0x216ad90]:
    patch(rva,ret,'Disable advertisement request or display')
for rva in [0x267e0a8,0x267fe90,0x26804f0,0x2176d5c,0x21775a8,0x2177718]:
    patch(rva,false,'Report advertisement unavailable or stop promotional popup coroutine')
for rva,reg,invoke,status in [(0x267e178,1,0x267b0dc,3),(0x267e3d4,2,0x267b0dc,3),(0x267e5ec,2,0x267b0dc,3),(0x267e7b8,2,0x267b0dc,10),(0x267f24c,1,0x267b180,3),(0x267f44c,1,0x267b180,3),(0x267295c,1,0x267b180,10),(0x267f574,1,0x267b180,10)]:
    patch(rva,words(0xb4000000|(5<<5)|reg,0xaa0003e0|(reg<<16),0x52800001|(status<<5),0xaa1f03e2,branch(rva+16,invoke),0xd65f03c0),'Complete ad callback with unavailable status')
(OUT/'behavior-patches.json').write_text(json.dumps(patches,indent=2))
struct.pack_into('<IIQQQQQQ',raw,phoff+note_index*phsize,1,5,offset,va,va,len(stub),len(stub),16384)
raw.extend(b'\0'*(offset-len(raw))); raw.extend(stub)
patched = WORK/'libil2cpp.so'; patched.write_bytes(raw)
disasm = Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
(OUT/'native-hook.asm').write_text('\n'.join(f'{i.address:08x}: {i.mnemonic} {i.op_str}' for i in disasm.disasm(stub,va)))

for apk in (ROOT/'pulled').glob('*.apk'):
    directory = WORK/apk.stem
    marker = directory/'.lan-manifest-modified'
    if not directory.exists():
        run('java','-jar',APKTOOL,'d','-s','-f',apk,'-o',directory)
    if not marker.exists():
        manifest = directory/'AndroidManifest.xml'
        text = manifest.read_text(encoding='utf-8').replace('com.ludo.king','com.ludo.king.lan')
        tree = ET.fromstring(text)
        application = tree.find('application')
        if apk.name=='base.apk':
            application.set(ANDROID+'label','Ludo King LAN')
            application.set(ANDROID+'extractNativeLibs','true')
            for provider in application.findall('provider'):
                authority = provider.get(ANDROID+'authorities')
                if authority and not authority.startswith('com.ludo.king.lan'):
                    provider.set(ANDROID+'authorities',';'.join(a+'.lan' for a in authority.split(';')))
            ET.SubElement(application,'provider',{
                ANDROID+'name':'local.dice.LanBootstrap',
                ANDROID+'authorities':'com.ludo.king.lan.localdice',
                ANDROID+'exported':'false',
                ANDROID+'initOrder':'100',
            })
        ET.ElementTree(tree).write(manifest,encoding='utf-8',xml_declaration=True)
        marker.write_text('Modified independent local package')
    if apk.name=='base.apk':
        manifest = directory/'AndroidManifest.xml'
        tree = ET.parse(manifest)
        application = tree.getroot().find('application')
        ad_providers = {'com.google.android.gms.ads.MobileAdsInitProvider','com.applovin.sdk.AppLovinInitProvider','com.facebook.ads.AudienceNetworkContentProvider','com.vungle.ads.VungleProvider','com.mbridge.msdk.config.component.status.MBComponentLifecycleProvider'}
        for provider in list(application.findall('provider')):
            if provider.get(ANDROID+'name') in ad_providers: application.remove(provider)
            else:
                for metadata in list(provider.findall('meta-data')):
                    if metadata.get(ANDROID+'name')=='com.unity3d.services.core.configuration.AdsSdkInitializer': provider.remove(metadata)
        tree.write(manifest,encoding='utf-8',xml_declaration=True)
    if apk.name=='base.apk':
        shutil.copyfile(dex/'classes.dex',directory/'classes8.dex')
    if apk.name=='split_config.arm64_v8a.apk':
        shutil.copyfile(patched,directory/'lib/arm64-v8a/libil2cpp.so')
    unsigned = WORK/(apk.stem+'-unsigned.apk')
    if apk.name=='base.apk':
        run('java','-jar',APKTOOL,'b',directory,'-o',unsigned)
    else:
        # Apktool's resource-free split build omits the framework include.
        compiled = WORK/(apk.stem+'-manifest.apk')
        run(BT/'aapt2.exe','link','-I',SDK/'platforms/android-35/android.jar','--manifest',directory/'AndroidManifest.xml','--version-code','416','--version-name','10.6.0.416','--min-sdk-version','24','--target-sdk-version','36','-o',compiled)
        with zipfile.ZipFile(compiled) as mz, zipfile.ZipFile(apk) as old, zipfile.ZipFile(unsigned,'w') as new:
            new.writestr('AndroidManifest.xml',mz.read('AndroidManifest.xml'),compress_type=zipfile.ZIP_DEFLATED)
            for info in old.infolist():
                if info.filename=='AndroidManifest.xml' or info.filename.startswith('META-INF/'): continue
                content = patched.read_bytes() if info.filename=='lib/arm64-v8a/libil2cpp.so' else old.read(info.filename)
                new.writestr(info,content)
    run(BT/'zipalign.exe','-f','-P','16','4',WORK/(apk.stem+'-unsigned.apk'),OUT/apk.name)

keystore = SRC/'local-development.jks'
if not keystore.exists():
    run('keytool','-genkeypair','-keystore',keystore,'-storepass','local-dice-build','-keypass','local-dice-build','-alias','localdice','-keyalg','RSA','-keysize','2048','-validity','3650','-dname','CN=Local Dice Development')
game_apks = [OUT/p.name for p in (ROOT/'pulled').glob('*.apk')]
for apk in game_apks:
    run('java','-jar',BT/'lib/apksigner.jar','sign','--ks',keystore,'--ks-pass','pass:local-dice-build','--key-pass','pass:local-dice-build',apk)
    run('java','-jar',BT/'lib/apksigner.jar','verify',apk)
    run(BT/'zipalign.exe','-c','-P','16','4',apk)
shutil.copyfile(config,OUT/config.name)
shutil.copyfile(SRC/'lan_relay.py',OUT/'lan_relay.py')
manifest = {'package':settings['package'],'version':'10.6.0.416','scope':'all-human local pass-and-play','patchRva':hex(site),'hookRva':hex(va),'hookBytes':len(stub),'startupGuardPatch':{'rva':hex(startup_site),'continuation':hex(startup_continue)},'sourceNativeSha256':hashlib.sha256(original.read_bytes()).hexdigest(),'patchedNativeSha256':hashlib.sha256(raw).hexdigest(),'apks':[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in game_apks]}
(OUT/'build-manifest.json').write_text(json.dumps(manifest,indent=2))
with zipfile.ZipFile(OUT/'LudoKing-LAN-Control.apks','w',zipfile.ZIP_STORED) as z:
    for apk in game_apks: z.write(apk,apk.name)
print('Release:',OUT,flush=True)
