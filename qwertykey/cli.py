"""
QwertyKey Rice CLI Tool
Comprehensive command-line control for lighting, time sync, battery, settings, and TFT display.
"""

import argparse
import sys
import datetime
from .device import QwertyKeyDevice
from .protocol import LIGHT_MODES, SLEEP_TIMES

NAMED_COLORS = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "white": (255, 255, 255),
    "yellow": (255, 255, 0),
    "cyan": (0, 255, 255),
    "magenta": (255, 0, 255),
    "purple": (128, 0, 128),
    "orange": (255, 165, 0),
    "pink": (255, 192, 203),
    "off": (0, 0, 0),
    "black": (0, 0, 0),
}

def parse_color(color_str):
    color_str = color_str.strip().lower()
    if color_str in NAMED_COLORS:
        return NAMED_COLORS[color_str]
    c_str = color_str.lstrip('#')
    if len(c_str) == 3:
        c_str = ''.join([c*2 for c in c_str])
    if len(c_str) == 6:
        try:
            return tuple(int(c_str[i:i+2], 16) for i in (0, 2, 4))
        except ValueError:
            pass
    raise ValueError(f"Color '{color_str}' not recognized. Use color names (e.g. red, green, blue) or hex codes (e.g. FF0000, #00FF00)")

def cmd_info(args, dev):
    print(f"Device: QwertyKey Rice 60%")
    print(f"Path:   {dev.hidraw_path}")
    st = dev.get_battery_status()
    batt = st.get("battery", 0)
    batt_str = f"{batt}%" if batt > 0 else "Wired Mode / 100%"
    print(f"Battery: {batt_str}")
    print(f"Status: Connected and ready.")

def cmd_light(args, dev):
    # Lookup mode by id or name
    mode_arg = args.mode or "Static"
    mode_id = None
    if mode_arg.isdigit():
        mode_id = int(mode_arg)
        if mode_id not in LIGHT_MODES:
            print(f"Error: Invalid mode id {mode_id}. Must be 0-19.", file=sys.stderr)
            sys.exit(1)
    else:
        for mid, info in LIGHT_MODES.items():
            if info["name"].lower() == mode_arg.lower():
                mode_id = mid
                break
        if mode_id is None:
            print(f"Error: Unknown mode name '{mode_arg}'.", file=sys.stderr)
            print("Available modes:")
            for mid, info in sorted(LIGHT_MODES.items()):
                print(f"  {mid:2d}: {info['name']}")
            sys.exit(1)

    r, g, b = parse_color(args.color)
    colorful = 1 if args.rainbow else 0

    print(f"Applying light effect: {LIGHT_MODES[mode_id]['name']} (ID: {mode_id})")
    print(f"Color: RGB({r}, {g}, {b}) | Rainbow: {bool(colorful)}")
    print(f"Brightness: {args.brightness} (0-5) | Speed: {args.speed} (1-5) | Direction: {args.direction}")

    dev.set_lighting(
        mode=mode_id,
        r=r,
        g=g,
        b=b,
        brightness=args.brightness,
        speed=args.speed,
        direction=args.direction,
        colorful=colorful
    )
    print("✓ Lighting applied successfully.")

def cmd_sidelight(args, dev):
    r, g, b = parse_color(args.color)
    print(f"Applying side light: Mode {args.mode}, RGB({r}, {g}, {b}), Brightness: {args.brightness}, Speed: {args.speed}")
    dev.set_side_light(
        mode=args.mode,
        r=r,
        g=g,
        b=b,
        brightness=args.brightness,
        speed=args.speed
    )
    print("✓ Side light applied successfully.")

