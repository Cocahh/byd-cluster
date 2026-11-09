package com.luiz.king;

import android.content.Context;
import android.util.Log;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.HashMap;
import java.util.Map;
import org.json.JSONArray;
import org.json.JSONObject;

final class Byd {
    static final String TAG = "King";
    static final String PKG = "android.hardware.bydauto.";
    static final String[] CLASSES = {
        "speed.BYDAutoSpeedDevice", "gearbox.BYDAutoGearboxDevice", "statistic.BYDAutoStatisticDevice", "bodywork.BYDAutoBodyworkDevice",
        "energy.BYDAutoEnergyDevice", "engine.BYDAutoEngineDevice", "ac.BYDAutoAcDevice", "light.BYDAutoLightDevice",
        "instrument.BYDAutoInstrumentDevice", "doorlock.BYDAutoDoorLockDevice", "charging.BYDAutoChargingDevice", "tyre.BYDAutoTyreDevice",
        "setting.BYDAutoSettingDevice", "safetybelt.BYDAutoSafetyBeltDevice", "power.BYDAutoPowerDevice", "sensor.BYDAutoSensorDevice",
        "radar.BYDAutoRadarDevice", "panorama.BYDAutoPanoramaDevice", "motor.BYDAutoMotorDevice", "time.BYDAutoTimeDevice",
        "multimedia.BYDAutoMultimediaDevice", "version.BYDAutoVersionDevice", "collision.BYDAutoCollisionDevice", "adas.BYDAutoADASDevice",
        "audio.BYDAutoAudioDevice", "function.BYDAutoFunctionDevice", "pm2p5.BYDAutoPM2p5Device", "wiper.BYDAutoWiperDevice"
    };
    private static Byd self;
    private final Context ctx;
    private JSONObject map = new JSONObject();
    private final Map<String, Object> devs = new HashMap<>();
    private final Map<String, Object[]> bound = new HashMap<>();
    private final Map<String, Long> failed = new HashMap<>();

    static synchronized Byd get(Context c) {
        if (self == null) self = new Byd(c.getApplicationContext());
        return self;
    }

    private Byd(Context c) { ctx = c; reload(); }

    synchronized void reload() {
        bound.clear(); failed.clear();
        try {
            File f = new File(ctx.getExternalFilesDir(null), "mapping.json");
            InputStream in = f.exists() ? new FileInputStream(f) : ctx.getAssets().open("mapping.json");
            ByteArrayOutputStream o = new ByteArrayOutputStream(); byte[] b = new byte[8192]; int n;
            while ((n = in.read(b)) > 0) o.write(b, 0, n);
            in.close();
            map = new JSONObject(o.toString("UTF-8"));
            Log.i(TAG, "mapping loaded from " + (f.exists() ? "files" : "assets"));
        } catch (Throwable t) { Log.e(TAG, "mapping load failed", t); }
    }

    JSONObject mapping() { return map; }

    private Object dev(String cls) throws Exception {
        Object d = devs.get(cls);
        if (d == null) {
            Class<?> k = Class.forName(PKG + cls);
            d = k.getMethod("getInstance", Context.class).invoke(null, ctx);
            if (d == null) throw new IllegalStateException("no instance " + cls);
            devs.put(cls, d);
        }
        return d;
    }

    private static Method find(Class<?> k, String name, int argc) {
        for (Method m : k.getMethods()) {
            if (!m.getName().equals(name) || m.getParameterTypes().length != argc) continue;
            boolean ok = true;
            for (Class<?> p : m.getParameterTypes()) if (p != int.class) ok = false;
            if (ok) return m;
        }
        return null;
    }

    private static Double num(Object v) {
        if (v instanceof Number) return ((Number) v).doubleValue();
        if (v instanceof Boolean) return ((Boolean) v) ? 1.0 : 0.0;
        return null;
    }

