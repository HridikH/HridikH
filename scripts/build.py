"""Static profile assets: avatar, banner, project cards, tech-stack row (light + dark).

    python scripts/build.py
"""
import json
import math
import textwrap

from PIL import Image, ImageDraw

from theme import CHAR_W, ROOT, THEMES, esc, font_css, icon_path, pcb_grid, write

GRID = json.loads((ROOT / "scripts" / "avatar-grid.json").read_text())

NAME = "Hridik Hingorani"
TAGLINE = "Computer Engineering @ UIUC. Robotics, embedded systems, controls."


# ---------------------------------------------------------------- avatar
def avatar_cells(px=1.0):
    """Pixel rects, merged into horizontal runs per palette color."""
    out = []
    for j, row in enumerate(GRID["rows"]):
        i = 0
        while i < len(row):
            ch = row[i]
            if ch == ".":
                i += 1
                continue
            k = i
            while k < len(row) and row[k] == ch:
                k += 1
            col = GRID["palette"][int(ch, 16)]
            out.append(f'<rect x="{i*px:g}" y="{j*px:g}" width="{(k-i)*px+0.04:g}" height="{px+0.04:g}" fill="{col}"/>')
            i = k
    return "".join(out)


def avatar_lids(px=1.0):
    return "".join(
        f'<rect x="{(int(x)-1)*px:g}" y="{(int(y)-1)*px:g}" width="{3*px:g}" height="{2*px:g}" fill="{GRID["skin"]}"/>'
        for x, y in GRID["eyes"])


AVATAR_CSS = (".lid{opacity:0;animation:blink 5.5s infinite}"
              "@keyframes blink{0%,91%,100%{opacity:0}92.5%,95.5%{opacity:1}}")
FLOAT = '<animateTransform attributeName="transform" type="translate" values="0 0;0 -{a};0 0" dur="5s" repeatCount="indefinite" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1"/>'


def avatar_svg(t):
    n = GRID["size"]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-6 -6 {n+12} {n+12}" width="{(n+12)*8}" height="{(n+12)*8}" shape-rendering="crispEdges">'
            f'<title>Hridik Hingorani, pixel portrait</title><style>{AVATAR_CSS}</style>'
            f'<rect x="-6" y="-6" width="{n+12}" height="{n+12}" rx="8" fill="{t["surface"]}"/>'
            f'<g>{FLOAT.format(a=0.8)}{avatar_cells()}<g class="lid">{avatar_lids()}</g></g></svg>')


def avatar_png(path, size=520):
    """Square PNG for the GitHub profile picture (shown as a circle, so the face sits centred)."""
    n = GRID["size"]
    px = size * 0.72 / n
    img = Image.new("RGB", (size, size), THEMES["dark"]["surface"])
    d = ImageDraw.Draw(img)
    ox = (size - n * px) / 2
    oy = size * 0.13
    for j, row in enumerate(GRID["rows"]):
        for i, ch in enumerate(row):
            if ch != ".":
                x, y = ox + i * px, oy + j * px
                d.rectangle([x, y, x + px, y + px], fill=GRID["palette"][int(ch, 16)])
    img.save(path)


# ---------------------------------------------------------------- banner
W, H = 1200, 330


