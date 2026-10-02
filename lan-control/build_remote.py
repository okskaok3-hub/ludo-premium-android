import os, subprocess, zipfile, json, hashlib
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT/'lan-control'; WORK = ROOT/'lan-build/remote'; OUT = ROOT/'lan-release'
SDK = Path(os.environ['LOCALAPPDATA'])/'Android/Sdk'; BT = SDK/'build-tools/36.0.0'
WORK.mkdir(parents=True,exist_ok=True)
def run(*args): subprocess.run(list(map(str,args)),check=True)
classes=WORK/'classes'; classes.mkdir(exist_ok=True)
dex=WORK/'dex'; dex.mkdir(exist_ok=True)
source=WORK/'RemoteActivity.java'
source.write_text((SRC/'src/local/dice/RemoteActivity.java').read_text(encoding='utf-8-sig').replace('TOKEN_REPLACED_AT_BUILD',json.loads((OUT/'controller-config.json').read_text())['token']),encoding='utf-8')
run('javac','-encoding','UTF-8','-source','8','-target','8','-classpath',SDK/'platforms/android-35/android.jar','-d',classes,source)
run('java','-cp',BT/'lib/d8.jar','com.android.tools.r8.D8','--min-api','24','--lib',SDK/'platforms/android-35/android.jar','--output',dex,*classes.rglob('*.class'))
run(BT/'aapt2.exe','link','-I',SDK/'platforms/android-35/android.jar','--manifest',SRC/'remote-manifest.xml','-o',WORK/'unsigned.apk')
with zipfile.ZipFile(WORK/'unsigned.apk','a') as z: z.write(dex/'classes.dex','classes.dex',compress_type=zipfile.ZIP_DEFLATED)
apk=OUT/'Local-Dice-Remote.apk'
run(BT/'zipalign.exe','-f','4',WORK/'unsigned.apk',apk)
run('java','-jar',BT/'lib/apksigner.jar','sign','--ks',SRC/'local-development.jks','--ks-pass','pass:local-dice-build','--key-pass','pass:local-dice-build',apk)
run('java','-jar',BT/'lib/apksigner.jar','verify',apk)
manifest={'package':'com.localdice.remote','version':'4.0','sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),'bytes':apk.stat().st_size,'screens':['animated scanner','deduplicated device selection','connected dice and colour control'],'colourPicker':'Android only'}
(OUT/'companion-manifest.json').write_text(json.dumps(manifest,indent=2))
print(apk)
