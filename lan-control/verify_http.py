import json, urllib.request, urllib.error
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
config=json.loads((ROOT/'lan-release/controller-config.json').read_text())
results=[]
for method,path,body,authorized in [('GET','/status',None,False),('POST','/next',b'9',True),('POST','/next',b'2',True),('POST','/next',b'5',True)]:
    req=urllib.request.Request('http://127.0.0.1:18765'+path,data=body,method=method,headers={'Authorization':'Bearer '+(config['token'] if authorized else 'invalid')})
    try: response=urllib.request.urlopen(req,timeout=3)
    except urllib.error.HTTPError as error: response=error
    results.append({'method':method,'path':path,'body':body.decode() if body else None,'code':response.code,'response':response.read().decode()})
(ROOT/'lan-release/http-verification.json').write_text(json.dumps(results,indent=2))
print(json.dumps(results,indent=2))
assert [r['code'] for r in results]==[401,400,200,409]
