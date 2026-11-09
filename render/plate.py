import sys, math
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
D, HC, TZ = 7.5, 1.6, 0.7
PITCH = math.atan2(HC - TZ, D)
def view(name, yaw_deg, W=1360, H=1200, cx=676, cy=690, F=1612.5, ss=1):
    src = np.asarray(Image.open(name + ".jpg").convert("RGB"))
    sh, sw = src.shape[:2]
    xs, ys = np.meshgrid((np.arange(W*ss) + 0.5)/ss, (np.arange(H*ss) + 0.5)/ss)
    cp, sp = math.cos(PITCH), math.sin(PITCH)
    f = np.array([0, cp, -sp]); r = np.array([1.0, 0, 0]); u = np.array([0, sp, cp])
    d = f[None, None, :]*F + r[None, None, :]*(xs - cx)[:, :, None] + u[None, None, :]*(cy - ys)[:, :, None]
    lon = np.arctan2(d[:, :, 0], d[:, :, 1]) + math.radians(yaw_deg)
    lat = np.arctan2(d[:, :, 2], np.hypot(d[:, :, 0], d[:, :, 1]))
    px = ((lon/(2*math.pi) + 0.5) % 1.0)*sw - 0.5; py = (0.5 - lat/math.pi)*sh - 0.5
    x0 = np.floor(px).astype(int); y0 = np.clip(np.floor(py).astype(int), 0, sh - 2); fx = (px - x0)[:, :, None]; fy = (py - y0)[:, :, None]
    x1 = (x0 + 1) % sw; x0 = x0 % sw
    out = src[y0, x0]*(1-fx)*(1-fy) + src[y0, x1]*fx*(1-fy) + src[y0+1, x0]*(1-fx)*fy + src[y0+1, x1]*fx*fy
    return out.astype(np.float32)
if __name__ == "__main__":
    name = sys.argv[1]; yaws = [int(v) for v in sys.argv[2:]]
    sheet = Image.new("RGB", (680*len(yaws), 600))
    for i, y in enumerate(yaws):
        im = Image.fromarray(view(name, y).astype(np.uint8)).resize((680, 600))
        sheet.paste(im, (i*680, 0))
    sheet.save(f"yaw_{name}.jpg", quality=85)
