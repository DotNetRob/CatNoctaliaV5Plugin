#!/usr/bin/env python3
"""Build fonts/*.otf from the source SVGs in icons/.

Traces the six CatWalk symbolic-icon SVGs (idle + 5 run frames) into a CFF
OpenType font with one glyph per frame ("a" = idle, "b".."f" = run cycle),
sharing a single horizontal/vertical registration so the animation doesn't
jitter, and trimming each glyph's advance width to the shared ink extent so
bar layout doesn't overlap the previous widget or leave a big gap before the
next one (see the "Font metrics" note in README.md).

Usage:
    pip install fonttools
    python tools/build_font.py --family "Noctalia Catwalk 3" --out fonts/catwalk3.otf

IMPORTANT: Noctalia's noctalia.loadFont() registers fonts in a process-global
cache keyed by file path, and re-registering the same path is a documented
no-op. Whenever you change the glyph *contents*, pick a --out filename and
--family that have never been used before (bump the number), then update the
loadFont() call in cat.luau to match. Overwriting an existing .otf in place
will leave already-running shells showing stale or missing glyphs. See the
"Development note: font caching" section in README.md.
"""

import argparse
import re
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import parse_path

REPO_ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = REPO_ROOT / "icons"

# glyph char -> source SVG in icons/
FRAME_FILES = {
    "a": "my-idle-symbolic.svg",
    "b": "my-active-0-symbolic.svg",
    "c": "my-active-1-symbolic.svg",
    "d": "my-active-2-symbolic.svg",
    "e": "my-active-3-symbolic.svg",
    "f": "my-active-4-symbolic.svg",
}

UPM = 1000
ASCENT = 500
DESCENT = 500
CANVAS = 388.0  # native width/height of the source SVGs
TARGET_H = 760.0  # visual height budget inside the ascent+descent box
SCALE = TARGET_H / CANVAS
PAD = 20.0  # horizontal breathing room on each side of the shared ink extent


def load_path_d(filename):
    content = (ICON_DIR / filename).read_text()
    m = re.search(r'<path[^>]*\bd="([^"]+)"', content, re.S)
    return m.group(1)


def raw_bounds(d):
    bounds_pen = BoundsPen(None)
    parse_path(d, bounds_pen)
    return bounds_pen.bounds


def build(family: str, out_path: Path, psname: str):
    paths = {name: load_path_d(fn) for name, fn in FRAME_FILES.items()}

    # Shared registration: use the union bbox (in SVG space) across every
    # frame so legs/tail animate in place instead of each frame re-centering
    # independently.
    all_bounds = [raw_bounds(d) for d in paths.values()]
    xmin = min(b[0] for b in all_bounds)
    xmax = max(b[2] for b in all_bounds)
    ymin = min(b[1] for b in all_bounds)
    ymax = max(b[3] for b in all_bounds)
    cx = (xmin + xmax) / 2
    cy = (ymin + ymax) / 2

    # Pass 1: center-registered transform, just to measure the TRUE
    # post-transform ink bounds (SVG y grows down; font y grows up).
    probe_matrix = (SCALE, 0, 0, -SCALE, -cx * SCALE, cy * SCALE)
    probe_bounds = []
    for d in paths.values():
        bp = BoundsPen(None)
        parse_path(d, TransformPen(bp, probe_matrix))
        probe_bounds.append(bp.bounds)

    ink_xmin = min(b[0] for b in probe_bounds)
    ink_xmax = max(b[2] for b in probe_bounds)
    advance = round(ink_xmax - ink_xmin + 2 * PAD)
    shift_x = -ink_xmin + PAD

    # Pass 2: same shared scale/registration, shifted so ink starts at PAD
    # (never negative -> no overlap into the previous glyph) and the advance
    # width tightly wraps the shared ink extent (no dead trailing space).
    matrix = (SCALE, 0, 0, -SCALE, -cx * SCALE + shift_x, cy * SCALE)

    glyph_order = [".notdef", "space"] + list(FRAME_FILES.keys())
    char_strings = {}
    widths = {".notdef": UPM, "space": round(advance * 0.6)}

    pen = T2CharStringPen(widths[".notdef"], None)
    pen.moveTo((100, 0))
    pen.lineTo((100, 10))
    pen.lineTo((110, 10))
    pen.lineTo((110, 0))
    pen.closePath()
    char_strings[".notdef"] = pen.getCharString()

    char_strings["space"] = T2CharStringPen(widths["space"], None).getCharString()

    for name, d in paths.items():
        cs_pen = T2CharStringPen(advance, None)
        parse_path(d, TransformPen(cs_pen, matrix))
        char_strings[name] = cs_pen.getCharString()
        widths[name] = advance

    fb = FontBuilder(UPM, isTTF=False)
    fb.setupGlyphOrder(glyph_order)
    fb.setupCharacterMap({ord(c): c for c in FRAME_FILES} | {ord(" "): "space"})
    fb.setupHorizontalMetrics({g: (widths[g], 0) for g in glyph_order})
    fb.setupHorizontalHeader(ascent=ASCENT, descent=-DESCENT)
    fb.setupNameTable({"familyName": family, "styleName": "Regular"})
    fb.setupOS2(sTypoAscender=ASCENT, sTypoDescender=-DESCENT, usWinAscent=ASCENT, usWinDescent=DESCENT)
    fb.setupPost()
    fb.setupCFF(psname, {"FullName": family}, char_strings, {})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fb.font.save(out_path)
    print(f"built {out_path} (family={family!r}) advance={advance} shiftX={shift_x:.1f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--family", required=True, help='Font family name, e.g. "Noctalia Catwalk 3". Must be new.')
    parser.add_argument("--out", required=True, type=Path, help="Output .otf path, e.g. fonts/catwalk3.otf. Must be new.")
    parser.add_argument("--psname", help="PostScript name (default: derived from --family).")
    args = parser.parse_args()

    out_path = args.out if args.out.is_absolute() else REPO_ROOT / args.out
    psname = args.psname or (re.sub(r"[^A-Za-z0-9]", "", args.family) + "-Regular")

    if out_path.exists():
        parser.error(
            f"{out_path} already exists. Pick a new filename (see the docstring) instead of overwriting it."
        )

    build(args.family, out_path, psname)


if __name__ == "__main__":
    main()
