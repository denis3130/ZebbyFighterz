#!/usr/bin/env python3
"""Joins the cells sheet.js rendered into labelled contact sheets (one PNG per act)."""
import json, sys
from PIL import Image, ImageDraw

for m in json.load(open(sys.argv[1])):
    cw, ch, yaws, cols = m["cw"], m["ch"], m["yaws"], m["cols"]
    top, left = 34, 46
    sheet = Image.new("RGB", (left + cw * len(cols), top + ch * len(yaws)), (24, 22, 32))
    d = ImageDraw.Draw(sheet)
    d.text((6, 4), m["title"], fill=(255, 160, 60))
    for j, c in enumerate(cols):
        d.text((left + j * cw + 6, 18), c, fill=(255, 255, 255) if "HIT" not in c else (90, 230, 255))
    for i, y in enumerate(yaws):
        d.text((4, top + i * ch + 6), "%d°" % y, fill=(200, 200, 210))
    k = 0
    for j in range(len(cols)):
        for i in range(len(yaws)):
            sheet.paste(Image.open(m["cells"][k]["file"]).convert("RGB"), (left + j * cw, top + i * ch)); k += 1
    sheet.save(m["out"])