    synchronized Double read(String key) {
        try {
            Object[] b = bound.get(key);
            if (b != null) return num(((Method) b[1]).invoke(b[0], (Object[]) b[2]));
            Long f = failed.get(key);
            if (f != null && System.currentTimeMillis() - f < 30000) return null;
            JSONArray cands = map.getJSONObject("read").optJSONArray(key);
            for (int i = 0; cands != null && i < cands.length(); i++) {
                JSONObject c = cands.getJSONObject(i);
                try {
                    Object d = dev(c.getString("c"));
                    JSONArray a = c.optJSONArray("a");
                    Object[] args = new Object[a == null ? 0 : a.length()];
                    for (int j = 0; j < args.length; j++) args[j] = a.getInt(j);
                    Method m = find(d.getClass(), c.getString("m"), args.length);
                    if (m == null) continue;
                    Double v = num(m.invoke(d, args));
                    if (v == null) continue;
                    bound.put(key, new Object[] { d, m, args });
                    Log.i(TAG, key + " bound to " + c.getString("c") + "." + c.getString("m") + " = " + v);
                    return v;
                } catch (Throwable t) { Log.w(TAG, key + " candidate failed: " + c + " " + t); }
            }
            failed.put(key, System.currentTimeMillis());
        } catch (Throwable t) {
            bound.remove(key); failed.put(key, System.currentTimeMillis());
            Log.w(TAG, "read " + key + " failed " + t);
        }
        return null;
    }

    String gear() {
        Double g = read("gear");
        if (g == null) return null;
        JSONObject gm = map.optJSONObject("gearMap");
        return gm == null ? null : gm.optString(String.valueOf(g.intValue()), null);
    }

    synchronized boolean setWindow(String id, boolean open) {
        try {
            JSONObject w = map.getJSONObject("write").getJSONObject("window");
            if (!w.optBoolean("enabled", false)) return false;
            Object d = dev(w.getString("c"));
            Method m = find(d.getClass(), w.getString("m"), 2);
            if (m == null) return false;
            m.invoke(d, w.getJSONObject("area").getInt(id), w.getInt(open ? "open" : "close"));
            return true;
        } catch (Throwable t) { Log.w(TAG, "setWindow failed " + t); return false; }
    }

    File probe() {
        JSONObject out = new JSONObject();
        for (String cls : CLASSES) {
            JSONObject o = new JSONObject();
            try {
                Class<?> k = Class.forName(PKG + cls);
                JSONObject fields = new JSONObject();
                for (Field f : k.getFields()) {
                    if (!Modifier.isStatic(f.getModifiers())) continue;
                    try { fields.put(f.getName(), String.valueOf(f.get(null))); } catch (Throwable t) { fields.put(f.getName(), "?"); }
                }
                o.put("fields", fields);
                JSONArray methods = new JSONArray(); JSONObject values = new JSONObject();
                Object d = null;
                try { d = dev(cls); } catch (Throwable t) { o.put("instanceError", String.valueOf(t)); }
                for (Method m : k.getDeclaredMethods()) {
                    if (!Modifier.isPublic(m.getModifiers())) continue;
                    StringBuilder sig = new StringBuilder(m.getReturnType().getSimpleName()).append(' ').append(m.getName()).append('(');
                    Class<?>[] ps = m.getParameterTypes();
                    for (int i = 0; i < ps.length; i++) sig.append(i > 0 ? "," : "").append(ps[i].getSimpleName());
                    methods.put(sig.append(')').toString());
                    String n = m.getName();
                    boolean getter = (n.startsWith("get") || n.startsWith("is") || n.startsWith("has")) && !n.equals("getInstance");
                    Class<?> r = m.getReturnType();
                    boolean simple = r.isPrimitive() || r == String.class;
                    if (d == null || !getter || !simple || r == void.class) continue;
                    try {
                        if (ps.length == 0) values.put(n, String.valueOf(m.invoke(d)));
                        else if (ps.length == 1 && ps[0] == int.class) {
                            JSONObject per = new JSONObject();
                            for (int a = 0; a <= 12; a++) { try { per.put(String.valueOf(a), String.valueOf(m.invoke(d, a))); } catch (Throwable t) { per.put(String.valueOf(a), "!"); } }
                            values.put(n, per);
                        }
                    } catch (Throwable t) { values.put(n, "! " + (t.getCause() != null ? t.getCause() : t)); }
                }
                o.put("methods", methods); o.put("values", values);
            } catch (ClassNotFoundException e) { try { o.put("missing", true); } catch (Throwable ignored) { }
            } catch (Throwable t) { try { o.put("error", String.valueOf(t)); } catch (Throwable ignored) { } }
            try { out.put(cls, o); } catch (Throwable ignored) { }
        }
        File f = new File(ctx.getExternalFilesDir(null), "probe.json");
        try { FileOutputStream w = new FileOutputStream(f); w.write(out.toString(1).getBytes("UTF-8")); w.close(); Log.i(TAG, "probe written " + f); } catch (Throwable t) { Log.e(TAG, "probe write failed", t); }
        return f;
    }
}
