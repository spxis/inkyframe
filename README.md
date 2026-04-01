# InkyFrame 7.3 Time MVP

A MicroPython world clock and meeting board for Pimoroni InkyFrame (RP2040/Pico W). Shows dual time zones (Vancouver & Tokyo), local/JP dates, and meetings with custom bitmap fonts (including kanji). Features WiFi NTP sync, button modes, and a memory-safe, customizable e-paper display.

This MVP replaces the screen content with two fixed-offset clocks:
- Vancouver (Pacific Time, UTC offset set in code; does not auto-adjust for DST)
- Japan (JST, UTC+9)

## 1) Device prerequisites

1. Flash Pimoroni MicroPython firmware for InkyFrame 7.3 (Pico W).
2. Connect the board to your Mac over USB.
3. Ensure the board appears to `mpremote` as a USB serial device.

## 2) Install deployment tool on macOS

```bash
python3 -m pip install --user mpremote
```

If `mpremote` is not on your PATH, use:

```bash
python3 -m mpremote --help
```

## 3) Configure Wi-Fi credentials

Create `secrets.py` from the template:

```bash
cp secrets.py.example secrets.py
```

Then edit `secrets.py` with your Wi-Fi SSID and password.

## 4) Push files over USB (fast path)

From this project folder:

```bash
mpremote fs cp main.py :main.py
mpremote fs cp secrets.py :secrets.py
mpremote reset
```

This will reboot the Pico W and run `main.py`, updating the display.

## 5) Verify update

The e-ink screen should show:
- Title: "InkyFrame 7.3 - Time MVP"
- Vancouver (Pacific Time)
- Japan (JST)

## Notes

- No battery required for development over USB.
- microSD is not required for this MVP.
- If Wi-Fi/NTP fails, the app still renders using current RTC time.

## Next step ideas

- Pull upcoming meetings from a small JSON feed.
- Add overlap-time suggestions between PST and JST.
- Add a button-triggered immediate refresh.
