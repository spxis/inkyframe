from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

font_path = "/System/Library/Fonts/Hiragino Sans GB.ttc"
font_size = 30
font = ImageFont.truetype(font_path, font_size)

labels = {
    "VANCOUVER_KATAKANA": "\u30d0\u30f3\u30af\u30fc\u30d0\u30fc",
    "TOKYO_KANJI": "\u6771\u4eac",
}

out = []
out.append('"""Pre-rendered Japanese label bitmaps for InkyFrame."""')
out.append("")
out.append("JP_BITMAPS = {")

for key, text in labels.items():
    img = Image.new("1", (512, 128), 0)
    dr = ImageDraw.Draw(img)
    dr.text((4, 4), text, font=font, fill=1)
    bbox = img.getbbox() or (0, 0, 1, 1)
    crop = img.crop(bbox)

    pad = 2
    padded = Image.new("1", (crop.width + pad * 2, crop.height + pad * 2), 0)
    padded.paste(crop, (pad, pad))

    rows = []
    px = padded.load()
    for y in range(padded.height):
        row = "".join("#" if px[x, y] else "." for x in range(padded.width))
        rows.append(row)

    out.append(f"    '{key}': {{")
    out.append(f"        'w': {padded.width},")
    out.append(f"        'h': {padded.height},")
    out.append("        'rows': [")
    for r in rows:
        out.append(f"            '{r}',")
    out.append("        ],")
    out.append("    },")

out.append("}")
out.append("")

Path("jp_label_bitmaps.py").write_text("\n".join(out), encoding="utf-8")
print("WROTE jp_label_bitmaps.py")
