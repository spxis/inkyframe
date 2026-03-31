from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ARIAL_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
ARIAL_UNICODE = "/Library/Fonts/Arial Unicode.ttf"


def render_bitmap(text, font_path, size, stroke=0, pad=2):
    font = ImageFont.truetype(font_path, size)
    img = Image.new("1", (1024, 256), 0)
    dr = ImageDraw.Draw(img)
    dr.text((4, 4), text, font=font, fill=1, stroke_width=stroke, stroke_fill=1)
    bbox = img.getbbox() or (0, 0, 1, 1)
    crop = img.crop(bbox)

    out = Image.new("1", (crop.width + pad * 2, crop.height + pad * 2), 0)
    out.paste(crop, (pad, pad))

    px = out.load()
    rows = []
    for y in range(out.height):
        rows.append("".join("#" if px[x, y] else "." for x in range(out.width)))

    return {"w": out.width, "h": out.height, "rows": rows}


def build_font(chars, font_path, size, stroke):
    return {ch: render_bitmap(ch, font_path, size=size, stroke=stroke, pad=1) for ch in chars}


def emit_dict(name, data, out_lines):
    out_lines.append(f"{name} = {{")
    for key, item in data.items():
        out_lines.append(f"    {key!r}: {{")
        out_lines.append(f"        'w': {item['w']},")
        out_lines.append(f"        'h': {item['h']},")
        out_lines.append("        'rows': [")
        for r in item["rows"]:
            out_lines.append(f"            {r!r},")
        out_lines.append("        ],")
        out_lines.append("    },")
    out_lines.append("}")
    out_lines.append("")


def main():
    word_bitmaps = {
        "VANCOUVER_EN": render_bitmap("Vancouver", ARIAL_BOLD, size=60, stroke=1, pad=2),
        "TOKYO_EN": render_bitmap("Tokyo", ARIAL_BOLD, size=60, stroke=1, pad=2),
    }

    jp_bitmaps = {
        "VANCOUVER_KATAKANA": render_bitmap("\u30d0\u30f3\u30af\u30fc\u30d0\u30fc", ARIAL_UNICODE, size=48, stroke=1, pad=2),
        "TOKYO_KANJI": render_bitmap("\u6771\u4eac", ARIAL_UNICODE, size=53, stroke=1, pad=2),
    }

    weekday_en = {
        "MONDAY": render_bitmap("Monday", ARIAL_BOLD, size=36, stroke=1, pad=2),
        "TUESDAY": render_bitmap("Tuesday", ARIAL_BOLD, size=36, stroke=1, pad=2),
        "WEDNESDAY": render_bitmap("Wednesday", ARIAL_BOLD, size=36, stroke=1, pad=2),
        "THURSDAY": render_bitmap("Thursday", ARIAL_BOLD, size=36, stroke=1, pad=2),
        "FRIDAY": render_bitmap("Friday", ARIAL_BOLD, size=36, stroke=1, pad=2),
        "SATURDAY": render_bitmap("Saturday", ARIAL_BOLD, size=36, stroke=1, pad=2),
        "SUNDAY": render_bitmap("Sunday", ARIAL_BOLD, size=36, stroke=1, pad=2),
    }

    weekday_jp = {
        "MONDAY": render_bitmap("\u6708\u66dc\u65e5", ARIAL_UNICODE, size=38, stroke=1, pad=2),
        "TUESDAY": render_bitmap("\u706b\u66dc\u65e5", ARIAL_UNICODE, size=38, stroke=1, pad=2),
        "WEDNESDAY": render_bitmap("\u6c34\u66dc\u65e5", ARIAL_UNICODE, size=38, stroke=1, pad=2),
        "THURSDAY": render_bitmap("\u6728\u66dc\u65e5", ARIAL_UNICODE, size=38, stroke=1, pad=2),
        "FRIDAY": render_bitmap("\u91d1\u66dc\u65e5", ARIAL_UNICODE, size=38, stroke=1, pad=2),
        "SATURDAY": render_bitmap("\u571f\u66dc\u65e5", ARIAL_UNICODE, size=38, stroke=1, pad=2),
        "SUNDAY": render_bitmap("\u65e5\u66dc\u65e5", ARIAL_UNICODE, size=38, stroke=1, pad=2),
    }

    font_time = build_font("0123456789:", ARIAL_BOLD, size=110, stroke=2)
    font_date = build_font("0123456789-", ARIAL_BOLD, size=42, stroke=1)

    out = []
    out.append('"""Generated custom bitmap assets for InkyFrame text rendering."""')
    out.append("")

    emit_dict("WORD_BITMAPS", word_bitmaps, out)
    emit_dict("JP_BITMAPS", jp_bitmaps, out)
    emit_dict("WEEKDAY_EN_BITMAPS", weekday_en, out)
    emit_dict("WEEKDAY_JP_BITMAPS", weekday_jp, out)
    emit_dict("FONT_TIME", font_time, out)
    emit_dict("FONT_DATE", font_date, out)

    Path("custom_bitmaps.py").write_text("\n".join(out), encoding="utf-8")
    print("WROTE custom_bitmaps.py")


if __name__ == "__main__":
    main()
