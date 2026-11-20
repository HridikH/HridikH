"""One palette, one typeface. Every generated SVG pulls its colors and font from here."""
import base64
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = Path(__file__).resolve().parent / "fonts"
ICON_DIR = Path(__file__).resolve().parent / "icons"

# Ink / paper base, one amber accent, a muted copper for traces and grids.
THEMES = {
    "dark": dict(bg="#0F1419", surface="#161C23", grid="#1F2730", line="#2A333D",
                 text="#ECE8DF", muted="#8C959E", accent="#E8A33D", trace="#9C6B33",
                 accent_soft="#3A2E1C"),
    "light": dict(bg="#F5F2EA", surface="#EDE8DD", grid="#E4DDCF", line="#D6CDBB",
                  text="#1A1F24", muted="#6A6E72", accent="#B26D12", trace="#C79A62",
                  accent_soft="#F1DDBB"),
}

FONT = "JBM"
CHAR_W = 0.6  # JetBrains Mono advance width, in em


def _font_b64(weight):
    data = (FONT_DIR / f"JetBrainsMono-{weight}.woff2").read_bytes()
    return base64.b64encode(data).decode()


def font_css(bold=True):
    css = f"@font-face{{font-family:{FONT};font-weight:400;src:url(data:font/woff2;base64,{_font_b64('Regular')}) format('woff2')}}"
    if bold:
        css += f"@font-face{{font-family:{FONT};font-weight:700;src:url(data:font/woff2;base64,{_font_b64('Bold')}) format('woff2')}}"
    return css + f"text{{font-family:{FONT},ui-monospace,SFMono-Regular,Menlo,monospace}}"


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def icon_path(name):
    """Path data from a Simple Icons SVG (24x24 viewBox)."""
    svg = (ICON_DIR / f"{name}.svg").read_text()
    start = svg.index(' d="') + 4
    return svg[start:svg.index('"', start)]


def pcb_grid(t, w, h, step=16, ident="g"):
    """Faint dotted grid, like a board's placement grid."""
    return (f'<defs><pattern id="{ident}" width="{step}" height="{step}" patternUnits="userSpaceOnUse">'
            f'<circle cx="1" cy="1" r="1" fill="{t["grid"]}"/></pattern></defs>'
            f'<rect width="{w}" height="{h}" fill="url(#{ident})"/>')


# Single-file theming: every color is a CSS variable, switched by prefers-color-scheme
# inside the SVG. One file per graphic, so it can sit inside a link on GitHub.
ADAPTIVE = {k: f"var(--{k})" for k in THEMES["light"]}


def _vars(t):
    return ";".join(f"--{k}:{v}" for k, v in t.items())


def vars_css():
    return f"svg{{{_vars(THEMES['light'])}}}@media (prefers-color-scheme:dark){{svg{{{_vars(THEMES['dark'])}}}}}"


_TAG = re.compile(r"<[a-zA-Z][^>]*>")
_VAR_ATTR = re.compile(r'\s(fill|stroke|stop-color)="(var\(--[a-z_]+\))"')


def adapt(svg):
    """Move var() colors out of presentation attributes (which don't take var()) into style."""
    def fix(m):
        tag = m.group(0)
        props = _VAR_ATTR.findall(tag)
        if not props:
            return tag
        tag = _VAR_ATTR.sub("", tag)
        decl = ";".join(f"{k}:{v}" for k, v in props)
        if ' style="' in tag:
            return tag.replace(' style="', f' style="{decl};', 1)
        end = -2 if tag.endswith("/>") else -1
        return f'{tag[:end]} style="{decl}"{tag[end:]}'
    svg = _TAG.sub(fix, svg)
    return svg.replace("<style>", f"<style>{vars_css()}", 1)


def write(rel, svg):
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg)
    return path
