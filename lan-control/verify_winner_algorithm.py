"""Compile the actual C dice decision for the Windows host and test endgame rules."""
import ctypes,json,os,subprocess
from pathlib import Path
R=Path(__file__).resolve().parent.parent;W=R/'lan-build/winner-tests';W.mkdir(parents=True,exist_ok=True)
s=(R/'lan-control/winner.c').read_text();a=s.index('typedef struct {int position');b=s.index('static int tokens',a);c=s.index('int winner_choose');d=s.index('\nint winner_pick',c)
(W/'choose.c').write_text(s[a:b]+s[c:d])
ndk=Path(os.environ['LOCALAPPDATA'])/'Android/Sdk/ndk/30.0.14904198/toolchains/llvm/prebuilt/windows-x86_64/bin'
subprocess.run([str(ndk/'clang.exe'),'--target=x86_64-pc-windows-msvc','-O2','-c',str(W/'choose.c'),'-o',str(W/'choose.obj')],check=True)
subprocess.run([str(ndk/'ld.lld.exe'),'-flavor','link','/dll','/noentry','/nodefaultlib','/export:winner_choose','/out:'+str(W/'choose.dll'),str(W/'choose.obj')],check=True)
class Token(ctypes.Structure):_fields_=[('position',ctypes.c_int),('active',ctypes.c_int),('home',ctypes.c_int)]
f=ctypes.CDLL(str(W/'choose.dll')).winner_choose;f.argtypes=[ctypes.POINTER(Token),ctypes.c_int,ctypes.c_int,ctypes.c_int];f.restype=ctypes.c_int
cases=[]
def case(name,t,target,original,sixes,expected=None,forbidden=None):
    actual=f((Token*4)(*[Token(*v) for v in t]),target,original,sixes);assert 1<=actual<=6
    if expected is not None:assert actual==expected,(name,actual)
    if forbidden is not None:assert actual!=forbidden,(name,actual)
    cases.append({'case':name,'result':actual})
base=[(0,0,0)]*4
case('opening six',base,1,2,0,6)
case('third six avoided',base,1,6,2,forbidden=6)
case('exact home 2',[(54,1,0)]+base[:3],1,6,0,2)
case('exact home 1 beats opening',[(55,1,0)]+base[:3],1,6,0,1)
case('progress six',[(12,1,0)]*4,1,1,0,6)
case('ordinary opponent original retained',[(12,1,0)]*4,0,3,0,3)
for distance in range(1,7):case('opponent last token protected '+str(distance),[(56,1,1)]*3+[(56-distance,1,0)],0,distance,0,forbidden=distance)
case('opponent permitted third token home',[(56,1,1)]*2+[(55,1,0),(12,1,0)],0,1,0,1)
(R/'lan-release/winner-algorithm-verification.json').write_text(json.dumps({'compiledCDecisionTests':cases,'allPassed':True},indent=2));print('Passed',len(cases),'compiled C decision cases')