def banner(t):
    n = GRID["size"]
    # Avatar drawn as an IC package (U1) with pins on both sides.
    bx, by, bs = 52, 48, 236
    px = (bs - 24) / n
    pins = ""
    pin_ys = [by + 34 + k * 34 for k in range(6)]
    for y in pin_ys:
        pins += f'<rect x="{bx-12}" y="{y-4}" width="12" height="8" rx="1.5" fill="{t["trace"]}"/>'
        pins += f'<rect x="{bx+bs}" y="{y-4}" width="12" height="8" rx="1.5" fill="{t["trace"]}"/>'
    ic = (f'<rect x="{bx}" y="{by}" width="{bs}" height="{bs}" rx="10" fill="{t["surface"]}" stroke="{t["line"]}" stroke-width="1.5"/>'
          f'<circle cx="{bx+14}" cy="{by+14}" r="3.5" fill="{t["line"]}"/>'
          f'<text x="{bx}" y="{by-12}" font-size="12" fill="{t["muted"]}" letter-spacing="1">U1</text>'
          f'<text x="{bx+bs}" y="{by+bs+22}" font-size="11" fill="{t["muted"]}" text-anchor="end" letter-spacing="1">HH-2027</text>'
          + pins +
          f'<g shape-rendering="crispEdges"><g>{FLOAT.format(a=3)}'
          f'<g transform="translate({bx+12} {by+16})">{avatar_cells(px)}<g class="lid">{avatar_lids(px)}</g></g></g></g>')

    # Left-side stubs running off the board edge, ending in vias.
    stubs = ""
    for k, y in enumerate(pin_ys[1:5]):
        x_end = 18 if k % 2 else 26
        stubs += f'<path d="M{bx-12} {y} H{x_end}" class="tr"/><circle cx="{x_end}" cy="{y}" r="4" class="via"/>'

    # Right-side traces: 45-degree jogs, then long runs under the text.
    ox = bx + bs + 12
    routes = [
        (f"M{ox} {pin_ys[3]} H{ox+28} L{ox+58} {pin_ys[3]+30} H884", True, 5.5),
        (f"M{ox} {pin_ys[4]} H{ox+40} L{ox+70} {pin_ys[4]+30} H700", False, 4.2),
        (f"M{ox} {pin_ys[5]} H{ox+52} L{ox+70} {pin_ys[5]+18} H560 L582 {pin_ys[5]-4} H640", False, 3.6),
    ]
    traces = ""
    for d, to_scope, dur in routes:
        traces += f'<path d="{d}" class="tr"/>'
        end = d.split()[-1]
        if not to_scope:
            # end point: last coordinate pair of the path
            nums = d.replace("H", " H ").replace("L", " L ").replace("M", " M ").split()
            x_end, y_end = _path_end(nums)
            traces += f'<circle cx="{x_end}" cy="{y_end}" r="4.5" class="via"/>'
        if dur:
            traces += f'<path d="{d}" class="pulse" style="animation-duration:{dur}s"/>'

    # Typed tagline: a clip rect that grows one character per step (SMIL, discrete).
    tx, ny, ty = 336, 130, 176
    fs = 19
    cw = fs * CHAR_W
    n_ch = len(TAGLINE)
    widths = ";".join(f"{k*cw:.1f}" for k in range(n_ch + 1))
    type_dur = 0.055 * n_ch
    typed = (f'<clipPath id="type"><rect x="{tx}" y="{ty-22}" height="32" width="0">'
             f'<animate attributeName="width" values="{widths}" dur="{type_dur:.2f}s" begin="0.5s" calcMode="discrete" fill="freeze"/></rect></clipPath>'
             f'<text x="{tx}" y="{ty}" font-size="{fs}" fill="{t["text"]}" clip-path="url(#type)">{esc(TAGLINE)}</text>'
             f'<rect class="cur" y="{ty-17}" width="{cw*0.55:.1f}" height="21" fill="{t["accent"]}" x="{tx}">'
             f'<animate attributeName="x" values="{";".join(f"{tx+k*cw:.1f}" for k in range(n_ch + 1))}" dur="{type_dur:.2f}s" begin="0.5s" calcMode="discrete" fill="freeze"/></rect>')
    name = (f'<text x="{tx-2}" y="{ny}" font-size="54" font-weight="700" fill="{t["text"]}" letter-spacing="-1">{NAME}</text>'
            f'<text x="{tx}" y="{ny-62}" font-size="12.5" fill="{t["muted"]}" letter-spacing="2">CHAMPAIGN, IL  ·  UIUC ECE</text>')

    # 2-link arm with joint angles, gently swinging (SMIL rotations in local frames).
    ax, ay, l1, l2 = 1092, 136, 64, 50
    arm = (f'<g transform="translate({ax} {ay})">'
           f'<path d="M-26 8 H26" stroke="{t["muted"]}" stroke-width="2"/>'
           + "".join(f'<path d="M{x} 8 l-7 8" stroke="{t["line"]}" stroke-width="1.5"/>' for x in range(-20, 30, 10)) +
           f'<path d="M0 0 H44" stroke="{t["line"]}" stroke-dasharray="3 4" stroke-width="1.2"/>'
           f'<path d="M30 0 A30 30 0 0 0 -12.7 -27.2" fill="none" stroke="{t["line"]}" stroke-width="1.2"/>'
           f'<text x="36" y="-14" font-size="12" fill="{t["muted"]}">q1</text>'
           f'<g transform="rotate(-115)"><animateTransform attributeName="transform" type="rotate" values="-108;-126;-108" dur="7s" repeatCount="indefinite" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1"/>'
           f'<path d="M0 0 H{l1}" stroke="{t["text"]}" stroke-width="5" stroke-linecap="round"/>'
           f'<g transform="translate({l1} 0)"><g transform="rotate(45)"><animateTransform attributeName="transform" type="rotate" values="62;24;62" dur="7s" repeatCount="indefinite" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1"/>'
           f'<path d="M0 0 H{l2}" stroke="{t["text"]}" stroke-width="4" stroke-linecap="round"/>'
           f'<path d="M{l2} -7 h8 M{l2} 7 h8 M{l2} -7 V7" stroke="{t["accent"]}" stroke-width="2.5" fill="none" stroke-linecap="round"/></g>'
           f'<circle r="6" fill="{t["bg"]}" stroke="{t["text"]}" stroke-width="2.5"/></g>'
           f'</g><circle r="7" fill="{t["bg"]}" stroke="{t["text"]}" stroke-width="2.5"/><circle r="2" fill="{t["accent"]}"/></g>')

    # Oscilloscope window: underdamped step response, redrawn on a loop.
    sx, sy, sw, sh = 900, 194, 262, 116
    grid = "".join(f'<path d="M{sx+sw*k/8:.1f} {sy+8} V{sy+sh-8}" class="sg"/>' for k in range(1, 8))
    grid += "".join(f'<path d="M{sx+8} {sy+sh*k/4:.1f} H{sx+sw-8}" class="sg"/>' for k in range(1, 4))
    zeta, wn = 0.32, 1.0
    wd = wn * math.sqrt(1 - zeta ** 2)
    pts = []
    x0, x1 = sx + 14, sx + sw - 12
    base, top = sy + sh - 22, sy + 40
    for k in range(121):
        u = k / 120
        tt = u * 16
        y = 1 - math.exp(-zeta * wn * tt) * (math.cos(wd * tt) + zeta / math.sqrt(1 - zeta ** 2) * math.sin(wd * tt))
        pts.append(f"{x0+(x1-x0)*u:.1f},{base-(base-top)*y:.1f}")
    scope = (f'<rect x="{sx}" y="{sy}" width="{sw}" height="{sh}" rx="8" fill="{t["surface"]}" stroke="{t["line"]}" stroke-width="1.5"/>'
             + grid +
             f'<path d="M{x0} {top} H{x1}" stroke="{t["muted"]}" stroke-dasharray="4 4" stroke-width="1"/>'
             f'<polyline points="{" ".join(pts)}" class="scope"/>'
             f'<text x="{sx+12}" y="{sy+20}" font-size="11" fill="{t["accent"]}" letter-spacing="1">CH1</text>'
             f'<text x="{sx+sw-12}" y="{sy+20}" font-size="11" fill="{t["muted"]}" text-anchor="end">step · ζ=0.32</text>')

    css = (font_css() + AVATAR_CSS +
           f'.tr{{fill:none;stroke:{t["trace"]};stroke-width:3;stroke-linejoin:round;stroke-linecap:round}}'
           f'.via{{fill:{t["bg"]};stroke:{t["trace"]};stroke-width:2.5}}'
           f'.pulse{{fill:none;stroke:{t["accent"]};stroke-width:3;stroke-linecap:round;stroke-dasharray:22 1400;stroke-dashoffset:1422;animation:run linear infinite}}'
           '@keyframes run{to{stroke-dashoffset:0}}'
           f'.sg{{stroke:{t["grid"]};stroke-width:1}}'
           f'.scope{{fill:none;stroke:{t["accent"]};stroke-width:2.2;stroke-linejoin:round;stroke-dasharray:420;stroke-dashoffset:420;animation:draw 6s ease-out infinite}}'
           '@keyframes draw{0%{stroke-dashoffset:420;opacity:1}45%{stroke-dashoffset:0;opacity:1}88%{stroke-dashoffset:0;opacity:1}100%{stroke-dashoffset:0;opacity:0}}'
           '.cur{animation:cur 1.1s steps(1) infinite}@keyframes cur{50%{opacity:0}}'
           '@media (prefers-reduced-motion:reduce){.pulse,.scope,.cur,.lid{animation:none}.scope{stroke-dashoffset:0}}')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">'
            f'<title>Hridik Hingorani · {esc(TAGLINE)}</title><style>{css}</style>'
            f'<rect width="{W}" height="{H}" rx="16" fill="{t["bg"]}"/>' + pcb_grid(t, W, H) +
            stubs + traces + ic + name + typed + arm + scope + '</svg>')


