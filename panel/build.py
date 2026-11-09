import base64, json, re, sys
from pathlib import Path

here = Path(__file__).parent
mime = {".png": "image/png", ".woff": "font/woff", ".webp": "image/webp"}

def uri(p):
    return f"data:{mime[p.suffix]};base64," + base64.b64encode(p.read_bytes()).decode()

def inline(m):
    kind, name = m.group(1), m.group(2)
    return uri(here / ("assets" if kind == "img" else "fonts") / name)

def build(src, out, extra=None):
    text = (here / src).read_text()
    for k, v in (extra or {}).items():
        text = text.replace("{{" + k + "}}", v)
    text = re.sub(r"\{\{(img|font):([^}]+)\}\}", inline, text)
    (here / out).write_text(text)
    print(out, len(text) // 1024, "KB")

build("road.src.html", "king-road.html")

home = here / "assets" / "home"
meta = json.loads((home / "meta.json").read_text())
frames = [{k: uri(home / f"{k}{i:02d}.{'png' if k == 'm' else 'webp'}") for k in "comen"} for i in range(meta["n"])]
cam = {k: meta[k] for k in ("dist", "hc", "tz", "f", "cx", "cy", "box", "sc")}
for n in ("standard", "halloween", "christmas", "carnaval"):
    th = home / f"thumb-{n}.webp"
    if not th.exists():
        from PIL import Image
        Image.new("RGB", (8, 5), (15, 15, 15)).save(th)
build("home.src.html", "king-home.html", {"frames": json.dumps(frames), "cam": json.dumps(cam), "fw": str(meta["fw"]), "fh": str(meta["fh"]), "ms": str(meta["ms"])})
