# --- Display Constants ---
TITLE_BOTTOM = 66
JP_LABEL_Y_OFFSET = 6
TIME_Y_BOTTOM = 225
TIME_SCALE_FACTOR = 1.25
DATE_Y_BOTTOM = 286
WEEKDAY_Y_BOTTOM = 318
COL_W_SPACING = 1
TIME_SPACING = 2
DATE_SPACING = 2
"""InkyFrame 7.3: A-E button modes for Vancouver/Tokyo clock + meetings.

Drop this file onto the Pico W running Pimoroni MicroPython firmware.
"""

import time

import ntptime  # type: ignore[import-not-found]
import network  # type: ignore[import-not-found]
import inky_frame  # type: ignore[import-not-found]
from picographics import DISPLAY_INKY_FRAME_7 as DISPLAY  # type: ignore[import-not-found]
from picographics import PicoGraphics  # type: ignore[import-not-found]

try:
    from custom_bitmaps import (
        FONT_UI_BIG,
        FONT_DATE,
        FONT_TIME,
        FONT_JP,
    )
    CUSTOM_BITMAPS_IMPORT_ERROR = None
except Exception as exc:
    FONT_UI_BIG = None
    FONT_DATE = None
    FONT_TIME = None
    FONT_JP = None
    CUSTOM_BITMAPS_IMPORT_ERROR = "{}: {}".format(type(exc).__name__, exc)

try:
    import secrets
except ImportError:
    secrets = None

# Vancouver offset can be overridden in secrets.py.
# Example: VANCOUVER_UTC_OFFSET = -7
PST_OFFSET_HOURS = getattr(secrets, "VANCOUVER_UTC_OFFSET", -7) if secrets else -7
JST_OFFSET_HOURS = 9
REFRESH_SECONDS = 5 * 60
NTP_RETRIES = 3
MIN_VALID_YEAR = 2024
WIFI_CONNECT_TIMEOUT_S = 35

MODE_A = "A"
MODE_B = "B"
MODE_C = "C"
MODE_D = "D"
MODE_E = "E"

SAMPLE_MEETINGS_UTC = [
    # Same meeting list rendered in different local timezones.
    ("Standup", 17, 0),
    ("Planning", 20, 0),
    ("1:1", 0, 30),
]

graphics = PicoGraphics(display=DISPLAY)

