package com.luiz.king;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.util.Log;
import android.view.View;
import android.view.WindowManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import org.json.JSONArray;
import org.json.JSONObject;

public class HomeActivity extends Activity {
    private WebView web;
    private Byd byd;
    private boolean ready;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private final Runnable tick = this::tick;
    private void tick() { push(); ui.postDelayed(tick, 400); }
    private static final class Client extends WebViewClient {
        private final HomeActivity a;
        Client(HomeActivity a) { this.a = a; }
        @Override public void onPageFinished(WebView v, String u) { a.ready = true; a.push(); }
    }

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        byd = Byd.get(this);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        web = new WebView(this);
        web.setBackgroundColor(Color.BLACK);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true); s.setAllowFileAccess(true); s.setMediaPlaybackRequiresUserGesture(false);
        web.setOverScrollMode(View.OVER_SCROLL_NEVER);
        web.setVerticalScrollBarEnabled(false); web.setHorizontalScrollBarEnabled(false);
        web.addJavascriptInterface(new Bridge(this), "KingHost");
        web.setWebViewClient(new Client(this));
        setContentView(web);
        web.loadUrl("file:///android_asset/king-home.html#car");
        handle(getIntent());
        try { startService(new Intent(this, ClusterService.class)); } catch (Throwable t) { Log.w(Byd.TAG, "cluster service not started " + t); }
    }

    @Override protected void onNewIntent(Intent i) { super.onNewIntent(i); handle(i); if (ready) web.evaluateJavascript("document.getElementById('h').classList.remove('setopen')", null); }

    private void handle(Intent i) {
        if (i == null) return;
        if (i.getBooleanExtra("reload", false)) { byd.reload(); Toast.makeText(this, "King mapping reloaded", Toast.LENGTH_SHORT).show(); }
        if (i.getBooleanExtra("probe", false)) new Thread(() -> byd.probe()).start();
    }

    @Override protected void onResume() {
        super.onResume();
        immersive();
        ui.removeCallbacks(tick); ui.post(tick);
    }

    @Override protected void onPause() { super.onPause(); ui.removeCallbacks(tick); }

    @Override public void onWindowFocusChanged(boolean f) { super.onWindowFocusChanged(f); if (f) immersive(); }

    @Override public void onBackPressed() { if (ready) web.evaluateJavascript("document.getElementById('h').classList.remove('setopen')", null); }

    private void immersive() {
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_LAYOUT_STABLE | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN | View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY);
    }

    private static void put(JSONObject o, String k, Double v) throws Exception { if (v != null && !v.isNaN()) o.put(k, v); }

    private void push() {
        if (!ready) return;
        try {
            JSONObject o = new JSONObject();
            Date now = new Date();
            o.put("clock", new SimpleDateFormat("HH:mm", Locale.US).format(now));
            o.put("date", new SimpleDateFormat("EEEE, d MMMM", Locale.US).format(now));
            o.put("day", new SimpleDateFormat("d MMM", Locale.US).format(now));
            put(o, "outsideC", byd.read("outsideC")); put(o, "soc", byd.read("soc")); put(o, "fuelPct", byd.read("fuelPct"));
            Double ev = byd.read("evRangeKm"), fr = byd.read("fuelRangeKm");
            put(o, "evRangeKm", ev);
            if (ev != null && fr != null) o.put("totalRangeKm", ev + fr);
            Double sp = byd.read("speed"); String g = byd.gear();
            o.put("parked", g != null ? "P".equals(g) : sp != null && sp < 0.5);
            o.put("carplay", "unknown");
            o.put("cluster", ClusterService.showing);
            Double fl = byd.read("winFL"), frr = byd.read("winFR"), rl = byd.read("winRL"), rr = byd.read("winRR");
            if (fl != null && frr != null && rl != null && rr != null) {
                JSONObject w = new JSONObject(); w.put("fl", fl); w.put("fr", frr); w.put("rl", rl); w.put("rr", rr); o.put("windows", w);
            }
            web.evaluateJavascript("window.KingHome&&KingHome.update(" + o + ")", null);
        } catch (Throwable t) { Log.w(Byd.TAG, "push failed " + t); }
    }

    private boolean launch(String pkg) {
        Intent i = getPackageManager().getLaunchIntentForPackage(pkg);
        if (i == null) return false;
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try { startActivity(i); return true; } catch (Throwable t) { return false; }
    }

    private void openApp(String app) {
        try {
            if ("bydhome".equals(app)) {
                Intent h = new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME);
                List<ResolveInfo> l = getPackageManager().queryIntentActivities(h, PackageManager.MATCH_DEFAULT_ONLY);
                for (ResolveInfo r : l) {
                    if (r.activityInfo.packageName.equals(getPackageName())) continue;
                    startActivity(new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME).setComponent(new ComponentName(r.activityInfo.packageName, r.activityInfo.name)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK));
                    return;
                }
            }
            JSONArray c = byd.mapping().getJSONObject("apps").optJSONArray(app);
            for (int i = 0; c != null && i < c.length(); i++) if (launch(c.getString(i))) return;
            if ("browser".equals(app)) { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("https://www.youtube.com")).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); return; }
            if ("settings".equals(app)) { startActivity(new Intent(Settings.ACTION_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)); return; }
            Toast.makeText(this, "Could not find an app for " + app, Toast.LENGTH_SHORT).show();
        } catch (Throwable t) { Toast.makeText(this, "Could not open " + app, Toast.LENGTH_SHORT).show(); Log.w(Byd.TAG, "openApp " + app + " " + t); }
    }

    static final class Bridge {
        private final HomeActivity a;
        Bridge(HomeActivity a) { this.a = a; }
        @JavascriptInterface public void openApp(final String app) { a.ui.post(() -> a.openApp(app)); }
        @JavascriptInterface public boolean setWindow(String id, String cmd) { return a.byd.setWindow(id, "open".equals(cmd)); }
        @JavascriptInterface public void flashLights() { }
        @JavascriptInterface public void setTheme(String name) { ClusterService.theme = name; ClusterService.applyTheme(); }
        @JavascriptInterface public void setCluster(final boolean on) { ClusterService.wanted = on; a.ui.post(ClusterService::refresh); }
    }
}