def _path_end(tokens):
    x = y = 0.0
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in ("M", "L"):
            x, y = float(tokens[i + 1]), float(tokens[i + 2])
            i += 3
        elif tok == "H":
            x = float(tokens[i + 1])
            i += 2
        else:
            i += 1
    return x, y


# ---------------------------------------------------------------- cards
PROJECTS = [
    dict(slug="k1", label="01 · HUMANOID RL", title="Humanoid push recovery",
         desc="PPO walking policy for a Booster K1 that takes a shove to the torso and keeps walking. Survival-gated push curriculum plus domain randomization, 4,096 robots in mjlab.",
         metric="falls 39% → 13%", tags="Python · PPO · MuJoCo", motif="humanoid"),
    dict(slug="gem", label="02 · AUTONOMY", title="GEM ev4 autonomy stack",
         desc="ROS 2 stack driving a full-size Polaris GEM: lane following, stops for signs, pedestrians and obstacles. I own the controls: Pure Pursuit, speed planning, PID, drive-by-wire limits.",
         metric="holds lane on the car", tags="ROS 2 · Python · LiDAR", motif="car"),
    dict(slug="flex", label="03 · TELEOP", title="Flex-sensor teleop hand",
         desc="Glove-to-hand teleoperation over ESP-NOW. Five-channel flex-sensor board routed in KiCad, ADC1-only pins to dodge WiFi contention, PCA9685 servo drive.",
         metric="5 ch · ESP-NOW", tags="ESP32 · C++ · KiCad", motif="hand"),
    dict(slug="jupiter", label="04 · VOICE", title="Jupiter AI",
         desc="A fully local voice assistant for Apple Silicon. Whisper in, Qwen3 on MLX with speculative decoding, Kokoro TTS out. Start talking and it stops mid-sentence.",
         metric="0.3–0.6 s first token", tags="Python · MLX · Whisper", motif="wave"),
]
CW, CH = 420, 206


