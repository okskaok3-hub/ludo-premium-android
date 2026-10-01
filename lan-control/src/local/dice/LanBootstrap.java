package local.dice;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.net.Uri;
import android.util.Log;
import android.os.Build;
import android.provider.Settings;
import java.util.UUID;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import org.json.JSONObject;

/** Local-only control bridge. Native code consumes the pending file atomically. */
public final class LanBootstrap extends ContentProvider {
    private static final String TOKEN = "TOKEN_REPLACED_AT_BUILD";
    private static final int PORT = 8765;
    private File directory;
    private String deviceId, deviceName;

    @Override public boolean onCreate() {
        directory = getContext().getFilesDir();
        deviceId = getContext().getSharedPreferences("lan-discovery", 0).getString("id", null);
        if (deviceId == null) {
            deviceId = UUID.randomUUID().toString();
            getContext().getSharedPreferences("lan-discovery", 0).edit().putString("id", deviceId).apply();
        }
        deviceName = Settings.Global.getString(getContext().getContentResolver(), "device_name");
        if (deviceName == null || deviceName.trim().isEmpty()) deviceName = Build.MODEL;
        if (deviceName.equals(Build.MODEL) && Build.MODEL.contains("sdk")) deviceName = "Android Emulator";
        if (deviceName.length() > 80) deviceName = deviceName.substring(0, 80);
        Thread thread = new Thread(() -> serve(), "LocalDiceLAN");
        thread.setDaemon(true);
        thread.start();
        Thread discovery = new Thread(() -> discover(), "LocalDiceDiscovery");
        discovery.setDaemon(true);
        discovery.start();
        return true;
    }

    private void discover() {
        try (DatagramSocket socket = new DatagramSocket(null)) {
            socket.setReuseAddress(true);
            socket.bind(new InetSocketAddress("0.0.0.0", 8766));
            byte[] buffer = new byte[256];
            while (!Thread.currentThread().isInterrupted()) {
                DatagramPacket packet = new DatagramPacket(buffer, buffer.length);
                socket.receive(packet);
                String query = new String(packet.getData(), 0, packet.getLength(), StandardCharsets.US_ASCII);
                if (!query.matches("LOCAL_DICE_DISCOVER_V1:[a-f0-9]{32}")) continue;
                JSONObject result = new JSONObject();
                result.put("protocol", "local-dice-v1");
                result.put("nonce", query.substring(query.indexOf(':') + 1));
                result.put("id", deviceId);
                result.put("name", deviceName);
                result.put("port", PORT);
                byte[] response = result.toString().getBytes(StandardCharsets.UTF_8);
                socket.send(new DatagramPacket(response, response.length, packet.getAddress(), packet.getPort()));
            }
        } catch (Exception e) { Log.w("LocalDiceLAN", "Discovery unavailable", e); }
    }

    private void serve() {
        try (ServerSocket server = new ServerSocket()) {
            server.setReuseAddress(true);
            server.bind(new InetSocketAddress("0.0.0.0", PORT));
            Log.i("LocalDiceLAN", "Listening on port " + PORT);
            while (!Thread.currentThread().isInterrupted()) {
                try (Socket socket = server.accept()) {
                    socket.setSoTimeout(2000);
                    handle(socket);
                } catch (Exception e) {
                    Log.w("LocalDiceLAN", "Request rejected: " + e.getClass().getSimpleName());
                }
            }
        } catch (IOException e) {
            Log.e("LocalDiceLAN", "LAN listener failed", e);
        }
    }

    private String line(InputStream input) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        for (int i = 0; i < 2048; i++) {
            int b = input.read();
            if (b < 0) throw new EOFException();
            if (b == 10) return bytes.toString("UTF-8").replace("\r", "");
            bytes.write(b);
        }
        throw new IOException("Line too long");
    }

    private void handle(Socket socket) throws Exception {
        InputStream input = socket.getInputStream();
        String[] request = line(input).split(" ");
        if (request.length != 3) { reply(socket, 400, "{\"error\":\"bad request\"}"); return; }
        int length = 0;
        String authorization = "";
        for (int i = 0; i < 24; i++) {
            String header = line(input);
            if (header.isEmpty()) break;
            int split = header.indexOf(':');
            if (split < 0) throw new IOException("Bad header");
            String name = header.substring(0, split).trim();
            String value = header.substring(split + 1).trim();
            if (name.equalsIgnoreCase("Authorization")) authorization = value;
            if (name.equalsIgnoreCase("Content-Length")) length = Integer.parseInt(value);
            if (i == 23) throw new IOException("Too many headers");
        }
        if (!authorization.equals("Bearer " + TOKEN)) {
            reply(socket, 401, "{\"error\":\"unauthorized\"}"); return;
        }
        File pending = new File(directory, "nextdice");
        if (request[0].equals("GET") && request[1].equals("/status")) {
            File applied = new File(directory, "lastdice");
            String last = applied.exists() ? new String(Files.readAllBytes(applied.toPath()), StandardCharsets.US_ASCII).trim() : "";
            JSONObject result = new JSONObject();
            result.put("pending", pending.exists());
            result.put("lastApplied", last.matches("[1-6]") ? Integer.parseInt(last) : JSONObject.NULL);
            result.put("scope", "local pass-and-play");
            result.put("deviceId", deviceId);
            result.put("deviceName", deviceName);
            reply(socket, 200, result.toString()); return;
        }
        if (!request[0].equals("POST") || !request[1].equals("/next")) {
            reply(socket, 404, "{\"error\":\"unknown endpoint\"}"); return;
        }
        if (length < 1 || length > 64) { reply(socket, 400, "{\"error\":\"body length\"}"); return; }
        byte[] body = new byte[length];
        int received = 0;
        while (received < length) {
            int count = input.read(body, received, length - received);
            if (count < 0) throw new EOFException();
            received += count;
        }
        String text = new String(body, StandardCharsets.UTF_8).trim();
        if (!text.matches("[1-6]")) { reply(socket, 400, "{\"error\":\"send one digit from 1 to 6\"}"); return; }
        if (pending.exists()) { reply(socket, 409, "{\"error\":\"a roll is already pending\"}"); return; }
        File temporary = new File(directory, "nextdice.tmp");
        try (FileOutputStream output = new FileOutputStream(temporary)) {
            output.write(text.getBytes(StandardCharsets.US_ASCII));
            output.getFD().sync();
        }
        if (!temporary.renameTo(pending)) throw new IOException("Publish failed");
        Log.i("LocalDiceLAN", "Queued local dice value " + text);
        reply(socket, 200, "{\"queued\":" + text + ",\"appliesTo\":\"next local roll\"}");
    }

    private void reply(Socket socket, int status, String body) throws IOException {
        byte[] bytes = body.getBytes(StandardCharsets.UTF_8);
        OutputStream output = socket.getOutputStream();
        String header = "HTTP/1.1 " + status + " Result\r\nContent-Type: application/json\r\nContent-Length: " + bytes.length + "\r\nConnection: close\r\nCache-Control: no-store\r\n\r\n";
        output.write(header.getBytes(StandardCharsets.US_ASCII));
        output.write(bytes);
        output.flush();
    }

    @Override public Cursor query(Uri u, String[] p, String s, String[] a, String o) { return null; }
    @Override public String getType(Uri u) { return null; }
    @Override public Uri insert(Uri u, ContentValues v) { return null; }
    @Override public int delete(Uri u, String s, String[] a) { return 0; }
    @Override public int update(Uri u, ContentValues v, String s, String[] a) { return 0; }
}
