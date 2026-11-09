import json, math, os, sys
import numpy as np
from PIL import Image
D_ = "out/h6"; OUT = "/Users/luizleite/Projects/byd-cluster/panel/assets/home"
N = 48; DIST = 0.075; HC = 0.016; TZ = 0.007; W, H = 1600, 1000
TF = math.tan(math.radians(27.75)/2); FR = (H/2)/TF; XW = 0.0078; PPM = 215.0
SC = PPM/(FR*0.01/DIST)
def cam(i):
    a = math.radians(i*360/N)
    pos = np.array([DIST*math.sin(a), -DIST*math.cos(a), HC])
    f = np.array([0, 0, TZ]) - pos; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r)
    return pos, f, r, np.cross(r, f)
def cast(i, ys, xs, side):
    pos, f, r, u = cam(i)
    d = f[None, :]*FR + (xs - W/2)[:, None]*r[None, :] + (H/2 - ys)[:, None]*u[None, :]
    t = (side*XW - pos[0])/d[:, 0]
    return pos[1] + t*d[:, 1], pos[2] + t*d[:, 2]
def proj(i, p):
    pos, f, r, u = cam(i); d = np.array(p) - pos; z = d @ f
    return W/2 + (d @ r)/z*FR, H/2 - (d @ u)/z*FR
def ch(i, p, c): return np.asarray(Image.open(f"{D_}/{p}_{i:02d}.png").convert("RGB"))[:, :, c].astype(np.float32)/255
def comps(mask):
    lab = np.zeros(mask.shape, np.int32); parent = [0]
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    prev = []
    for y in range(mask.shape[0]):
        row = mask[y]; cur = []
        if row.any():
            d = np.diff(np.concatenate(([0], row.view(np.int8), [0])))
            for s, e in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
                l = 0
                for ps, pe, pl in prev:
                    if ps < e and pe > s:
                        pl = find(pl)
                        if l == 0: l = pl
                        elif l != pl: parent[max(l, pl)] = min(l, pl); l = min(l, pl)
                if l == 0: parent.append(len(parent)); l = len(parent) - 1
                cur.append((s, e, l)); lab[y, s:e] = l
        prev = cur
    return np.array([find(k) for k in range(len(parent))], np.int32)[lab]
G = 0.0001; GY0 = -0.03; GW, GH = 600, 200
def lookup(i, side, picks):
    lab = comps(ch(i, "g", 2) > 0.5)
    ids = [k for k in np.unique(lab) if k and (lab == k).sum() > 800]
    ids.sort(key=lambda k: np.nonzero(lab == k)[1].mean())
    print("side", i, [(int((lab == k).sum()), int(np.nonzero(lab == k)[1].mean())) for k in ids])
    grid = np.zeros((GH, GW), np.uint8)
    for wid, idx in picks:
        ys, xs = np.nonzero(lab == ids[idx])
        yy, zz = cast(i, ys.astype(np.float64), xs.astype(np.float64), side)
        grid[np.clip((zz/G).astype(int), 0, GH-1), np.clip(((yy - GY0)/G).astype(int), 0, GW-1)] = wid
    for _ in range(4):
        g2 = grid.copy()
        for dy, dx in ((0,1),(0,-1),(1,0),(-1,0)):
            s = np.roll(grid, (dy, dx), (0, 1)); g2[(g2 == 0) & (s > 0)] = s[(g2 == 0) & (s > 0)]
        grid = g2
    return grid
LEFT = lookup(12, 1, [(1, 1), (3, 2)]); RIGHT = lookup(36, -1, [(4, 2), (2, 3)])
box = [W, H, 0, 0]; alphas = []
for i in range(N):
    a = np.clip(np.asarray(Image.open(f"{D_}/w_{i:02d}.png").convert("L")).astype(np.float32)/110, 0, 1); alphas.append(a)
    ys, xs = np.nonzero(a > 0.03); box = [min(box[0], xs.min()), min(box[1], ys.min()), max(box[2], xs.max()+1), max(box[3], ys.max()+1)]
hw = max(W/2 - box[0], box[2] - W/2) + 10; box = [int(W/2 - hw), int(box[1] - 10), int(W/2 + hw), int(box[3] + 10)]
FW = int(round((box[2]-box[0])*SC/2))*2; FH = int(round((box[3]-box[1])*SC/2))*2; MS = 0.5
print("box", box, FW, FH, SC)
def tone(rgb):
    rgb = rgb.astype(np.float32); l = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    red = np.clip((rgb[:, :, 0] - 1.7*np.maximum(rgb[:, :, 1], rgb[:, :, 2]) - 18)/40, 0, 1)[:, :, None]
    mix = l[:, :, None]*np.array([0.97, 1.0, 1.05], np.float32)*0.86 + rgb*0.14
    return np.clip(mix*(1-red) + rgb*red, 0, 255)