WIDTH, HEIGHT = graphics.get_bounds()
WHITE = graphics.create_pen(255, 255, 255)
BLACK = graphics.create_pen(0, 0, 0)
COL_GUTTER = 28
LEFT_X = 20
RIGHT_X = (WIDTH // 2) + COL_GUTTER
COL_W = (WIDTH // 2) - (COL_GUTTER + 20)

REQUIRED_JP_CHARS = tuple("バンクーバー東京月火水木金土日曜日")
REQUIRED_TIME_CHARS = tuple("0123456789:")
REQUIRED_DATE_CHARS = tuple("0123456789/-年月日")
REQUIRED_UI_BIG_CHARS = tuple("VancouverTokyo")


def connect_wifi(timeout_s=WIFI_CONNECT_TIMEOUT_S):
    """Connect to Wi-Fi; returns (wlan_or_none, wifi_status_text)."""
    if secrets is None:
        return None, "WiFi: no secrets.py"

    ssid = getattr(secrets, "WIFI_SSID", None)
    password = getattr(secrets, "WIFI_PASSWORD", None)
    if not ssid or not password:
        return None, "WiFi: missing creds"

    country = getattr(secrets, "WIFI_COUNTRY", "CA")
    try:
        network.country(country)
    except Exception:
        pass

    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    # Pimoroni examples disable Wi-Fi power saving for compatibility with some APs.
    try:
        wlan.config(pm=0xA11140)
    except Exception:
        pass

    if wlan.isconnected():
        return wlan, "WiFi: {}".format(ssid)

    wlan.connect(ssid, password)
    start = time.time()
    while not wlan.isconnected() and (time.time() - start) < timeout_s:
        time.sleep(0.2)

    if wlan.isconnected():
        return wlan, "WiFi: {}".format(ssid)

    status = "?"
    try:
        status = str(wlan.status())
    except Exception:
        pass
    return None, "WiFi fail s={}".format(status)


def has_keys(mapping, keys):
    if not mapping:
        return False
    for key in keys:
        if key not in mapping:
            return False
    return True


def custom_assets_ready():
    return (
        has_keys(FONT_UI_BIG, REQUIRED_UI_BIG_CHARS)
        and has_keys(FONT_JP, REQUIRED_JP_CHARS)
        and has_keys(FONT_TIME, REQUIRED_TIME_CHARS)
        and has_keys(FONT_DATE, REQUIRED_DATE_CHARS)
    )


def show_asset_error_screen():
    graphics.set_pen(BLACK)
    graphics.clear()
    graphics.set_pen(WHITE)
    set_footer_font()
    graphics.text("FATAL: custom bitmap assets missing", 20, 40, WIDTH - 40, 2)
    graphics.text("Arial/Japanese assets are required.", 20, 80, WIDTH - 40, 2)
    graphics.text("Re-deploy custom_bitmaps.py + main.py", 20, 120, WIDTH - 40, 2)
    graphics.text("Then press RESET and E once.", 20, 160, WIDTH - 40, 2)
    if CUSTOM_BITMAPS_IMPORT_ERROR:
        graphics.text("Import error: {}".format(CUSTOM_BITMAPS_IMPORT_ERROR), 20, 200, WIDTH - 40, 2)
    missing = []
    if not has_keys(FONT_UI_BIG, REQUIRED_UI_BIG_CHARS):
        missing.append("FONT_UI_BIG")
    if not has_keys(FONT_JP, REQUIRED_JP_CHARS):
        missing.append("FONT_JP")
    if not has_keys(FONT_TIME, REQUIRED_TIME_CHARS):
        missing.append("FONT_TIME")
    if not has_keys(FONT_DATE, REQUIRED_DATE_CHARS):
        missing.append("FONT_DATE")
    if missing:
        graphics.text("Missing: {}".format(", ".join(missing)), 20, 240, WIDTH - 40, 2)
    graphics.update()


def disconnect_wifi(wlan):
    """Turn Wi-Fi fully off between refreshes to save power."""
    if not wlan:
        return
    try:
        wlan.disconnect()
    except Exception:
        pass
    try:
        wlan.active(False)
    except Exception:
        pass


def sync_time_ntp():
    """Best-effort sync compatible with older/newer Inky firmware builds."""
    ntptime.timeout = 10
    hosts = ("pool.ntp.org", "time.google.com", "time.cloudflare.com")
    last_err = "unknown"

    for host in hosts:
        ntptime.host = host
        for _ in range(NTP_RETRIES):
            try:
                # Some firmware builds expose inky_frame.set_time(), others do not.
                if hasattr(inky_frame, "set_time"):
                    inky_frame.set_time()
                else:
                    ntptime.settime()
                return True, "NTP ok"
            except Exception as exc:
                last_err = type(exc).__name__
                time.sleep(1)

    return False, "NTP fail {}".format(last_err)


def timezone_struct(utc_epoch, offset_hours):
    """Return a gmtime tuple shifted by fixed hour offset."""
    return time.gmtime(utc_epoch + (offset_hours * 3600))


def fmt_time(t):
    return "{:02d}:{:02d}".format(t[3], t[4])


def fmt_date(t):
    return "{:04d}/{:02d}/{:02d}".format(t[0], t[1], t[2])


def fmt_date_jp(t):
    return "{:04d}年{:02d}月{:02d}日".format(t[0], t[1], t[2])


def clock_looks_valid(utc_epoch):
    """Treat default firmware RTC years as invalid until NTP sync succeeds."""
    return time.gmtime(utc_epoch)[0] >= MIN_VALID_YEAR


def read_mode_button(current_mode):
    """Return selected mode from A-D if a button is pressed."""
    try:
        if inky_frame.button_a.read():
            return MODE_A
        if inky_frame.button_b.read():
            return MODE_B
        if inky_frame.button_c.read():
            return MODE_C
        if inky_frame.button_d.read():
            return MODE_D
    except Exception:
        pass
    return current_mode


def force_refresh_pressed():
    """E button forces immediate refresh."""
    try:
        return inky_frame.button_e.read()
    except Exception:
        return False


def wifi_label(wlan):
    if wlan and wlan.isconnected() and secrets:
        ssid = getattr(secrets, "WIFI_SSID", "")
        if ssid:
            return "WiFi: {}".format(ssid)
        return "WiFi: connected"
    return "WiFi: off"


def midnight_epoch(utc_struct):
    """Epoch for midnight UTC for a given UTC date struct."""
    return time.mktime((utc_struct[0], utc_struct[1], utc_struct[2], 0, 0, 0, 0, 0))


def next_meetings(now_utc_epoch, count=5):
    """Return upcoming meeting epochs in UTC from a simple daily schedule."""
    candidates = []
    for day_offset in range(0, 5):
        day_struct = time.gmtime(now_utc_epoch + (day_offset * 86400))
        day0 = midnight_epoch(day_struct)
        for title, hour_utc, minute_utc in SAMPLE_MEETINGS_UTC:
            candidates.append((title, day0 + (hour_utc * 3600) + (minute_utc * 60)))

    candidates.sort(key=lambda item: item[1])
    return [item for item in candidates if item[1] >= now_utc_epoch][:count]


def fmt_meeting_line(meeting, offset_hours):
    title, utc_epoch = meeting
    local_t = timezone_struct(utc_epoch, offset_hours)
    return "{} {:02d}:{:02d}".format(title, local_t[3], local_t[4])


def overlap_text_lines(now_utc_epoch):
    """D mode: simple overlap helper for planning calls."""
    now_pst = timezone_struct(now_utc_epoch, PST_OFFSET_HOURS)
    now_jst = timezone_struct(now_utc_epoch, JST_OFFSET_HOURS)

    # Suggested overlap windows (PST), then auto-converted for JST display text.
    windows_pst = [(16, 0, 18, 0), (19, 0, 21, 0)]
    lines = [
        "Best overlap windows:",
        "",
    ]

    for start_h, start_m, end_h, end_m in windows_pst:
        start_j_h = (start_h + 17) % 24
        end_j_h = (end_h + 17) % 24
        lines.append(
            "PST {:02d}:{:02d}-{:02d}:{:02d} | JST {:02d}:{:02d}-{:02d}:{:02d}".format(
                start_h,
                start_m,
                end_h,
                end_m,
                start_j_h,
                start_m,
                end_j_h,
                end_m,
            )
        )

    lines.append("")
    lines.append("Now PST {:02d}:{:02d} | JST {:02d}:{:02d}".format(now_pst[3], now_pst[4], now_jst[3], now_jst[4]))
    return lines


def set_best_font():
    """Use a cleaner font if available on this firmware, else fall back."""
    # sans is the closest built-in style to Arial/Helvetica.
    for font_name in ("sans", "bitmap8"):
        try:
            graphics.set_font(font_name)
            return
        except Exception:
            pass


def set_footer_font():
    """Use classic bitmap footer text regardless of main font style."""
    try:
        graphics.set_font("bitmap8")
    except Exception:
        pass


def draw_text_bold(text, x, y, w, scale, bold=True):
    """Pseudo-bold text by drawing with tiny offsets (set_thickness unsupported)."""
    graphics.text(text, x, y, w, scale)
    if bold:
        graphics.text(text, x + 1, y, w, scale)
        graphics.text(text, x, y + 1, w, scale)
        graphics.text(text, x + 1, y + 1, w, scale)
        graphics.text(text, x + 2, y, w, scale)


def draw_bitmap_label(key, x, y):
    """Draw pre-rendered 1-bit label bitmap, returns True on success."""
    if not FONT_JP or key not in FONT_JP:
        return False

    data = FONT_JP[key]
    rows = data.get("rows", [])
    for yy, row in enumerate(rows):
        for xx, pix in enumerate(row):
            if pix == "#":
                graphics.pixel(x + xx, y + yy)
    return True


def draw_named_bitmap(dict_map, key, x, y):
    if not dict_map or key not in dict_map:
        return False
    data = dict_map[key]
    for yy, row in enumerate(data.get("rows", [])):
        for xx, pix in enumerate(row):
            if pix == "#":
                graphics.pixel(x + xx, y + yy)
    return True


def draw_bitmap_label_centered(key, x, y, max_width):
    if not FONT_JP or key not in FONT_JP:
        return False
    w = FONT_JP[key].get("w", 0)
    start_x = x + max((max_width - w) // 2, 0)
    return draw_named_bitmap(FONT_JP, key, start_x, y)


def draw_jp_weekday(weekday_key, x, y, max_width):
    jp_text = {
        "MONDAY": "月曜日",
        "TUESDAY": "火曜日",
        "WEDNESDAY": "水曜日",
        "THURSDAY": "木曜日",
        "FRIDAY": "金曜日",
        "SATURDAY": "土曜日",
        "SUNDAY": "日曜日",
    }.get(weekday_key)
    if not jp_text:
        return False
    return draw_bitmap_text(jp_text, FONT_JP, x, y, max_width, spacing=1)


def measure_bitmap_text(text, font_map, spacing=2):
    if not font_map:
        return 0
    total = 0
    for i, ch in enumerate(text):
        glyph = font_map.get(ch)
        if not glyph:
            continue
        total += glyph["w"]
        if i < len(text) - 1:
            total += spacing
    return total


def draw_bitmap_text(text, font_map, x, y, max_width, spacing=2):
    """Draw text from custom bitmap glyphs centered in the provided width."""
    if not font_map:
        return False

    text_w = measure_bitmap_text(text, font_map, spacing=spacing)
    start_x = x + max((max_width - text_w) // 2, 0)
    cx = start_x

    for ch in text:
        glyph = font_map.get(ch)
        if not glyph:
            continue
        for yy, row in enumerate(glyph.get("rows", [])):
            for xx, pix in enumerate(row):
                if pix == "#":
                    graphics.pixel(cx + xx, y + yy)
        cx += glyph["w"] + spacing
    return True


def fit_scale(text, max_scale, min_scale=1, max_width=None):
    """Find the largest text scale that fits in the target width."""
    if max_width is None:
        max_width = COL_W - 8
    for scale in range(max_scale, min_scale - 1, -1):
        try:
            if graphics.measure_text(text, scale=scale) <= max_width:
                return scale
        except Exception:
            # Older firmware sometimes has stricter measure_text signatures.
            if graphics.measure_text(text, scale) <= max_width:
                return scale
    return min_scale


def clear_inverted():
    graphics.set_pen(BLACK)
    graphics.clear()
    graphics.set_pen(WHITE)


def draw_mode_a(pst, jst, sync_ok, wifi_text):
    clear_inverted()
    set_best_font()

    # Strict 2-column layout.
    graphics.rectangle((WIDTH // 2) - 2, 0, 4, HEIGHT)

    # Bottom-align city titles, then keep Japanese labels centered just below.
    title_h = 0
    if FONT_UI_BIG:
        title_h = max((glyph.get("h", 0) for glyph in FONT_UI_BIG.values()), default=0)
    # Draw title text bottom-aligned in its area (calculate y so glyphs' bottoms align)
    def bottom_align_bitmap_text(text, font_map, x, y_bottom, max_width, spacing=COL_W_SPACING):
        h = max((font_map[ch]["h"] for ch in text if ch in font_map), default=0)
        y = y_bottom - h
        return draw_bitmap_text(text, font_map, x, y, max_width, spacing=spacing)

    bottom_align_bitmap_text("Vancouver", FONT_UI_BIG, LEFT_X, TITLE_BOTTOM, COL_W, spacing=COL_W_SPACING)
    bottom_align_bitmap_text("Tokyo", FONT_UI_BIG, RIGHT_X, TITLE_BOTTOM, COL_W, spacing=COL_W_SPACING)

    # Japanese labels centered under titles with tighter spacing.
    jp_y = TITLE_BOTTOM + JP_LABEL_Y_OFFSET
    bottom_align_bitmap_text("バンクーバー", FONT_JP, LEFT_X, jp_y + max((FONT_JP[ch]["h"] for ch in "バンクーバー" if ch in FONT_JP), default=0), COL_W, spacing=COL_W_SPACING)
    bottom_align_bitmap_text("東京", FONT_JP, RIGHT_X, jp_y + max((FONT_JP[ch]["h"] for ch in "東京" if ch in FONT_JP), default=0), COL_W, spacing=COL_W_SPACING)
    set_best_font()

    # Render times from thick custom bitmap digit font, bottom-aligned, 25% larger if possible
    pst_time = fmt_time(pst)
    jst_time = fmt_time(jst)
    def bottom_align_bitmap_time(text, font_map, x, y_bottom, max_width, spacing=TIME_SPACING, scale_factor=TIME_SCALE_FACTOR):
        h = max((font_map[ch]["h"] for ch in text if ch in font_map), default=0)
        y = y_bottom - int(h * scale_factor)
        return draw_bitmap_text(text, font_map, x, y, max_width, spacing=spacing)
    bottom_align_bitmap_time(pst_time, FONT_TIME, LEFT_X, TIME_Y_BOTTOM, COL_W, spacing=TIME_SPACING, scale_factor=TIME_SCALE_FACTOR)
    bottom_align_bitmap_time(jst_time, FONT_TIME, RIGHT_X, TIME_Y_BOTTOM, COL_W, spacing=TIME_SPACING, scale_factor=TIME_SCALE_FACTOR)

    # Render dates from custom bitmap date font, bottom-aligned
    pst_date = fmt_date(pst)
    jst_date = fmt_date_jp(jst)
    def bottom_align_bitmap_date(text, font_map, x, y_bottom, max_width, spacing=DATE_SPACING):
        h = max((font_map[ch]["h"] for ch in text if ch in font_map), default=0)
        y = y_bottom - h
        return draw_bitmap_text(text, font_map, x, y, max_width, spacing=spacing)
    bottom_align_bitmap_date(pst_date, FONT_DATE, LEFT_X, DATE_Y_BOTTOM, COL_W, spacing=DATE_SPACING)
    bottom_align_bitmap_date(jst_date, FONT_DATE, RIGHT_X, DATE_Y_BOTTOM, COL_W, spacing=DATE_SPACING)

    # Center the weekday name below the date, using bitmap font for English and Japanese
    weekday_keys = ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY")
    weekday_en_map = {
        "MONDAY": "Monday",
        "TUESDAY": "Tuesday",
        "WEDNESDAY": "Wednesday",
        "THURSDAY": "Thursday",
        "FRIDAY": "Friday",
        "SATURDAY": "Saturday",
        "SUNDAY": "Sunday",
    }
    pst_weekday_key = weekday_keys[pst[6] % 7]
    jst_weekday_key = weekday_keys[jst[6] % 7]
    # English weekday (bitmap font, bottom-aligned, centered)
    weekday_text = weekday_en_map.get(pst_weekday_key, "Monday")
    def bottom_align_bitmap_weekday(text, font_map, x, y_bottom, max_width, spacing=COL_W_SPACING):
        h = max((font_map[ch]["h"] for ch in text if ch in font_map), default=0)
        y = y_bottom - h
        return draw_bitmap_text(text, font_map, x, y, max_width, spacing=spacing)
    bottom_align_bitmap_weekday(weekday_text, FONT_UI_BIG, LEFT_X, WEEKDAY_Y_BOTTOM, COL_W, spacing=COL_W_SPACING)
    # Japanese weekday already centered by draw_jp_weekday, bottom-aligned
    jp_weekday_y = WEEKDAY_Y_BOTTOM
    draw_jp_weekday(jst_weekday_key, RIGHT_X, jp_weekday_y, COL_W)

    status = "A Dual clocks | NTP synced" if sync_ok else "A Dual clocks | Clock not synced"
    set_footer_font()
    draw_text_bold(status, 20, HEIGHT - 54, WIDTH - 40, 2, bold=False)
    draw_text_bold("E=Refresh", 20, HEIGHT - 34, WIDTH // 2, 2, bold=False)
    draw_text_bold(wifi_text, WIDTH // 2, HEIGHT - 34, (WIDTH // 2) - 20, 2, bold=False)

    graphics.update()


def draw_mode_b(now_utc_epoch, pst, sync_ok, wifi_text):
    meetings = next_meetings(now_utc_epoch, count=5)

    clear_inverted()
    set_best_font()

    draw_text_bold("B Vancouver + Meetings", 20, 14, WIDTH - 40, 2, bold=False)
    draw_text_bold("VANCOUVER (PST)", 20, 48, WIDTH - 40, 2)
    draw_text_bold(fmt_time(pst), 20, 96, WIDTH - 40, 5)
    draw_text_bold(fmt_date(pst), 20, 200, WIDTH - 40, 2)

    y = 240
    draw_text_bold("Upcoming:", 20, y, WIDTH - 40, 2, bold=False)
    y += 30
    for meeting in meetings:
        draw_text_bold(fmt_meeting_line(meeting, PST_OFFSET_HOURS), 20, y, WIDTH - 40, 2, bold=False)
        y += 28

    status = "NTP synced" if sync_ok else "Clock not synced"
    set_footer_font()
    draw_text_bold(status, 20, HEIGHT - 54, WIDTH - 40, 2, bold=False)
    draw_text_bold("E=Refresh", 20, HEIGHT - 34, WIDTH // 2, 2, bold=False)
    draw_text_bold(wifi_text, WIDTH // 2, HEIGHT - 34, (WIDTH // 2) - 20, 2, bold=False)
    graphics.update()


def draw_mode_c(now_utc_epoch, jst, sync_ok, wifi_text):
    meetings = next_meetings(now_utc_epoch, count=5)

    clear_inverted()
    set_best_font()

    draw_text_bold("C Tokyo + Meetings", 20, 14, WIDTH - 40, 2, bold=False)
    draw_text_bold("TOKYO (JST)", 20, 48, WIDTH - 40, 2)
    draw_text_bold(fmt_time(jst), 20, 96, WIDTH - 40, 5)
    draw_text_bold(fmt_date(jst), 20, 200, WIDTH - 40, 2)

    y = 240
    draw_text_bold("Upcoming:", 20, y, WIDTH - 40, 2, bold=False)
    y += 30
    for meeting in meetings:
        draw_text_bold(fmt_meeting_line(meeting, JST_OFFSET_HOURS), 20, y, WIDTH - 40, 2, bold=False)
        y += 28

    status = "NTP synced" if sync_ok else "Clock not synced"
    set_footer_font()
    draw_text_bold(status, 20, HEIGHT - 54, WIDTH - 40, 2, bold=False)
    draw_text_bold("E=Refresh", 20, HEIGHT - 34, WIDTH // 2, 2, bold=False)
    draw_text_bold(wifi_text, WIDTH // 2, HEIGHT - 34, (WIDTH // 2) - 20, 2, bold=False)
    graphics.update()


def draw_mode_d(now_utc_epoch, sync_ok, wifi_text):
    clear_inverted()
    set_best_font()

    draw_text_bold("D Overlap Helper", 20, 14, WIDTH - 40, 2, bold=False)
    y = 62
    for line in overlap_text_lines(now_utc_epoch):
        draw_text_bold(line, 20, y, WIDTH - 40, 2, bold=False)
        y += 30

    status = "NTP synced" if sync_ok else "Clock not synced"
    set_footer_font()
    draw_text_bold(status, 20, HEIGHT - 54, WIDTH - 40, 2, bold=False)
    draw_text_bold("E=Refresh", 20, HEIGHT - 34, WIDTH // 2, 2, bold=False)
    draw_text_bold(wifi_text, WIDTH // 2, HEIGHT - 34, (WIDTH // 2) - 20, 2, bold=False)
    graphics.update()


def draw_mode_e(pst, jst, sync_ok, wifi_text):
    clear_inverted()
    set_best_font()

    graphics.rectangle((WIDTH // 2) - 2, 0, 4, HEIGHT)

    # Note: full kanji rendering needs custom font data; default firmware fonts are limited.
    draw_text_bold("E Nihongo View", 20, 14, WIDTH - 40, 2, bold=False)
    draw_text_bold("VANCOUVER", LEFT_X, 52, COL_W, 2)
    draw_text_bold("TOKYO", RIGHT_X, 52, COL_W, 2)

    draw_text_bold(fmt_time(pst), LEFT_X, 120, COL_W, 6)
    draw_text_bold(fmt_time(jst), RIGHT_X, 120, COL_W, 6)

    draw_text_bold("PST", LEFT_X, 236, COL_W, 2, bold=False)
    draw_text_bold("JST", RIGHT_X, 236, COL_W, 2, bold=False)

    draw_text_bold("{:04d}/{:02d}/{:02d}".format(pst[0], pst[1], pst[2]), LEFT_X, 270, COL_W, 2)
    draw_text_bold("{:04d}/{:02d}/{:02d}".format(jst[0], jst[1], jst[2]), RIGHT_X, 270, COL_W, 2)

    status = "NTP synced" if sync_ok else "Clock not synced"
    set_footer_font()
    draw_text_bold(status, 20, HEIGHT - 54, WIDTH - 40, 2, bold=False)
    draw_text_bold("E=Refresh", 20, HEIGHT - 34, WIDTH // 2, 2, bold=False)
    draw_text_bold(wifi_text, WIDTH // 2, HEIGHT - 34, (WIDTH // 2) - 20, 2, bold=False)
    graphics.update()


def draw_by_mode(mode_key, now_utc_epoch, pst, jst, sync_ok, wifi_text):
    if mode_key == MODE_A:
        draw_mode_a(pst, jst, sync_ok, wifi_text)
        return
    if mode_key == MODE_B:
        draw_mode_b(now_utc_epoch, pst, sync_ok, wifi_text)
        return
    if mode_key == MODE_C:
        draw_mode_c(now_utc_epoch, jst, sync_ok, wifi_text)
        return
    if mode_key == MODE_D:
        draw_mode_d(now_utc_epoch, sync_ok, wifi_text)
        return
    draw_mode_e(pst, jst, sync_ok, wifi_text)


def main():
    if not custom_assets_ready():
        show_asset_error_screen()
        while True:
            time.sleep(60)

    ntp_ok = False
    sync_text = "NTP: pending"
    wifi_text = "WiFi: off"
    mode = MODE_A

    utc_epoch = time.time()
    wlan, wifi_text = connect_wifi()
    if wlan:
        ntp_ok, sync_text = sync_time_ntp()
    disconnect_wifi(wlan)
    if wifi_text.startswith("WiFi: ") and wlan is not None:
        wifi_text = "WiFi: off (last ok)"
    utc_epoch = time.time()

    pst = timezone_struct(utc_epoch, PST_OFFSET_HOURS)
    jst = timezone_struct(utc_epoch, JST_OFFSET_HOURS)

    draw_by_mode(mode, utc_epoch, pst, jst, ntp_ok, "{} | {}".format(sync_text, wifi_text))

    # Poll buttons quickly, refresh data every 5 minutes (or E button).
    next_refresh = time.time() + REFRESH_SECONDS
    prev_e_pressed = False
    while True:
        mode_new = read_mode_button(mode)
        if mode_new != mode:
            mode = mode_new
            utc_epoch = time.time()
            pst = timezone_struct(utc_epoch, PST_OFFSET_HOURS)
            jst = timezone_struct(utc_epoch, JST_OFFSET_HOURS)
            draw_by_mode(mode, utc_epoch, pst, jst, ntp_ok, "{} | {}".format(sync_text, wifi_text))
            time.sleep(0.2)
            continue

        now_epoch = time.time()
        e_pressed = force_refresh_pressed()
        manual_refresh = e_pressed and not prev_e_pressed
        prev_e_pressed = e_pressed
        if now_epoch >= next_refresh or manual_refresh:
            wlan, wifi_text = connect_wifi()
            if wlan:
                ntp_ok, sync_text = sync_time_ntp()
            disconnect_wifi(wlan)
            if wifi_text.startswith("WiFi: ") and wlan is not None:
                wifi_text = "WiFi: off (last ok)"

            utc_epoch = time.time()

            pst = timezone_struct(utc_epoch, PST_OFFSET_HOURS)
            jst = timezone_struct(utc_epoch, JST_OFFSET_HOURS)
            draw_by_mode(mode, utc_epoch, pst, jst, ntp_ok, "{} | {}".format(sync_text, wifi_text))

            next_refresh = now_epoch + REFRESH_SECONDS
            if manual_refresh:
                time.sleep(0.3)

        time.sleep(0.2)


main()
