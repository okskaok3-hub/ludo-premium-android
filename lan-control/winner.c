/* Freestanding ARM64: local Classic dice assistance; original movement/ranking stay in charge. */
typedef unsigned char u8;
typedef unsigned long up;
extern void *gamemanager_slot;
extern void *ping_method_slot;
extern void init_metadata(void *);
extern void *get_transform(void *, void *);
extern void *get_child(void *, int, void *);
extern void *get_ping(void *, void *);
extern int is_quick(void *, void *);
#define P(o,n) (*(void **)((u8 *)(o)+(n)))
#define I(o,n) (*(int *)((u8 *)(o)+(n)))
#define B(o,n) (*((u8 *)(o)+(n)))
static long syscall4(long n,long a,long b,long c,long d) {
 register long x8 __asm__("x8")=n,x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d;
 __asm__ volatile("svc #0":"+r"(x0):"r"(x8),"r"(x1),"r"(x2),"r"(x3):"memory","cc");return x0;
}
static const char state[]="/data/user/0/com.ludo.king.lan/files/winner-state";
static const char temp[]="/data/user/0/com.ludo.king.lan/files/winner-state.tmp";
static const char policy[]="/data/user/0/com.ludo.king.lan/files/winner-policy";
static const char pending[]="/data/user/0/com.ludo.king.lan/files/nextdice";
static const char hex[]="0123456789abcdef";
static void remove_file(const char *p){syscall4(35,-100,(long)p,0,0);}
static int read_file(const char *p,char *b,int n){long f=syscall4(56,-100,(long)p,0x80000,0);if(f<0)return 0;int r=syscall4(63,f,(long)b,n,0);syscall4(57,f,0,0,0);return r;}
static void publish(char *b){long f=syscall4(56,-100,(long)temp,577,384);if(f<0)return;long r=syscall4(64,f,(long)b,20,0);syscall4(57,f,0,0,0);if(r==20)syscall4(38,-100,(long)temp,-100,(long)state);}
static void *manager(void){void *k=gamemanager_slot;if(!k)return 0;k=P(k,0);if(!k)return 0;k=P(k,0xb8);return k?P(k,0x48):0;}
static int mask_for(void *gc){
 void *gm=manager();if(!gc||!gm||!B(gm,0x8a)||B(gm,0x89)||B(gm,0x8b)||B(gm,0x8c)||B(gm,0x8d)||is_quick(gm,0))return 0;
 int total=I(gc,0x54c);if(total<2||total>4)return 0;
 void *list=P(gc,0x400),*bots=P(gc,0x800);if(!list||!bots)return 0;
 void *items=P(list,0x10);if(!items||I(list,0x18)<5||I(bots,0x18)<5)return 0;
 int mask=0;for(int t=1;t<=4;t++)if(B(items,0x20+t)){if(I(bots,0x20+t*4))return 0;mask|=1<<(t-1);}return mask;
}
void winner_end(void){remove_file(policy);remove_file(state);}
void winner_begin(void *gc){
 winner_end();remove_file(pending);int mask=mask_for(gc);if(!mask)return;
 long ts[2]={0,0};syscall4(113,1,(long)ts,0,0);up id=(up)ts[0]*1000000000+(up)ts[1];char b[20];
 for(int i=15;i>=0;i--){b[i]=hex[id&15];id>>=4;}b[16]=':';b[17]=hex[mask];b[18]=':';b[19]='1';publish(b);
}
typedef struct {int position,active,home;} Token;
static int tokens(void *gc,int turn,Token *out){
 void *list=P(gc,0x518);if(!list||I(list,0x18)<=turn)return 0;void *a=P(list,0x10);if(!a)return 0;
 void *object=P(a,0x20+turn*8);if(!object)return 0;void *transform=get_transform(object,0);if(!transform)return 0;
 void *var=ping_method_slot;if(!var)return 0;if(!P(var,0))init_metadata(var);void *method=P(var,0);if(!method)return 0;
 void *positions=P(gc,0x520);if(!positions||I(positions,0x18)<(turn+1)*4)return 0;
 for(int j=0;j<4;j++){void *child=get_child(transform,j,0);if(!child)return 0;void *ping=get_ping(child,method);if(!ping)return 0;
 /* Leaving base sets off-the-mark/token-out before the active flag settles. */
 out[j].active=B(ping,0x58)||B(ping,0x5a)||B(ping,0xf1);out[j].home=B(ping,0x5b);out[j].position=I(positions,0x20+(turn*4+j)*4);if(out[j].position<0||out[j].position>56)return 0;}
 return 1;
}
/* Shared pure decision function also exercised by host tests. */
int winner_choose(Token *t,int target,int original,int sixes){
 int homes=0;for(int j=0;j<4;j++)homes+=t[j].home!=0;
 if(!target){if(homes!=3)return original;for(int j=0;j<4;j++)if(!t[j].home&&t[j].active&&t[j].position+original==56){for(int d=6;d>=1;d--)if(t[j].position+d!=56)return d;}return original;}
 int best=0,score=-100000;
 for(int d=1;d<=6;d++){if(d==6&&sixes>=2)continue;int s=-1000;
 for(int j=0;j<4;j++){if(t[j].home)continue;int v=-1000;
 if(!t[j].active){if(d==6)v=300;}else if(t[j].position+d<=56){v=20+d+t[j].position/4;if(t[j].position+d==56)v=1000;else if(d==6)v+=120;}
 if(v>s)s=v;}if(s>score){score=s;best=d;}}
 return best?best:original;
}
int winner_pick(void *dc,void *gc){
 char s[21],p[19];if(read_file(state,s,21)!=20||s[19]!='1'||read_file(policy,p,19)!=18)return 0;
 for(int i=0;i<16;i++)if(s[i]!=p[i])return 0;
 int selected=p[17]-'0',mask=mask_for(gc);if(p[16]!=':'||selected<1||selected>4||!(mask&(1<<(selected-1))))return 0;
 void *wins=P(gc,0x3e8);if(wins)for(int t=1;t<=4;t++)if(B(wins,0x20+t)){winner_end();return 0;}
 int turn=I(gc,0x548);if(turn<1||turn>4)return 0;Token t[4];if(!tokens(gc,turn,t))return 0;
 int original=I(dc,0x20)^I(dc,0x24);if(original<1||original>6)return 0;
 int die=winner_choose(t,turn==selected,original,I(gc,0x570));
 /* Compact local diagnostic: turn, colour, die, streak, then position/active/home. */
 char log[32];log[0]='0'+turn;log[1]='0'+selected;log[2]='0'+die;log[3]='0'+I(gc,0x570);
 for(int j=0;j<4;j++){log[4+j*4]='0'+t[j].position/10;log[5+j*4]='0'+t[j].position%10;log[6+j*4]='0'+t[j].active;log[7+j*4]='0'+t[j].home;}
 long f=syscall4(56,-100,(long)"/data/user/0/com.ludo.king.lan/files/winner-roll",577,384);
 if(f>=0){syscall4(64,f,(long)log,20,0);syscall4(57,f,0,0,0);}
 return die;
}
