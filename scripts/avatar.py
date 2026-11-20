"""Photo -> pixel-art grid (run once, locally). The photo itself is not committed.

    python scripts/avatar.py path/to/photo.jpg

Writes scripts/avatar-grid.json (palette + cells + eye positions); build.py renders it.
"""
import json
import sys
from collections import deque

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

from theme import ROOT

N = 52            # grid size
COLORS = 12       # palette size
X0, Y0, S = 190, 0, 440            # square crop in the 800x800 source
EYES = [(355, 136), (442, 130)]    # eye centres in source pixels


def build(src):
    img = Image.open(src).convert("RGB")
    crop = img.crop((X0, Y0, X0 + S, Y0 + S))
    hsv = np.asarray(crop.convert("HSV")).astype(float) / 255
    H = W = S
    yy, xx = np.mgrid[0:H, 0:W]
    gx, gy = xx + X0, yy + Y0

    # Subject mask: head ellipse + neck + white shirt, then fill enclosed holes.
    head = ((gx - 412) / 112) ** 2 + ((gy - 150) / 158) ** 2 <= 1
    neck = (gx > 345) & (gx < 480) & (gy > 220) & (gy < 330)
    shirt = (hsv[..., 1] < 0.30) & (hsv[..., 2] > 0.55) & (gy > 260)
    m = Image.fromarray(((head | neck | shirt) * 255).astype(np.uint8)).filter(ImageFilter.MedianFilter(9))
    mask = np.asarray(m) > 127
    bg = np.zeros_like(mask)
    q = deque((y, x) for y in range(H) for x in (0, W - 1) if not mask[y, x])
    q.extend((y, x) for x in range(W) for y in (0, H - 1) if not mask[y, x])
    for y, x in q:
        bg[y, x] = True
    while q:
        y, x = q.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and not mask[ny, nx] and not bg[ny, nx]:
                bg[ny, nx] = True
                q.append((ny, nx))
    mask = ~bg

    boosted = ImageEnhance.Color(ImageEnhance.Contrast(crop).enhance(1.35)).enhance(1.15)
    rgb = np.asarray(boosted).astype(float) / 255

    f = S / N
    cells = {}
    for j in range(N):
        for i in range(N):
            sl = (slice(int(j * f), int((j + 1) * f)), slice(int(i * f), int((i + 1) * f)))
            mk = mask[sl]
            if mk.mean() > 0.5:
                cells[(i, j)] = rgb[sl][mk].mean(0)

    pal_img = Image.fromarray((np.array(list(cells.values()))[None] * 255).astype(np.uint8)).quantize(
        COLORS, method=Image.Quantize.MEDIANCUT)
    pal = np.array(pal_img.getpalette()[:COLORS * 3]).reshape(COLORS, 3)
    rows = [["." for _ in range(N)] for _ in range(N)]
    for (i, j), c in cells.items():
        rows[j][i] = "0123456789ab"[int(np.argmin(((pal - c * 255) ** 2).sum(1)))]

    face = [c for (i, j), c in cells.items() if 10 <= j < 24 and 14 <= i < 36]
    skin = np.median(face, axis=0)
    out = dict(
        size=N,
        palette=["#%02x%02x%02x" % tuple(int(v) for v in p) for p in pal],
        rows=["".join(r) for r in rows],
        skin="#%02x%02x%02x" % tuple((skin * 255).astype(int)),
        eyes=[[round((ex - X0) / f, 1), round((ey - Y0) / f, 1)] for ex, ey in EYES],
    )
    (ROOT / "scripts" / "avatar-grid.json").write_text(json.dumps(out, indent=1))
    print("wrote scripts/avatar-grid.json")


if __name__ == "__main__":
    build(sys.argv[1])
