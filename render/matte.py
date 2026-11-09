import numpy as np
from PIL import Image
O = "/Users/luizleite/Projects/byd-cluster/panel/assets/home"
names = {"c3aff49b7f114d3a89ccdb52a19e9663": "pumpkin", "92444a40e9f240048e469e2ad54af7be": "plaid", "33bb8031d7ac40758575835cec277761": "red", "1390a7592b3d4abc8057a061e567211c": "pine"}
for u, n in names.items():
    b = np.asarray(Image.open(f"out/props2/{u}_b.png").convert("RGB")).astype(np.float32)
    w = np.asarray(Image.open(f"out/props2/{u}_w.png").convert("RGB")).astype(np.float32)
    a = np.clip(1 - (w - b).mean(2) / 255, 0, 1)
    rgb = np.clip(b / np.maximum(a, 0.02)[:, :, None], 0, 255)
    ys, xs = np.nonzero(a > 0.6); x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    pad = 30 if n == "pumpkin" else 4
    box = (max(0, x0 - pad), max(0, y0 - pad), min(900, x1 + pad + 1), min(900, y1 + 3))
    im = Image.fromarray(np.dstack([rgb, a[:, :, None] * 255]).astype(np.uint8), "RGBA").crop(box)
    s = 440 / max(im.size); im = im.resize((int(im.size[0] * s), int(im.size[1] * s)), Image.LANCZOS)
    im.save(f"{O}/prop-{n}.webp", quality=90, method=6); print(n, im.size)