def motif(kind, t, x, y):
    s = f'stroke="{t["trace"]}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    a = f'stroke="{t["accent"]}" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"'
    if kind == "humanoid":
        return (f'<g transform="translate({x} {y})"><circle cx="20" cy="6" r="5" {s}/><path d="M20 11 V28 M20 15 L11 23 M20 15 L29 22 M20 28 L14 42 M20 28 L27 41" {s}/>'
                f'<path d="M-2 18 H8 M4 14 L8 18 L4 22" {a}/></g>')
    if kind == "car":
        return (f'<g transform="translate({x} {y})"><rect x="8" y="4" width="24" height="38" rx="6" {s}/>'
                f'<path d="M5 11 V17 M35 11 V17 M5 29 V35 M35 29 V35" {s}/><circle cx="20" cy="15" r="3" {a}/>'
                f'<path d="M12 4 A12 12 0 0 1 28 4 M8 -1 A17 17 0 0 1 32 -1" {a}/></g>')
    if kind == "hand":
        return (f'<g transform="translate({x} {y})"><path d="M10 42 V24 M10 24 V10 M17 24 V4 M24 24 V6 M31 24 V12 M10 24 Q4 26 3 18" {s}/>'
                f'<path d="M8 42 H34 L33 24 H8" {s}/><circle cx="17" cy="12" r="1.8" fill="{t["accent"]}"/><circle cx="24" cy="14" r="1.8" fill="{t["accent"]}"/><circle cx="10" cy="16" r="1.8" fill="{t["accent"]}"/></g>')
    bars = [8, 18, 30, 14, 36, 22, 10, 26, 16, 6]
    return f'<g transform="translate({x} {y})">' + "".join(
        f'<path d="M{2+i*4.2:.1f} {22-h/2:.1f} V{22+h/2:.1f}" {a if 3 <= i <= 5 else s}/>' for i, h in enumerate(bars)) + '</g>'


