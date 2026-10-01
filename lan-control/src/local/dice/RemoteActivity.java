package local.dice;

import android.app.*;
import android.os.*;
import android.content.Context;
import android.net.wifi.WifiManager;
import android.text.InputType;
import android.text.TextUtils;
import android.graphics.*;
import android.graphics.drawable.*;
import android.content.res.ColorStateList;
import android.view.*;
import android.view.animation.LinearInterpolator;
import android.animation.ValueAnimator;
import android.widget.*;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.json.JSONObject;

public final class RemoteActivity extends Activity {
    private static final String DEFAULT_TOKEN="TOKEN_REPLACED_AT_BUILD";
    private static final int BG=0xffF6F7FB,INK=0xff141B2D,MUTED=0xff657086,BLUE=0xff3B66F5,LINE=0xffE4E8F1,GREEN=0xff167C57;
    private static final int SCANNING=0,RESULTS=1,CONTROL=2;
    private LinearLayout root,devices;
    private TextView status,connectionLabel;
    private EditText address,token;
    private Button sendButton;
    private DiceFace hero;
    private final List<View> diceButtons=new ArrayList<>();
    private final LinkedHashMap<String,Device> found=new LinkedHashMap<>();
    private final Handler handler=new Handler(Looper.getMainLooper());
    private volatile DatagramSocket discoverySocket;
    private volatile int generation;
    private int page=SCANNING,requestGeneration,selected=1;
    private boolean destroyed,busy,pending,connected,resumed,refreshing;
    private String connectedAddress="",connectedToken="";
    private Device current;
    private static final class Device {
        String id,name,address; boolean relay;
        Device(String i,String n,String a,boolean r){id=i;name=n;address=a;relay=r;}
    }
    private final Runnable polling=new Runnable(){public void run(){
        if(!destroyed&&resumed&&page==CONTROL&&!busy) send("GET","/status",null,true);
        if(!destroyed&&resumed&&page==CONTROL) handler.postDelayed(this,2500);
    }};

    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        getWindow().setStatusBarColor(BG);getWindow().setNavigationBarColor(BG);
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR|(Build.VERSION.SDK_INT>=26?View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR:0));
        address=new EditText(this);token=new EditText(this);
        address.setSingleLine(true);token.setSingleLine(true);
        address.setText(getPreferences(0).getString("address",""));token.setText(getPreferences(0).getString("token",DEFAULT_TOKEN));
        token.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);
        root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setBackgroundColor(BG);
        root.setOnApplyWindowInsetsListener((v,insets)->{v.setPadding(insets.getSystemWindowInsetLeft(),insets.getSystemWindowInsetTop(),insets.getSystemWindowInsetRight(),insets.getSystemWindowInsetBottom());return insets;});
        setContentView(root);root.requestApplyInsets();scan();
    }
    private int dp(float n){return Math.round(n*getResources().getDisplayMetrics().density);}
    private TextView text(String value,int size,int color,boolean bold){
        TextView t=new TextView(this);t.setText(value);t.setTextSize(size);t.setTextColor(color);
        t.setTypeface(Typeface.create(bold?"sans-serif-medium":"sans-serif",Typeface.NORMAL));t.setIncludeFontPadding(false);return t;
    }
    private LinearLayout column(){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);return l;}
    private GradientDrawable shape(int color,float radius,int stroke){GradientDrawable d=new GradientDrawable();d.setColor(color);d.setCornerRadius(dp(radius));if(stroke!=0)d.setStroke(dp(1),stroke);return d;}
    private void surface(View v,int color,int stroke,float radius){v.setBackground(new RippleDrawable(ColorStateList.valueOf(0x163B66F5),shape(color,radius,stroke),shape(-1,radius,0)));}
    private void space(LinearLayout l,int height){l.addView(new View(this),new LinearLayout.LayoutParams(1,dp(height)));}
    private Button button(String label,boolean primary){
        Button b=new Button(this);b.setText(label);b.setAllCaps(false);b.setTextSize(16);b.setTypeface(Typeface.create("sans-serif-medium",0));b.setTextColor(primary?-1:INK);b.setMinHeight(0);b.setMinimumHeight(0);b.setPadding(dp(16),0,dp(16),0);b.setStateListAnimator(null);surface(b,primary?INK:-1,primary?0:LINE,18);return b;
    }
    private void appendButton(LinearLayout l,Button b){l.addView(b,new LinearLayout.LayoutParams(-1,dp(56)));}
    private void header(boolean back){
        LinearLayout row=new LinearLayout(this);row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(dp(24),dp(12),dp(24),dp(12));
        if(back){Button b=button("‹",false);b.setTextSize(28);b.setContentDescription("Back to devices");row.addView(b,new LinearLayout.LayoutParams(dp(44),dp(44)));b.setOnClickListener(v->showResults(null));}
        TextView brand=text("LOCAL DICE",12,INK,true);brand.setLetterSpacing(.18f);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(0,-2,1);p.leftMargin=back?dp(16):0;row.addView(brand,p);
        TextView badge=text("●  SAME WI-FI",10,GREEN,true);badge.setLetterSpacing(.04f);row.addView(badge);root.addView(row);
    }
    private void transition(){root.setAlpha(0);root.animate().alpha(1).setDuration(180).start();}
    private void showScanner(){
        page=SCANNING;root.removeAllViews();header(false);
        LinearLayout body=column();body.setPadding(dp(28),dp(26),dp(28),dp(20));
        TextView eyebrow=text("DISCOVER",11,BLUE,true);eyebrow.setLetterSpacing(.18f);body.addView(eyebrow);space(body,12);
        body.addView(text("Let's connect.",34,INK,true));space(body,12);
        body.addView(text("Finding your game on the\nsame Wi-Fi network.",16,MUTED,false));
        Radar radar=new Radar(this);radar.setContentDescription("Scanning for nearby Ludo King LAN devices");body.addView(radar,new LinearLayout.LayoutParams(-1,0,1));
        TextView label=text("Looking for your game",19,INK,true);label.setGravity(Gravity.CENTER);body.addView(label);space(body,10);
        TextView hint=text("Keep Ludo King LAN open on your device.",13,MUTED,false);hint.setGravity(Gravity.CENTER);body.addView(hint);space(body,28);
        root.addView(body,new LinearLayout.LayoutParams(-1,0,1));transition();
    }
    private LinearLayout content(){
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.setClipToPadding(false);
        LinearLayout body=column();body.setPadding(dp(24),dp(18),dp(24),dp(24));scroll.addView(body);root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));return body;
    }
    private void showResults(String error){
        ++requestGeneration;busy=false;connected=false;connectedAddress="";connectedToken="";handler.removeCallbacks(polling);
        page=RESULTS;root.removeAllViews();header(false);LinearLayout body=content();
        TextView eyebrow=text("YOUR NETWORK",11,BLUE,true);eyebrow.setLetterSpacing(.18f);body.addView(eyebrow);space(body,12);
        body.addView(text(found.isEmpty()?"No games yet.":"Choose your game.",32,INK,true));space(body,12);
        body.addView(text(found.isEmpty()?"Make sure the game is open and both\ndevices are connected to the same Wi-Fi.":"One tap to connect. Your next roll awaits.",15,MUTED,false));space(body,32);
        devices=column();body.addView(devices);
        if(found.isEmpty()){
            DiceFace empty=new DiceFace(this,6,false);LinearLayout.LayoutParams p=new LinearLayout.LayoutParams(dp(100),dp(100));p.gravity=Gravity.CENTER;p.topMargin=dp(28);p.bottomMargin=dp(36);devices.addView(empty,p);
        }else for(Device d:found.values())addDeviceCard(d);
        space(body,24);status=text(error==null?(found.isEmpty()?"No devices discovered":found.size()+" game"+(found.size()==1?"":"s")+" available"):error,13,MUTED,false);status.setGravity(Gravity.CENTER);body.addView(status);space(body,24);
        Button again=button("Scan again",true);appendButton(body,again);again.setOnClickListener(v->scan());space(body,12);
        Button manual=button("Connect manually",false);appendButton(body,manual);manual.setOnClickListener(v->manualDialog());space(body,28);
        TextView foot=text("PRIVATE NETWORK  ·  LOCAL PLAY",10,MUTED,true);foot.setLetterSpacing(.12f);foot.setGravity(Gravity.CENTER);body.addView(foot);transition();
    }
    private void addDeviceCard(Device d){
        LinearLayout card=new LinearLayout(this);card.setGravity(Gravity.CENTER_VERTICAL);card.setPadding(dp(18),dp(20),dp(18),dp(20));surface(card,-1,LINE,22);card.setElevation(dp(1));
        DiceFace icon=new DiceFace(this,6,false);card.addView(icon,new LinearLayout.LayoutParams(dp(48),dp(48)));
        LinearLayout names=column();LinearLayout.LayoutParams np=new LinearLayout.LayoutParams(0,-2,1);np.leftMargin=dp(16);np.rightMargin=dp(12);card.addView(names,np);
        TextView name=text(d.name,17,INK,true);name.setMaxLines(2);name.setEllipsize(TextUtils.TruncateAt.END);names.addView(name);space(names,7);names.addView(text("Ludo King LAN · Available",12,GREEN,false));
        card.addView(text("›",28,MUTED,false));LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(-1,-2);cp.bottomMargin=dp(14);devices.addView(card,cp);
        card.setFocusable(true);card.setContentDescription("Connect to "+d.name);card.setOnClickListener(v->connectDevice(d));
    }
    private void connectDevice(Device d){
        if(busy)return;current=d;address.setText(d.address);connected=false;pending=false;selected=1;
        showControl();send("GET","/status",null,false);
    }
    private void showControl(){
        page=CONTROL;root.removeAllViews();diceButtons.clear();header(true);LinearLayout body=content();
        LinearLayout badge=new LinearLayout(this);badge.setGravity(Gravity.CENTER_VERTICAL);badge.setPadding(dp(16),dp(14),dp(16),dp(14));badge.setBackground(shape(-1,18,LINE));
        LinearLayout names=column();TextView name=text(current.name,16,INK,true);name.setMaxLines(2);names.addView(name);space(names,6);connectionLabel=text("●  Connecting…",12,MUTED,false);names.addView(connectionLabel);badge.addView(names,new LinearLayout.LayoutParams(0,-2,1));
        TextView change=text("Change",12,BLUE,true);change.setGravity(Gravity.CENTER);change.setMinHeight(dp(48));change.setMinWidth(dp(64));change.setPadding(dp(12),dp(12),0,dp(12));change.setOnClickListener(v->showResults(null));badge.addView(change);body.addView(badge);space(body,24);
        body.addView(text("Make your next move.",29,INK,true));space(body,8);body.addView(text("Choose the number for your next local roll.",14,MUTED,false));space(body,24);
        LinearLayout showcase=new LinearLayout(this);showcase.setGravity(Gravity.CENTER_VERTICAL);showcase.setPadding(dp(24),dp(22),dp(24),dp(22));
        GradientDrawable gradient=new GradientDrawable(GradientDrawable.Orientation.TL_BR,new int[]{0xff151D35,0xff303E72});gradient.setCornerRadius(dp(26));showcase.setBackground(gradient);
        LinearLayout caption=column();TextView small=text("NEXT ROLL",11,0xffAFC2FF,true);small.setLetterSpacing(.16f);caption.addView(small);space(caption,12);caption.addView(text("Your choice.",24,-1,true));space(caption,8);caption.addView(text("One roll at a time.",12,0xffC3CDE6,false));showcase.addView(caption,new LinearLayout.LayoutParams(0,-2,1));
        hero=new DiceFace(this,selected,true);showcase.addView(hero,new LinearLayout.LayoutParams(dp(94),dp(94)));body.addView(showcase);space(body,24);
        for(int row=0;row<2;row++){
            LinearLayout numbers=new LinearLayout(this);
            for(int col=0;col<3;col++){
                final int n=row*3+col+1;LinearLayout tile=column();tile.setGravity(Gravity.CENTER);tile.setFocusable(true);tile.setContentDescription("Select number "+n);
                TextView digit=text(Integer.toString(n),32,INK,true);digit.setGravity(Gravity.CENTER);tile.addView(digit);space(tile,4);TextView label=text(new String[]{"ONE","TWO","THREE","FOUR","FIVE","SIX"}[n-1],9,MUTED,true);label.setGravity(Gravity.CENTER);label.setLetterSpacing(.12f);tile.addView(label);
                tile.setOnClickListener(v->{selected=n;hero.value=n;hero.invalidate();updateControls();v.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP);});diceButtons.add(tile);
                LinearLayout.LayoutParams tp=new LinearLayout.LayoutParams(0,dp(84),1);if(col>0)tp.leftMargin=dp(12);numbers.addView(tile,tp);
            }
            body.addView(numbers);if(row==0)space(body,12);
        }
        space(body,22);sendButton=button("Connect to send",true);appendButton(body,sendButton);sendButton.setOnClickListener(v->send("POST","/next",Integer.toString(selected),false));space(body,14);
        status=text("Checking your connection…",13,MUTED,false);status.setGravity(Gravity.CENTER);status.setAccessibilityLiveRegion(View.ACCESSIBILITY_LIVE_REGION_POLITE);body.addView(status);space(body,12);
        Button refresh=button("Refresh connection",false);appendButton(body,refresh);refresh.setOnClickListener(v->send("GET","/status",null,false));
        updateControls();handler.removeCallbacks(polling);if(resumed)handler.postDelayed(polling,2500);transition();
    }
    private void updateControls(){
        if(page!=CONTROL)return;
        for(int i=0;i<diceButtons.size();i++){View v=diceButtons.get(i);boolean active=selected==i+1;surface(v,active?0xffEAF0FF:-1,active?BLUE:LINE,19);v.setSelected(active);v.setAlpha(busy&&!refreshing?.65f:1);v.setEnabled(!busy||refreshing);}
        if(sendButton!=null){boolean enabled=connected&&(!busy||refreshing)&&!pending;sendButton.setEnabled(enabled);sendButton.setAlpha(enabled?1:.45f);sendButton.setText(busy&&!refreshing?"Connecting…":pending?"Waiting for the game to roll":!connected?"Connect to send":"Send number "+selected+"   →");}
        if(connectionLabel!=null){connectionLabel.setText(busy&&!connected?"●  Connecting…":connected?"●  Connected":"●  Connection unavailable");connectionLabel.setTextColor(connected?GREEN:MUTED);}
    }
    private void manualDialog(){
        LinearLayout form=column();form.setPadding(dp(24),dp(12),dp(24),0);
        if(address.getParent()!=null)((android.view.ViewGroup)address.getParent()).removeView(address);
        if(token.getParent()!=null)((android.view.ViewGroup)token.getParent()).removeView(token);
        address.setHint("Device IP:8765");token.setHint("Access token");form.addView(address);form.addView(token);
        new AlertDialog.Builder(this).setTitle("Connect manually").setMessage("Use this if Wi-Fi discovery is unavailable.").setView(form).setNegativeButton("Cancel",null).setPositiveButton("Connect",(dialog,which)->{
            if(address.getText().toString().trim().isEmpty()||token.getText().toString().trim().isEmpty()){status.setText("Enter the address and access token.");return;}
            current=new Device("manual","Ludo King LAN",address.getText().toString().trim(),false);connected=false;pending=false;showControl();send("GET","/status",null,false);
        }).show();
    }
    private void scan(){
        ++requestGeneration;busy=false;handler.removeCallbacks(polling);found.clear();showScanner();final int ticket=++generation;
        DatagramSocket old=discoverySocket;if(old!=null)old.close();
        new Thread(()->{
            WifiManager.MulticastLock lock=null;DatagramSocket socket=null;String failure=null;
            try{
                WifiManager wifi=(WifiManager)getApplicationContext().getSystemService(Context.WIFI_SERVICE);
                if(wifi!=null){lock=wifi.createMulticastLock("local-dice-scan");lock.setReferenceCounted(false);lock.acquire();}
                socket=new DatagramSocket();socket.setBroadcast(true);socket.setSoTimeout(300);discoverySocket=socket;
                String nonce=UUID.randomUUID().toString().replace("-","");byte[] query=("LOCAL_DICE_DISCOVER_V1:"+nonce).getBytes(StandardCharsets.US_ASCII);
                Set<InetAddress> targets=new HashSet<>();targets.add(InetAddress.getByName("255.255.255.255"));targets.add(InetAddress.getByName("127.0.0.1"));
                Enumeration<NetworkInterface> interfaces=NetworkInterface.getNetworkInterfaces();
                while(interfaces!=null&&interfaces.hasMoreElements()){NetworkInterface network=interfaces.nextElement();if(!network.isUp()||network.isLoopback())continue;for(InterfaceAddress iface:network.getInterfaceAddresses())if(iface.getBroadcast()!=null)targets.add(iface.getBroadcast());}
                if(Build.FINGERPRINT.contains("generic")||Build.MODEL.contains("sdk")||Build.HARDWARE.contains("ranchu")||Build.HARDWARE.contains("goldfish"))targets.add(InetAddress.getByName("10.0.2.2"));
                long end=System.currentTimeMillis()+5000,nextSend=0;byte[] buffer=new byte[1200];
                while(ticket==generation&&System.currentTimeMillis()<end){
                    if(System.currentTimeMillis()>=nextSend){for(InetAddress target:targets)try{socket.send(new DatagramPacket(query,query.length,target,8766));}catch(IOException ignored){}nextSend=System.currentTimeMillis()+1500;}
                    DatagramPacket reply=new DatagramPacket(buffer,buffer.length);try{socket.receive(reply);}catch(SocketTimeoutException timeout){continue;}
                    try{
                        JSONObject result=new JSONObject(new String(reply.getData(),0,reply.getLength(),StandardCharsets.UTF_8));
                        if(!"local-dice-v1".equals(result.optString("protocol"))||!nonce.equals(result.optString("nonce"))||result.optInt("port")!=8765)continue;
                        String id=result.optString("id");if(id.isEmpty()||id.length()>128)continue;
                        String name=result.optString("name","Ludo King LAN").replaceAll("[\\p{Cntrl}]"," ").replace(" · Ludo King LAN","");if(name.length()>80)name=name.substring(0,80);
                        final Device device=new Device(id,name,reply.getAddress().getHostAddress()+":8765",result.optBoolean("relay"));
                        runOnUiThread(()->{if(destroyed||ticket!=generation)return;Device prior=found.get(device.id);if(prior==null&&found.size()<64)found.put(device.id,device);else if(prior!=null&&device.relay&&!prior.relay)found.put(device.id,device);});
                    }catch(Exception ignored){}
                }
            }catch(Exception e){if(ticket==generation)failure="Scan unavailable. Try again or connect manually.";}
            finally{
                if(socket!=null)socket.close();if(discoverySocket==socket)discoverySocket=null;if(lock!=null&&lock.isHeld())lock.release();final String error=failure;
                runOnUiThread(()->{if(!destroyed&&ticket==generation)showResults(error);});
            }
        },"DiceDiscovery").start();
    }
    private void send(String method,String path,String body){send(method,path,body,false);}
    private void send(String method,String path,String body,boolean quiet){
        if(busy||destroyed||page!=CONTROL)return;
        final String destination=address.getText().toString().trim(),credential=token.getText().toString().trim();
        if(destination.isEmpty()||credential.isEmpty())return;
        if(body!=null&&(!connected||!destination.equals(connectedAddress)||!credential.equals(connectedToken)))return;
        final int ticket=requestGeneration;busy=true;refreshing=quiet;if(!quiet)status.setText(body==null?"Connecting to your game…":"Sending number "+body+"…");updateControls();
        new Thread(()->{
            HttpURLConnection connection=null;boolean success=false,waiting=false;String message;String name=null;ByteArrayOutputStream result=new ByteArrayOutputStream();
            try{
                String base=destination.startsWith("http://")?destination:"http://"+destination;
                connection=(HttpURLConnection)new URL(base+path).openConnection();connection.setConnectTimeout(2500);connection.setReadTimeout(2500);connection.setRequestMethod(method);connection.setRequestProperty("Authorization","Bearer "+credential);
                if(body!=null){byte[] bytes=body.getBytes(StandardCharsets.US_ASCII);connection.setDoOutput(true);connection.setFixedLengthStreamingMode(bytes.length);connection.setRequestProperty("Content-Type","text/plain");try(OutputStream output=connection.getOutputStream()){output.write(bytes);}}
                int code=connection.getResponseCode();InputStream input=code>=400?connection.getErrorStream():connection.getInputStream();
                if(input!=null)try(InputStream stream=input){byte[] buffer=new byte[1024];int n;while((n=stream.read(buffer))>=0&&result.size()<4096)result.write(buffer,0,n);}
                JSONObject json=new JSONObject(result.toString("UTF-8"));
                if(code==200&&body==null&&"local pass-and-play".equals(json.optString("scope"))){success=true;waiting=json.optBoolean("pending");name=json.optString("deviceName",null);message=waiting?"Number ready. Roll the dice in your game.":"Ready when you are. Choose a number and send.";}
                else if(code==200&&body!=null&&json.optInt("queued")==Integer.parseInt(body)){success=true;waiting=true;message="Number "+body+" is ready. Roll the dice in your game.";}
                else if(code==409&&body!=null){success=true;waiting=true;message="A number is already waiting. Roll in the game first.";}
                else message=code==401?"Access token doesn't match. Connect again using manual settings.":"Couldn't connect. Keep the game open and try again.";
            }catch(Exception e){android.util.Log.w("LocalDiceRemote","Request failed",e);message=body==null?"Connection lost. Keep the game open, then refresh.":"Delivery could not be confirmed. Refresh before sending again.";}
            finally{if(connection!=null)connection.disconnect();}
            final boolean ok=success,queued=waiting;final String info=message,deviceName=name;
            runOnUiThread(()->{
                if(destroyed||ticket!=requestGeneration||page!=CONTROL)return;
                boolean wasConnected=connected,wasPending=pending;
                busy=false;refreshing=false;connected=ok;pending=queued;connectedAddress=ok?destination:"";connectedToken=ok?credential:"";
                if(ok)getPreferences(0).edit().putString("address",destination).putString("token",credential).apply();
                if(current!=null&&deviceName!=null&&!deviceName.trim().isEmpty())current.name=deviceName;
                // Preserve the send acknowledgement until the next roll consumes it.
                if(!quiet||!ok||!queued||!wasConnected||wasPending!=queued)status.setText(info);updateControls();
            });
        },"DiceRemoteRequest").start();
    }
    @Override public void onBackPressed(){if(page==CONTROL)showResults(null);else if(page==SCANNING){++generation;DatagramSocket s=discoverySocket;if(s!=null)s.close();showResults(null);}else super.onBackPressed();}
    @Override protected void onResume(){super.onResume();resumed=true;if(page==CONTROL){handler.removeCallbacks(polling);handler.postDelayed(polling,1000);}}
    @Override protected void onPause(){resumed=false;handler.removeCallbacks(polling);super.onPause();}
    @Override protected void onDestroy(){destroyed=true;++generation;++requestGeneration;handler.removeCallbacksAndMessages(null);DatagramSocket s=discoverySocket;if(s!=null)s.close();super.onDestroy();}

    private class DiceFace extends View{
        int value;boolean dark;Paint paint=new Paint(3);
        DiceFace(Context c,int v,boolean d){super(c);value=v;dark=d;setImportantForAccessibility(View.IMPORTANT_FOR_ACCESSIBILITY_NO);}
        @Override protected void onDraw(Canvas c){
            float size=Math.min(getWidth(),getHeight()),x=(getWidth()-size)/2,y=(getHeight()-size)/2;
            paint.setColor(dark?-1:0xffEAF0FF);c.drawRoundRect(x+size*.03f,y+size*.03f,x+size*.97f,y+size*.97f,size*.23f,size*.23f,paint);
            paint.setColor(dark?0xff273764:BLUE);float low=.27f,high=.73f,mid=.5f,r=size*.065f;
            if(value%2==1)c.drawCircle(x+size*mid,y+size*mid,r,paint);
            if(value>=2){c.drawCircle(x+size*low,y+size*low,r,paint);c.drawCircle(x+size*high,y+size*high,r,paint);}
            if(value>=4){c.drawCircle(x+size*high,y+size*low,r,paint);c.drawCircle(x+size*low,y+size*high,r,paint);}
            if(value==6){c.drawCircle(x+size*low,y+size*mid,r,paint);c.drawCircle(x+size*high,y+size*mid,r,paint);}
        }
    }
    private class Radar extends View{
        private final Paint paint=new Paint(3);private ValueAnimator animator;private float phase;
        Radar(Context c){super(c);setLayerType(View.LAYER_TYPE_SOFTWARE,null);}
        @Override protected void onAttachedToWindow(){super.onAttachedToWindow();if(Build.VERSION.SDK_INT>=26&&!ValueAnimator.areAnimatorsEnabled())return;animator=ValueAnimator.ofFloat(0,1);animator.setDuration(2600);animator.setRepeatCount(ValueAnimator.INFINITE);animator.setInterpolator(new LinearInterpolator());animator.addUpdateListener(a->{phase=(float)a.getAnimatedValue();invalidate();});animator.start();}
        @Override protected void onDetachedFromWindow(){if(animator!=null){animator.cancel();animator=null;}super.onDetachedFromWindow();}
        @Override protected void onDraw(Canvas c){
            float x=getWidth()/2f,y=getHeight()/2f,r=Math.min(getWidth()*.45f,getHeight()*.43f);
            paint.setShader(new RadialGradient(x,y,r,new int[]{0xffE3E9FF,0xffF6F7FB},null,Shader.TileMode.CLAMP));c.drawCircle(x,y,r,paint);paint.setShader(null);
            paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(dp(1));paint.setColor(0xffDCE3F4);
            for(int i=1;i<=3;i++)c.drawCircle(x,y,r*i/3,paint);paint.setStyle(Paint.Style.FILL);
            c.save();c.rotate(phase*360,x,y);paint.setShader(new SweepGradient(x,y,new int[]{0x003B66F5,0x003B66F5,0x253B66F5,0x653B66F5},new float[]{0,.7f,.92f,1}));c.drawCircle(x,y,r,paint);paint.setShader(null);c.restore();
            paint.setStyle(Paint.Style.STROKE);paint.setStrokeWidth(dp(2));paint.setColor(0x303B66F5);float pulse=(phase*.5f+.45f)*r;c.drawCircle(x,y,pulse,paint);paint.setStyle(Paint.Style.FILL);
            for(int i=0;i<3;i++){double a=Math.toRadians(i*115+25);float px=x+(float)Math.cos(a)*r*.79f,py=y+(float)Math.sin(a)*r*.79f;paint.setColor(0xffFFFFFF);c.drawCircle(px,py,dp(10),paint);paint.setColor(i==1?0xff8871E5:BLUE);c.drawCircle(px,py,dp(4),paint);}
            float box=Math.min(dp(88),r*.7f);paint.setColor(0xff182442);c.drawRoundRect(x-box/2,y-box/2,x+box/2,y+box/2,dp(24),dp(24),paint);paint.setColor(-1);
            float offset=box*.2f;for(int i=-1;i<=1;i++)for(int j=-1;j<=1;j++)if(i==j||i==-j)c.drawCircle(x+i*offset,y+j*offset,box*.055f,paint);
        }
    }
}
