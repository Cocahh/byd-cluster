import json, math, sys
import numpy as np
from PIL import Image
sys.argv = ["x"]; src = open("compose4.py").read().split("LEFT = lookup")[0]
exec(src)
OUT = "/Users/luizleite/Projects/byd-cluster/panel/assets/home"
meta = json.load(open(f"{OUT}/meta.json"))
box = [141, 263, 1460, 804]
cx = (box[0]+box[2])/2; hw = max(cx-box[0], box[2]-cx); box[0] = int(cx-hw); box[2] = int(cx+hw)
SC = 1280 / (box[2]-box[0]); FW, FH = meta["fw"], meta["fh"]
def proj(i, p):
    pos, f, r, u = cam(i); d = np.array(p) - pos; z = d @ f
    return W/2 + (d @ r)/z/TF*(H/2), H/2 - (d @ u)/z/TF*(H/2)
a = np.asarray(Image.open(f"{D}/w_12.png").convert("L")); ys, xs = np.nonzero(a > 60); yb = ys.max(); xb = xs[ys == yb].mean()
pos, f, r, u = cam(12); nx = (xb - W/2)/(H/2)*TF; ny = (H/2 - yb)/(H/2)*TF; d = f + nx*r + ny*u; t = (0.0082 - pos[0])/d[0]
ZG = float(pos[2] + t*d[2]); print("ground z", ZG, "y", pos[1] + t*d[1])
ANCH = [("f", (0.006, -0.0222, 0.0068)), ("f", (-0.006, -0.0222, 0.0068)), ("f", (0, -0.0236, 0.0066)), ("r", (0, 0.0236, 0.0092)), ("r", (0.007, 0.0228, 0.0092)), ("r", (-0.007, 0.0228, 0.0092)), ("r", (0.006, 0.0236, 0.0035)), ("r", (-0.006, 0.0236, 0.0035)), ("t", (0, 0.0125, 0.0138)), ("m", (0.0102, -0.0062, 0.0106)), ("m", (-0.0102, -0.0062, 0.0106))]
def tone(rgb):
    rgb = rgb.astype(np.float32); l = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    return l
for i in range(N):
    lm = np.asarray(Image.open(f"{D}/l_{i:02d}.png").convert("RGB"))[:, :, 1].astype(np.float32)/255
    lab = comps(lm > 0.5)
    c = np.asarray(Image.open(f"{D}/c_{i:02d}.png").convert("RGB")); lum = tone(c)
    al = np.asarray(Image.open(f"{D}/w_{i:02d}.png").convert("L")).astype(np.float32); al = np.clip(al/110, 0, 1)
    rgb = np.zeros((H, W, 3), np.float32); A = np.zeros((H, W), np.float32); kinds = []
    pts = [(k, proj(i, p)) for k, p in ANCH]
    for k in np.unique(lab):
        if not k: continue
        sel = lab == k
        if sel.sum() < 120: continue
        ys, xs = np.nonzero(sel); mx, my = xs.mean(), ys.mean()
        kind = min(pts, key=lambda q: (q[1][0]-mx)**2 + (q[1][1]-my)**2)[0]
        kinds.append(kind)
        if kind == "m": continue
        L = lum[sel]
        if kind == "f":
            v = np.clip(L*2.6 + 95, 0, 255); rgb[sel] = v[:, None]*np.array([0.94, 0.97, 1.0])
        else:
            v = np.clip(L*3.0 + 120, 0, 255); rgb[sel] = np.stack([v, v*0.13 + 6, v*0.09 + 4], 1)
        A[sel] = 1
    A = A*lm*al
    im = Image.fromarray(np.dstack([rgb, A[:, :, None]*255]).astype(np.uint8), "RGBA").crop(box).resize((FW, FH), Image.LANCZOS)
    im.save(f"{OUT}/e{i:02d}.webp", quality=82, method=6)
    print(i, "".join(kinds), flush=True)
meta.update({"zg": ZG, "box": [int(b) for b in box], "sc": SC, "r": R, "el": 9, "tz": TZ, "tf": TF})
json.dump(meta, open(f"{OUT}/meta.json", "w"))