def cmd_time(args, dev):
    now = datetime.datetime.now()
    print(f"Synchronizing keyboard LCD clock to system time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    dev.sync_time(now, screen_idx=args.screen)
    print("✓ Time synchronized successfully.")

def cmd_settings(args, dev):
    print(f"Configuring settings: Sleep = {args.sleep} min, Debounce = {args.debounce} ms")
    dev.set_settings(
        sleep_time=args.sleep,
        key_respondtime=args.debounce
    )
    print("✓ Settings applied successfully.")

def cmd_tft(args, dev):
    print(f"Preparing to upload image/GIF to LCD screen: {args.file}")
    
    def on_progress(percent):
        sys.stdout.write(f"\rUploading: [{('=' * (percent // 2)).ljust(50)}] {percent}%")
        sys.stdout.flush()

    dev.upload_tft_gif(args.file, progress_callback=on_progress)
    print("\n✓ TFT upload complete.")

def main():
    parser = argparse.ArgumentParser(description="QwertyKey Rice Keyboard Linux CLI")
    parser.add_argument("--device", "-d", help="Custom hidraw path (e.g. /dev/hidraw3)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Info
    p_info = subparsers.add_parser("info", help="Show keyboard status and battery")

    # Light
    p_light = subparsers.add_parser("light", help="Set RGB backlight effects")
    p_light.add_argument("mode", nargs="?", default="Static", help="Mode number (0-19) or name (e.g. Static, Rolling, Breath) [default: Static]")
    p_light.add_argument("--color", "-c", default="#FF0000", help="Color name or hex code (e.g. red, green, #FF0000) [default: #FF0000]")
    p_light.add_argument("--brightness", "-b", type=int, default=5, choices=range(0, 6), help="Brightness 0-5 (default: 5)")
    p_light.add_argument("--speed", "-s", type=int, default=3, choices=range(1, 6), help="Speed 1-5 (default: 3)")
    p_light.add_argument("--direction", type=int, default=1, choices=[1, 2], help="1=Left/Up, 2=Right/Down")
    p_light.add_argument("--rainbow", "-r", action="store_true", help="Enable spectrum/rainbow dynamic colors")

    # Side light
    p_side = subparsers.add_parser("sidelight", help="Set side light effects")
    p_side.add_argument("--mode", "-m", type=int, default=1, choices=range(0, 5), help="Mode 0-4")
    p_side.add_argument("--color", "-c", default="#00FF00", help="Color name or hex code (default: #00FF00)")
    p_side.add_argument("--brightness", "-b", type=int, default=5, choices=range(0, 6))
    p_side.add_argument("--speed", "-s", type=int, default=3, choices=range(1, 6))

    # Time
    p_time = subparsers.add_parser("time", help="Sync system clock to keyboard LCD display")
    p_time.add_argument("--screen", type=int, default=0, help="Screen index (default: 0)")

    # Settings
    p_settings = subparsers.add_parser("settings", help="Set sleep timer and debounce")
    p_settings.add_argument("--sleep", type=int, default=5, choices=[0, 1, 5, 30], help="Sleep timeout in minutes (0=Disabled)")
    p_settings.add_argument("--debounce", type=int, default=1, choices=range(1, 11), help="Key debounce response time (ms)")

    # TFT
    p_tft = subparsers.add_parser("tft", help="Upload GIF or image to LCD screen (160x96)")
    p_tft.add_argument("file", help="Path to GIF, PNG, or JPEG file")

    args = parser.parse_args()

    try:
        dev = QwertyKeyDevice(args.device)
        dev.open()
    except Exception as e:
        print(f"Error opening keyboard: {e}", file=sys.stderr)
        print("Tip: Check USB connection or ensure you have read/write access to /dev/hidraw*", file=sys.stderr)
        sys.exit(1)

    try:
        if args.command == "info":
            cmd_info(args, dev)
        elif args.command == "light":
            cmd_light(args, dev)
        elif args.command == "sidelight":
            cmd_sidelight(args, dev)
        elif args.command == "time":
            cmd_time(args, dev)
        elif args.command == "settings":
            cmd_settings(args, dev)
        elif args.command == "tft":
            cmd_tft(args, dev)
    finally:
        dev.close()

if __name__ == "__main__":
    main()
