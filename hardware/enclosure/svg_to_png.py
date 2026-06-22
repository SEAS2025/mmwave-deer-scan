"""Minimal SVG -> PNG rasterizer for the DeerWatch drawings (Pillow only).

Handles exactly the primitives our generators emit: <rect>, <line> (incl.
stroke-dasharray), <circle>, <text> (incl. rotate transform), and a top-level
<g transform="translate(...)">. Not a general SVG renderer.

    python hardware/enclosure/svg_to_png.py <in.svg> <out.png> [scale]
"""

from __future__ import annotations

import math
import re
import sys
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont

NS = "{http://www.w3.org/2000/svg}"


def _num(s, d=0.0):
    try:
        return float(s)
    except (TypeError, ValueError):
        return d


def _color(s, default=(0, 0, 0)):
    if not s or s == "none":
        return None
    s = s.strip()
    if s.startswith("#"):
        h = s[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    named = {"white": (255, 255, 255), "black": (0, 0, 0)}
    return named.get(s, default)


def _font(size, bold=False):
    names = (["consolab.ttf", "arialbd.ttf"] if bold else ["consola.ttf", "arial.ttf"])
    for n in names:
        try:
            return ImageFont.truetype(n, int(size))
        except Exception:
            continue
    return ImageFont.load_default()


def render(in_svg, out_png, scale=2.0):
    tree = ET.parse(in_svg)
    root = tree.getroot()
    W = int(_num(root.get("width"), 800) * scale)
    Hh = int(_num(root.get("height"), 600) * scale)
    img = Image.new("RGB", (W, Hh), "white")
    dr = ImageDraw.Draw(img)

    ox = oy = 0.0
    g = root.find(f"{NS}g")
    nodes = list(root)
    if g is not None:
        t = g.get("transform", "")
        m = re.search(r"translate\(([-\d.]+),([-\d.]+)\)", t)
        if m:
            ox, oy = float(m.group(1)), float(m.group(2))
        nodes = list(g)

    def sx(x):
        return (x + ox) * scale

    def sy(y):
        return (y + oy) * scale

    for el in nodes:
        tag = el.tag.replace(NS, "")
        if tag == "rect":
            x, y = sx(_num(el.get("x"))), sy(_num(el.get("y")))
            w, h = _num(el.get("width")) * scale, _num(el.get("height")) * scale
            fill = _color(el.get("fill"), None) if el.get("fill") not in (None, "none") else None
            stroke = _color(el.get("stroke"))
            sw = max(1, int(_num(el.get("stroke-width"), 1) * scale))
            dr.rectangle([x, y, x + w, y + h], outline=stroke, fill=fill, width=sw)
        elif tag == "line":
            x1, y1 = sx(_num(el.get("x1"))), sy(_num(el.get("y1")))
            x2, y2 = sx(_num(el.get("x2"))), sy(_num(el.get("y2")))
            stroke = _color(el.get("stroke"))
            sw = max(1, int(_num(el.get("stroke-width"), 1) * scale))
            if el.get("stroke-dasharray"):
                _dashed(dr, x1, y1, x2, y2, stroke, sw)
            else:
                dr.line([x1, y1, x2, y2], fill=stroke, width=sw)
        elif tag == "circle":
            cx, cy = sx(_num(el.get("cx"))), sy(_num(el.get("cy")))
            r = _num(el.get("r")) * scale
            stroke = _color(el.get("stroke"))
            sw = max(1, int(_num(el.get("stroke-width"), 1) * scale))
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=stroke, width=sw)
        elif tag == "text":
            x, y = sx(_num(el.get("x"))), sy(_num(el.get("y")))
            size = _num(el.get("font-size"), 11) * scale
            bold = el.get("font-weight") == "bold"
            fill = _color(el.get("fill"))
            anchor = el.get("text-anchor", "start")
            s = (el.text or "").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
            rot = 0.0
            tr = el.get("transform", "")
            mm = re.search(r"rotate\(([-\d.]+)", tr)
            if mm:
                rot = float(mm.group(1))
            _text(img, dr, x, y, s, _font(size, bold), fill, anchor, rot)

    img.save(out_png)
    print(f"Wrote {out_png} ({W}x{Hh})")


def _dashed(dr, x1, y1, x2, y2, color, w, dash=6, gap=4):
    dist = math.hypot(x2 - x1, y2 - y1)
    if dist == 0:
        return
    dx, dy = (x2 - x1) / dist, (y2 - y1) / dist
    pos = 0.0
    while pos < dist:
        a = pos
        b = min(pos + dash, dist)
        dr.line([x1 + dx * a, y1 + dy * a, x1 + dx * b, y1 + dy * b], fill=color, width=w)
        pos += dash + gap


def _text(img, dr, x, y, s, font, fill, anchor, rot):
    if not s:
        return
    bbox = dr.textbbox((0, 0), s, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    if rot:
        pad = 4
        timg = Image.new("RGBA", (tw + 2 * pad, th + 2 * pad), (0, 0, 0, 0))
        td = ImageDraw.Draw(timg)
        td.text((pad - bbox[0], pad - bbox[1]), s, font=font, fill=fill)
        timg = timg.rotate(-rot, expand=True, resample=Image.BICUBIC)
        ax = x - timg.width / 2 if anchor == "middle" else (x - timg.width if anchor == "end" else x)
        ay = y - timg.height / 2
        img.paste(timg, (int(ax), int(ay)), timg)
    else:
        ax = x - tw / 2 if anchor == "middle" else (x - tw if anchor == "end" else x)
        dr.text((ax, y - th), s, font=font, fill=fill)


if __name__ == "__main__":
    in_svg = sys.argv[1] if len(sys.argv) > 1 else "hardware/enclosure/orthographic.svg"
    out_png = sys.argv[2] if len(sys.argv) > 2 else "hardware/enclosure/orthographic_preview.png"
    sc = float(sys.argv[3]) if len(sys.argv) > 3 else 2.0
    render(in_svg, out_png, sc)