ANCH = [("f", (0.006, -0.0222, 0.0068)), ("f", (-0.006, -0.0222, 0.0068)), ("f", (0, -0.0236, 0.0066)), ("r", (0, 0.0236, 0.0092)), ("r", (0.007, 0.0228, 0.0092)), ("r", (-0.007, 0.0228, 0.0092)), ("r", (0.006, 0.0236, 0.0035)), ("r", (-0.006, 0.0236, 0.0035)), ("r", (0, 0.0125, 0.0138)), ("m", (0.0102, -0.0062, 0.0106)), ("m", (-0.0102, -0.0062, 0.0106))]
def save(rgb, al, name, q):
    Image.fromarray(np.dstack([rgb, al[:, :, None]*255]).clip(0, 255).astype(np.uint8), "RGBA").crop(box).resize((FW, FH), Image.LANCZOS).save(f"{OUT}/{name}", quality=q, method=6)
for f in os.listdir(OUT):
    if f[0] in "comen" and f[1:3].isdigit(): os.remove(f"{OUT}/{f}")
for i in range(N):
    pos = cam(i)[0]; gl = ch(i, "g", 2); lab = comps(gl > 0.5); idmap = np.zeros((H, W), np.uint8)
    for k in np.unique(lab):
        if not k: continue
        sel = lab == k; n = sel.sum()
        if n < 150: continue
        ys, xs = np.nonzero(sel)
        for side, grid, ok in ((1, LEFT, pos[0] > 0.008), (-1, RIGHT, pos[0] < -0.008)):
            if not ok: continue
            yy, zz = cast(i, ys.astype(np.float64), xs.astype(np.float64), side)
            gx = ((yy - GY0)/G).astype(int); gz = (zz/G).astype(int)
            inb = (gx >= 0) & (gx < GW) & (gz >= 0) & (gz < GH)
            v = np.zeros(n, np.uint8); v[inb] = grid[gz[inb], gx[inb]]
            cnt = np.bincount(v, minlength=5); best = cnt[1:].argmax() + 1
            if cnt[best] > 0.55*n: idmap[sel] = best
    for _ in range(5):
        m2 = idmap.copy()
        for dy, dx in ((0,1),(0,-1),(1,0),(-1,0)):
            s = np.roll(idmap, (dy, dx), (0, 1)); m2[(m2 == 0) & (s > 0)] = s[(m2 == 0) & (s > 0)]
        idmap = m2
    a = alphas[i]
    craw = np.asarray(Image.open(f"{D_}/c_{i:02d}.png").convert("RGB")); c = tone(craw)
    o = tone(np.asarray(Image.open(f"{D_}/o_{i:02d}.png").convert("RGB")))
    save(c, a, f"c{i:02d}.webp", 84)
    save(o, a*gl*(idmap > 0), f"o{i:02d}.webp", 80)
    Image.fromarray(idmap*60, "L").crop(box).resize((int(FW*MS), int(FH*MS)), Image.NEAREST).save(f"{OUT}/m{i:02d}.png", optimize=True)
    lm = ch(i, "l", 1); llab = comps(lm > 0.5); lum = craw.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)
    rgb = np.zeros((H, W, 3), np.float32); A = np.zeros((H, W), np.float32); pts = [(k, proj(i, p)) for k, p in ANCH]; kinds = ""
    for k in np.unique(llab):
        if not k: continue
        sel = llab == k
        if sel.sum() < 120: continue
        ys, xs = np.nonzero(sel); mx, my = xs.mean(), ys.mean()
        kind = min(pts, key=lambda q: (q[1][0]-mx)**2 + (q[1][1]-my)**2)[0]; kinds += kind
        if kind == "m": continue
        L = lum[sel]
        if kind == "f": v = np.clip(L*2.6 + 95, 0, 255); rgb[sel] = v[:, None]*np.array([0.94, 0.97, 1.0])
        else: v = np.clip(L*3.0 + 120, 0, 255); rgb[sel] = np.stack([v, v*0.13 + 6, v*0.09 + 4], 1)
        A[sel] = 1
    save(rgb, A*lm*a, f"e{i:02d}.webp", 82)
    sv = np.asarray(Image.open(f"{D_}/s_{i:02d}.png").convert("L")).astype(np.float32)/255
    sa = np.clip((sv - 0.80)/0.14, 0, 1); sa = sa*sa*(3 - 2*sa)
    sa = sa*a*(1 - np.clip(gl*1.4, 0, 1))*(1 - np.clip(lm*2, 0, 1))
    shade = np.clip((sv - 0.8)/0.2, 0, 1)[:, :, None]
    srgb = (np.array([176, 190, 212], np.float32)*(1 - shade) + np.array([246, 249, 255], np.float32)*shade)
    save(srgb, sa*0.96, f"n{i:02d}.webp", 84)
    print(i, [int((idmap == k).sum()) for k in (1, 2, 3, 4)], kinds, round(float(sa.mean()), 3), flush=True)
json.dump({"n": N, "fw": FW, "fh": FH, "ms": MS, "box": box, "sc": SC, "dist": DIST*100, "hc": HC*100, "tz": TZ*100, "f": PPM*DIST*100, "cx": 676, "cy": 690}, open(f"{OUT}/meta.json", "w"))
