import json, math, sys
import numpy as np
from PIL import Image
D = "out/h4"; OUT = "/Users/luizleite/Projects/byd-cluster/panel/assets/home"
import os; os.makedirs(OUT, exist_ok=True)
N = 48; R = 0.2; EL = math.radians(9); TZ = 0.0076; W, H = 1600, 1000
TF = math.tan(math.radians(10.669) / 2); XW = 0.0078
def cam(i):
    a = math.radians(i * 360 / N)
    pos = np.array([R*math.cos(EL)*math.sin(a), -R*math.cos(EL)*math.cos(a), TZ + R*math.sin(EL)])
    f = np.array([0, 0, TZ]) - pos; f /= np.linalg.norm(f)
    r = np.cross(f, [0, 0, 1.0]); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return pos, f, r, u
def cast(i, ys, xs, side):
    pos, f, r, u = cam(i)
    nx = (xs - W/2) / (H/2) * TF; ny = (H/2 - ys) / (H/2) * TF
    d = f[None, :] + nx[:, None]*r[None, :] + ny[:, None]*u[None, :]
    t = (side*XW - pos[0]) / d[:, 0]
    return pos[1] + t*d[:, 1], pos[2] + t*d[:, 2]
def glass(i):
    return np.asarray(Image.open(f"{D}/g_{i:02d}.png").convert("RGB"))[:, :, 2].astype(np.float32) / 255
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
    lut = np.array([find(k) for k in range(len(parent))], np.int32)
    return lut[lab]
G = 0.0001; GY0, GZ0 = -0.03, 0.0; GW, GH = 600, 200
def lookup(i, side, picks):
    m = glass(i) > 0.5; lab = comps(m)
    ids = [k for k in np.unique(lab) if k and (lab == k).sum() > 800]
    ids.sort(key=lambda k: np.nonzero(lab == k)[1].mean())
    print("side", i, [(int((lab == k).sum()), int(np.nonzero(lab == k)[1].mean())) for k in ids])
    grid = np.zeros((GH, GW), np.uint8)
    for wid, idx in picks:
        ys, xs = np.nonzero(lab == ids[idx])
        yy, zz = cast(i, ys.astype(np.float64), xs.astype(np.float64), side)
        gx = np.clip(((yy - GY0)/G).astype(int), 0, GW-1); gz = np.clip(((zz - GZ0)/G).astype(int), 0, GH-1)
        grid[gz, gx] = wid
    for _ in range(3):
        g2 = grid.copy()
        for dy, dx in ((0,1),(0,-1),(1,0),(-1,0)):
            s = np.roll(grid, (dy, dx), (0, 1)); g2[(g2 == 0) & (s > 0)] = s[(g2 == 0) & (s > 0)]
        grid = g2
    return grid
LEFT = lookup(12, 1, [(1, 1), (3, 2)])
RIGHT = lookup(36, -1, [(4, 2), (2, 3)])
box = [W, H, 0, 0]; alphas = []
for i in range(N):
    a = np.asarray(Image.open(f"{D}/w_{i:02d}.png").convert("L")).astype(np.float32)
    a = np.clip(a / 110, 0, 1); alphas.append(a)
    ys, xs = np.nonzero(a > 0.03)
    box = [min(box[0], xs.min()), min(box[1], ys.min()), max(box[2], xs.max()+1), max(box[3], ys.max()+1)]
box = [box[0]-10, box[1]-10, box[2]+10, box[3]+10]
cx = (box[0]+box[2])/2; hw = max(cx-box[0], box[2]-cx); box[0] = int(cx-hw); box[2] = int(cx+hw)
print("box", box)
SC = 1280 / (box[2]-box[0]); FW = 1280; FH = int(round((box[3]-box[1])*SC/2))*2; MS = 0.5
def tone(rgb):
    rgb = rgb.astype(np.float32); l = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    red = np.clip((rgb[:, :, 0] - 1.7*np.maximum(rgb[:, :, 1], rgb[:, :, 2]) - 18) / 40, 0, 1)[:, :, None]
    cool = l[:, :, None] * np.array([0.97, 1.0, 1.05], np.float32)
    mix = cool*0.86 + rgb*0.14
    return np.clip(mix*(1-red) + rgb*red, 0, 255)
meta = []
for i in range(N):
    pos = cam(i)[0]; gl = glass(i); lab = comps(gl > 0.5); idmap = np.zeros((H, W), np.uint8)
    for k in np.unique(lab):
        if not k: continue
        sel = lab == k; n = sel.sum()
        if n < 150: continue
        ys, xs = np.nonzero(sel)
        for side, grid, ok in ((1, LEFT, pos[0] > 0.02), (-1, RIGHT, pos[0] < -0.02)):
            if not ok: continue
            yy, zz = cast(i, ys.astype(np.float64), xs.astype(np.float64), side)
            gx = ((yy - GY0)/G).astype(int); gz = ((zz - GZ0)/G).astype(int)
            inb = (gx >= 0) & (gx < GW) & (gz >= 0) & (gz < GH)
            v = np.zeros(n, np.uint8); v[inb] = grid[gz[inb], gx[inb]]
            cnt = np.bincount(v, minlength=5)
            best = cnt[1:].argmax() + 1
            if cnt[best] > 0.55*n: idmap[sel] = best
    for _ in range(5):
        m2 = idmap.copy()
        for dy, dx in ((0,1),(0,-1),(1,0),(-1,0)):
            s = np.roll(idmap, (dy, dx), (0, 1)); m2[(m2 == 0) & (s > 0)] = s[(m2 == 0) & (s > 0)]
        idmap = m2
    a = alphas[i]
    c = tone(np.asarray(Image.open(f"{D}/c_{i:02d}.png").convert("RGB")))
    o = tone(np.asarray(Image.open(f"{D}/o_{i:02d}.png").convert("RGB")))
    def out(rgb, al, name, q):
        im = Image.fromarray(np.dstack([rgb, al[:, :, None]*255]).astype(np.uint8), "RGBA").crop(box).resize((FW, FH), Image.LANCZOS)
        im.save(f"{OUT}/{name}", quality=q, method=6)
    out(c, a, f"c{i:02d}.webp", 84)
    out(o, a * gl * (idmap > 0), f"o{i:02d}.webp", 80)
    mi = Image.fromarray(idmap * 60, "L").crop(box).resize((int(FW*MS), int(FH*MS)), Image.NEAREST)
    mi.save(f"{OUT}/m{i:02d}.png", optimize=True)
    meta.append([int((idmap == k).sum()) for k in (1, 2, 3, 4)])
    print(i, meta[-1], flush=True)
json.dump({"n": N, "fw": FW, "fh": FH, "ms": MS}, open(f"{OUT}/meta.json", "w"))
