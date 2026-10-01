"""Expose the emulator's dice API and discovery on the host LAN."""
import argparse, socket, socketserver, threading, json, re, time, http.client, http.server
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--port',type=int,default=8765)
parser.add_argument('--upstream',type=int,default=18765)
parser.add_argument('--name',default=None)
args=parser.parse_args()
credential=json.loads((Path(__file__).parent/'controller-config.json').read_text())['token']
def discover():
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as udp:
        udp.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1);udp.bind(('0.0.0.0',8766))
        print('Wi-Fi discovery listening on UDP 8766',flush=True)
        checked=0.0;ready=False;identity={}
        while True:
            query,peer=udp.recvfrom(256)
            if not re.fullmatch(rb'LOCAL_DICE_DISCOVER_V1:[a-f0-9]{32}',query):continue
            if time.monotonic()-checked>2:
                connection=http.client.HTTPConnection('127.0.0.1',args.upstream,timeout=1)
                try:
                    connection.request('GET','/status',headers={'Authorization':'Bearer '+credential,'Connection':'close'})
                    response=connection.getresponse();identity=json.loads(response.read(4096))
                    ready=response.status==200 and identity.get('scope')=='local pass-and-play' and bool(identity.get('deviceId'))
                except (OSError,ValueError,http.client.HTTPException):ready=False
                finally:connection.close()
                checked=time.monotonic()
            if not ready:continue
            response={'protocol':'local-dice-v1','nonce':query.decode().split(':')[1],'id':identity['deviceId'],
                      'name':(args.name or identity.get('deviceName','Ludo King LAN'))[:100],'port':args.port,'relay':True}
            udp.sendto(json.dumps(response).encode('utf-8'),peer)
class Relay(http.server.BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'
    def setup(self):super().setup();self.connection.settimeout(5)
    def log_message(self,*args):pass
    def reply(self,status,data):
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)))
        self.close_connection=self.headers.get('Connection','').lower()=='close'
        self.send_header('Cache-Control','no-store');self.send_header('Connection','close' if self.close_connection else 'keep-alive');self.end_headers();self.wfile.write(data);self.wfile.flush()
    def forward(self):
        if (self.command,self.path) not in [('GET','/status'),('POST','/next')]:self.reply(404,b'{"error":"unknown endpoint"}');return
        try:length=int(self.headers.get('Content-Length','0'))
        except ValueError:self.reply(400,b'{"error":"bad length"}');return
        if self.headers.get('Transfer-Encoding') or length<0 or length>64 or (self.command=='POST' and length<1):self.reply(400,b'{"error":"bad length"}');return
        upstream=http.client.HTTPConnection('127.0.0.1',args.upstream,timeout=4)
        try:
            body=self.rfile.read(length) if length else None
            if body is not None and len(body)!=length:self.reply(400,b'{"error":"incomplete body"}');return
            # Forward the caller's authorization; discovery credentials never authorize controls.
            upstream.request(self.command,self.path,body=body,headers={'Authorization':self.headers.get('Authorization',''),'Content-Type':'text/plain','Connection':'close'})
            response=upstream.getresponse();data=response.read(4097)
            if len(data)>4096:raise ValueError('response too large')
            self.reply(response.status,data)
        except (OSError,ValueError,http.client.HTTPException):
            try:self.reply(502,b'{"error":"game unavailable; check status before retrying"}')
            except OSError:pass
        finally:upstream.close()
    do_GET=forward
    do_POST=forward
class Server(http.server.ThreadingHTTPServer):
    allow_reuse_address=True
    daemon_threads=True
    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name='localhost'
        self.server_port=self.server_address[1]
with Server(('0.0.0.0',args.port),Relay) as server:
    threading.Thread(target=discover,daemon=True).start()
    print(f'LAN relay listening on port {args.port}; forwarding to localhost:{args.upstream}',flush=True)
    server.serve_forever()
