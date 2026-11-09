import base64, re, sys
from pathlib import Path

here = Path(__file__).parent
src = (here / "road.src.html").read_text()
mime = {".png": "image/png", ".woff": "font/woff", ".webp": "image/webp"}

def inline(m):
    kind, name = m.group(1), m.group(2)
    p = here / ("assets" if kind == "img" else "fonts") / name
    return f"data:{mime[p.suffix]};base64," + base64.b64encode(p.read_bytes()).decode()

out = re.sub(r"\{\{(img|font):([^}]+)\}\}", inline, src)
(here / "king-road.html").write_text(out)
print("king-road.html", len(out) // 1024, "KB")
