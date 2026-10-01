import argparse,json,urllib.request
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('value',nargs='?',type=int,choices=range(1,7))
parser.add_argument('--host',default='127.0.0.1:18765')
args=parser.parse_args()
root=Path(__file__).resolve().parent.parent
config=json.loads((root/'lan-release/controller-config.json').read_text())
request=urllib.request.Request('http://'+args.host+('/next' if args.value else '/status'),data=str(args.value).encode() if args.value else None,headers={'Authorization':'Bearer '+config['token']})
with urllib.request.urlopen(request,timeout=4) as response: print(response.read().decode())