def card(t, p):
    lines = textwrap.wrap(p["desc"], 49)
    body = "".join(f'<text x="24" y="{96+k*19}" font-size="12.5" fill="{t["muted"]}">{esc(l)}</text>' for k, l in enumerate(lines))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH}" width="{CW}" height="{CH}">'
            f'<title>{esc(p["title"])}</title><style>{font_css()}</style>'
            f'<rect x=".75" y=".75" width="{CW-1.5}" height="{CH-1.5}" rx="12" fill="{t["surface"]}" stroke="{t["line"]}" stroke-width="1.5"/>'
            f'<path d="M{CW-1} 150 H{CW-22} L{CW-34} 162 V{CH-1}" fill="none" stroke="{t["grid"]}" stroke-width="2"/>'
            f'<text x="24" y="34" font-size="10.5" fill="{t["muted"]}" letter-spacing="1.5">{esc(p["label"])}</text>'
            f'<text x="24" y="64" font-size="19" font-weight="700" fill="{t["text"]}">{esc(p["title"])}</text>'
            + body + motif(p["motif"], t, CW - 66, 18) +
            f'<path d="M24 {CH-44} H{CW-24}" stroke="{t["grid"]}" stroke-width="1"/>'
            f'<text x="24" y="{CH-20}" font-size="13" font-weight="700" fill="{t["accent"]}">{esc(p["metric"])}</text>'
            f'<text x="{CW-24}" y="{CH-20}" font-size="11.5" fill="{t["muted"]}" text-anchor="end">{esc(p["tags"])}</text></svg>')


# ---------------------------------------------------------------- tech stack
STACK = [
    ("ROBOTICS · CONTROLS", [("ros", "ROS 2"), ("python", "Python"), ("chip:MAT", "MATLAB"), ("chip:MJ", "MuJoCo"),
                             ("chip:GZ", "Gazebo"), ("opencv", "OpenCV")]),
    ("EMBEDDED · FPGA", [("c", "C"), ("cplusplus", "C++"), ("rust", "Rust"), ("espressif", "ESP32"),
                         ("raspberrypi", "RPi"), ("kicad", "KiCad"), ("chip:SV", "SysVerilog"), ("linux", "Linux")]),
    ("ML", [("pytorch", "PyTorch"), ("numpy", "NumPy"), ("chip:MLX", "MLX"), ("weightsandbiases", "W&B")]),
]
SW, ROW_H = 830, 70


def stack(t):
    out = []
    for r, (label, items) in enumerate(STACK):
        y = 22 + r * ROW_H
        out.append(f'<text x="0" y="{y+18}" font-size="11" fill="{t["muted"]}" letter-spacing="1.5">{label}</text>')
        out.append(f'<path d="M0 {y+28} H150" stroke="{t["grid"]}" stroke-width="1"/>')
        for k, (ic, name) in enumerate(items):
            cx = 214 + k * 78
            if ic.startswith("chip:"):
                code = ic[5:]
                pins = "".join(f'<path d="M{cx-17} {y+o} h4 M{cx+13} {y+o} h4" stroke="{t["muted"]}" stroke-width="1.5"/>' for o in (6, 13, 20))
                out.append(f'<rect x="{cx-13}" y="{y}" width="26" height="26" rx="3" fill="none" stroke="{t["text"]}" stroke-width="1.6"/>{pins}'
                           f'<text x="{cx}" y="{y+16.5}" font-size="{9 if len(code) > 2 else 10}" font-weight="700" fill="{t["text"]}" text-anchor="middle">{code}</text>')
            else:
                out.append(f'<path transform="translate({cx-12} {y+1}) scale(1)" d="{icon_path(ic)}" fill="{t["text"]}"/>')
            out.append(f'<text x="{cx}" y="{y+44}" font-size="10" fill="{t["muted"]}" text-anchor="middle">{esc(name)}</text>')
    h = 22 + len(STACK) * ROW_H - 8
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SW} {h}" width="{SW}" height="{h}">'
            f'<title>Tech stack</title><style>{font_css(bold=True)}</style>{"".join(out)}</svg>')


# ---------------------------------------------------------------- main
if __name__ == "__main__":
    write("assets/avatar.svg", avatar_svg(THEMES["dark"]))
    avatar_png(ROOT / "assets" / "avatar.png")
    for mode, t in THEMES.items():
        write(f"assets/banner-{mode}.svg", banner(t))
        write(f"assets/stack-{mode}.svg", stack(t))
        for p in PROJECTS:
            write(f"assets/card-{p['slug']}-{mode}.svg", card(t, p))
    print("built static assets")
