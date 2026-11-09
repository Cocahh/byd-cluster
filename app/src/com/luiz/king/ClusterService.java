package com.luiz.king;

import android.app.Presentation;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.hardware.display.DisplayManager;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.provider.Settings;
import android.util.Log;
import android.view.Display;
import android.view.View;
import android.view.WindowManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import org.json.JSONArray;
import org.json.JSONObject;

public class ClusterService extends Service implements DisplayManager.DisplayListener {
    static volatile boolean showing;
    static volatile boolean wanted = true;
    static volatile String theme = "standard";
    private static ClusterService self;
    private final Handler ui = new Handler(Looper.getMainLooper());
    private DisplayManager dm;
    private Byd byd;
    private Presentation pres;
    private WebView web;
    private boolean ready;
    private int misses;
    private final Runnable tick = this::tick;
    private void tick() { push(); ui.postDelayed(tick, 100); }
    private String themeJs() { return "KingPanel.setTheme('" + theme.replaceAll("[^a-z]", "") + "')"; }
    private static final class Client extends WebViewClient {
        private final ClusterService s;
        Client(ClusterService s) { this.s = s; }
        @Override public void onPageFinished(WebView v, String u) { s.ready = true; v.evaluateJavascript(s.themeJs() + ";KingPanel.start()", null); }
    }
    private static final class Panel extends Presentation {
        private final ClusterService s;
        Panel(ClusterService s, Display d) { super(s, d); this.s = s; }
        @Override protected void onCreate(Bundle b) {
            super.onCreate(b);
            WebView w = new WebView(getContext());
            w.setBackgroundColor(Color.BLACK);
            WebSettings ws = w.getSettings();
            ws.setJavaScriptEnabled(true); ws.setDomStorageEnabled(true); ws.setAllowFileAccess(true);
            w.setOverScrollMode(View.OVER_SCROLL_NEVER);
            w.setWebViewClient(new Client(s));
            setContentView(w);
            s.web = w;
            w.loadUrl("file:///android_asset/king-road.html#car");
        }
    }

    static void refresh() { if (self != null) self.check(); }
    static void applyTheme() { final ClusterService s = self; if (s != null) s.ui.post(s::pushTheme); }
    private void pushTheme() { if (ready && web != null) web.evaluateJavascript(themeJs(), null); }

    @Override public IBinder onBind(Intent i) { return null; }

    @Override public void onCreate() {
        super.onCreate();
        self = this; byd = Byd.get(this);
        dm = (DisplayManager) getSystemService(Context.DISPLAY_SERVICE);
        dm.registerDisplayListener(this, ui);
        check();
    }

    @Override public int onStartCommand(Intent i, int f, int id) { check(); return START_STICKY; }
    @Override public void onDestroy() { dm.unregisterDisplayListener(this); hide(); self = null; super.onDestroy(); }
    @Override public void onDisplayAdded(int id) { check(); }
    @Override public void onDisplayRemoved(int id) { check(); }
    @Override public void onDisplayChanged(int id) { }

    private Display target() {
        JSONArray names = null;
        try { names = byd.mapping().getJSONObject("cluster").getJSONArray("displayName"); } catch (Throwable ignored) { }
        for (Display d : dm.getDisplays()) {
            if (d.getDisplayId() == Display.DEFAULT_DISPLAY) continue;
            String n = String.valueOf(d.getName()).toLowerCase(Locale.US);
            for (int i = 0; names != null && i < names.length(); i++) if (n.contains(names.optString(i).toLowerCase(Locale.US))) return d;
        }
        return null;
    }

    private void check() {
        Display d = target();
        Log.i(Byd.TAG, "cluster check: display=" + (d == null ? "none" : d.getName()) + " wanted=" + wanted);
        if (d == null || !wanted) { hide(); return; }
        if (pres != null && pres.getDisplay().getDisplayId() == d.getDisplayId()) return;
        hide();
        boolean need = true;
        try { need = byd.mapping().getJSONObject("cluster").optBoolean("requireSpeed", true); } catch (Throwable ignored) { }
        if (need && byd.read("speed") == null) { Log.w(Byd.TAG, "speed is not readable, leaving the driver display alone"); return; }
        if (Build.VERSION.SDK_INT >= 23 && !Settings.canDrawOverlays(this)) { Log.w(Byd.TAG, "overlay permission missing"); return; }
        try {
            pres = new Panel(this, d);
            pres.getWindow().setType(Build.VERSION.SDK_INT >= 26 ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY : WindowManager.LayoutParams.TYPE_SYSTEM_ALERT);
            pres.show();
            showing = true; misses = 0;
            ui.removeCallbacks(tick); ui.post(tick);
            Log.i(Byd.TAG, "driver display shown on " + d.getName());
        } catch (Throwable t) { Log.e(Byd.TAG, "could not show on driver display", t); hide(); }
    }

    private void hide() {
        ui.removeCallbacks(tick);
        if (pres != null) { try { pres.dismiss(); } catch (Throwable ignored) { } }
        pres = null; web = null; ready = false; showing = false;
    }

    private static void put(JSONObject o, String k, Double v, double def) throws Exception { o.put(k, v == null || v.isNaN() ? def : v); }

    private void push() {
        if (!ready || web == null) return;
        try {
            Double sp = byd.read("speed");
            if (sp == null) {
                if (++misses == 10) web.evaluateJavascript("KingPanel.fault(true)", null);
                return;
            }
            if (misses >= 10) web.evaluateJavascript("KingPanel.fault(false)", null);
            misses = 0;
            JSONObject o = new JSONObject();
            o.put("speed", sp);
            String g = byd.gear(); o.put("gear", g == null ? "D" : g);
            Double rpm = byd.read("rpm"); o.put("engineOn", rpm != null && rpm > 300);
            put(o, "powerKw", byd.read("powerKw"), 0); put(o, "soc", byd.read("soc"), 0); put(o, "fuelPct", byd.read("fuelPct"), 0);
            Double ev = byd.read("evRangeKm"), fr = byd.read("fuelRangeKm");
            put(o, "evRangeKm", ev, 0); o.put("totalRangeKm", (ev == null ? 0 : ev) + (fr == null ? 0 : fr));
            put(o, "odoKm", byd.read("odoKm"), 0); o.put("tripKm", 0); o.put("tripL100", 0); o.put("tripKwh100", 0);
            put(o, "outsideC", byd.read("outsideC"), 0);
            o.put("clock", new SimpleDateFormat("HH:mm", Locale.US).format(new Date()));
            Double tl = byd.read("turnL"), tr = byd.read("turnR");
            o.put("turnL", tl != null && tl > 0); o.put("turnR", tr != null && tr > 0);
            o.put("warnings", new JSONArray());
            web.evaluateJavascript("KingPanel.update(" + o + ")", null);
        } catch (Throwable t) { Log.w(Byd.TAG, "cluster push failed " + t); }
    }
}
