"""Merge the tested four-split local game into one signed standalone APK."""
import os, json, shutil, subprocess, zipfile, hashlib
from pathlib import Path
from xml.etree import ElementTree as ET
ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'lan-control';WORK=ROOT/'lan-build/standalone';OUT=ROOT/'lan-release'
SDK=Path(os.environ['LOCALAPPDATA'])/'Android/Sdk';BT=SDK/'build-tools/36.0.0'
APKTOOL=Path('C:/Users/user/Downloads/Telegram Desktop/apktool_2.12.0.jar')
ANDROID='{http://schemas.android.com/apk/res/android}';ET.register_namespace('android','http://schemas.android.com/apk/res/android')
WORK.mkdir(parents=True,exist_ok=True)
base=WORK/'base';shutil.copytree(ROOT/'lan-build/base',base,dirs_exist_ok=True,ignore=shutil.ignore_patterns('build','original'))
manifest=base/'AndroidManifest.xml';tree=ET.parse(manifest);root=tree.getroot()
for key in ['split',ANDROID+'requiredSplitTypes',ANDROID+'splitTypes',ANDROID+'isFeatureSplit',ANDROID+'isSplitRequired']:root.attrib.pop(key,None)
for node in list(root.findall('uses-split')):root.remove(node)
application=root.find('application');application.attrib.pop(ANDROID+'isSplitRequired',None)
for node in list(application.findall('meta-data')):
    if node.get(ANDROID+'name') in ['com.android.vending.splits.required','com.android.vending.splits','com.android.vending.derived.apk.id']:application.remove(node)
tree.write(manifest,encoding='utf-8',xml_declaration=True)
def run(*args):subprocess.run(list(map(str,args)),check=True)
compiled=WORK/'base-unsigned.apk';run('java','-jar',APKTOOL,'b',base,'-o',compiled)
merged=WORK/'merged-unsigned.apk';seen={};counts={}
inputs=[compiled,OUT/'split_UnityDataAssetPack.apk',OUT/'split_AddressablesAssetPack.apk',OUT/'split_config.arm64_v8a.apk']
with zipfile.ZipFile(merged,'w') as target:
    for index,path in enumerate(inputs):
        count=0
        with zipfile.ZipFile(path) as source:
            for info in source.infolist():
                name=info.filename
                if name.startswith('META-INF/') or (index and name=='AndroidManifest.xml'):continue
                data=source.read(name)
                if name in seen:
                    if seen[name]!=hashlib.sha256(data).digest():raise ValueError('Conflicting split entry: '+name)
                    continue
                seen[name]=hashlib.sha256(data).digest();target.writestr(info,data);count+=1
        counts[path.name]=count
apk=OUT/'Ludo-King-LAN-Standalone.apk'
run(BT/'zipalign.exe','-f','-P','16','4',merged,apk)
run('java','-jar',BT/'lib/apksigner.jar','sign','--ks',SRC/'local-development.jks','--ks-pass','pass:local-dice-build','--key-pass','pass:local-dice-build',apk)
run('java','-jar',BT/'lib/apksigner.jar','verify',apk)
run(BT/'zipalign.exe','-c','-P','16','4',apk)
with zipfile.ZipFile(apk) as z:assert z.testzip() is None
report={'file':apk.name,'package':'com.ludo.king.lan','architecture':'arm64-v8a','sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'bytes':apk.stat().st_size,'mergedEntries':counts,'splitRequirementRemoved':True}
(OUT/'standalone-manifest.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
