# QwertyKey Rice 60% — Native Linux Driver & Suite

A native Linux driver, command-line interface (CLI), and modern desktop GUI for the **QwertyKey Rice 60%** mechanical keyboard with integrated LCD/TFT display.

Reverse-engineered from the original Windows MFC utility (`QwertyKey_Rice_V3.exe` / `DeviceDriver.exe`).

---

## Features

- **Backlight RGB Control**: All 20 hardware animation modes (Static, Rolling, Breathing, Spectrum, Ripples, Explode, etc.), customizable RGB colors, brightness, speed, direction, and rainbow/spectrum mode.
- **Side Light Control**: Modes, colors, brightness, and speed for keyboard side light bars.
- **LCD Clock Synchronization**: Sync keyboard TFT screen clock with host system time automatically or on-demand.
- **TFT GIF / Image Upload**: Upload custom animations and images (160×96 RGB565) to the keyboard screen with progress reporting.
- **Per-Key Custom RGB**: Interactive 60% visual key layout selector for assigning individual key backlighting.
- **Hardware Settings**: Sleep timeout (0, 1, 5, 30 min) and key debounce response times.
- **Battery Status & Wired Mode**: Queries device battery percentage and connection status.
- **Zero Kernel Drivers Needed**: Communicates directly through Linux standard `/dev/hidraw` ioctls (`HIDIOCSFEATURE` / `HIDIOCGFEATURE`).

---

## Hardware Protocol Details

- **Vendor ID (VID)**: `0x0C45` (Microdia / Sonix)
- **Product ID (PID)**: `0x8016`
- **HID Interface**: `0` (MI_00)
- **Report Structure**: 65 bytes total (Byte `0x00`: Report ID `0x00`, Bytes `1..64`: Command Payload).
- **Handshake Sequence**:
  1. `[0x04, 0x18]` (Config Enter)
  2. Subcommand Init (e.g. `[0x04, 0x13, ...]` for lighting, `[0x04, 0x28, ...]` for time, `[0x04, 0x72]` for TFT)
  3. Payload block(s) with trailer magic `0xAA, 0x55`
  4. `[0x04, 0x02]` (Config Apply)
  5. `[0x04, 0xF0]` (Config Exit / Save)
- **TFT Display**: 160×96 pixels, 16-bit Little-Endian RGB565 streamed in 4096-byte blocks.

---

## Installation & Setup

### 1. Udev Rules (Non-root USB Access)

To allow running the tools without `sudo`, copy the provided udev rules:

```bash
sudo cp udev/99-qwertykey.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger
```

### 2. Python Dependencies

```bash
pip install -r requirements.txt
# Or install in editable mode:
pip install -e .
```

Dependencies: `PyQt5`, `Pillow`.

---

## Graphical User Interface (GUI)

Launch the desktop application:

```bash
qwertykey-gui
# Or directly via Python:
python3 -m qwertykey.gui
```

### GUI Highlights
- **Backlight RGB Tab**: Choose from 20 effects with interactive preview, color picker, speed/brightness sliders, and rainbow switch.
- **Per-Key Custom RGB Tab**: Interactive visual 60% key matrix to click and color individual keys.
- **TFT Screen & GIF Tab**: Real-time LCD clock synchronization and animated GIF preview with upload progress bar.
- **Settings Tab**: Power sleep timeout, debounce tuning, and side light controls.
- **Top Bar**: Live battery percentage display and connection status.

---

## Command Line Interface (CLI)

The CLI tool allows fast automation, scripting, and cron integration:

### View Status & Battery
```bash
qwertykey info
```

### Backlight Control
```bash
# Set Rolling effect in rainbow mode
qwertykey light Rolling --rainbow --brightness 5 --speed 4

# Set Static red color
qwertykey light Static --color "#FF0000" --brightness 5

# Set Breath effect in cyan
qwertykey light Breath --color "#00FFFF" --speed 3
```

### Sync LCD Clock
```bash
# Sync keyboard clock to system time
qwertykey time
```

### Upload Screen Animation (GIF / PNG / JPG)
```bash
qwertykey tft /path/to/animation.gif
```

### Hardware Settings
```bash
# Set sleep timer to 5 minutes, debounce response to 1ms
qwertykey settings --sleep 5 --debounce 1
```

### Side Lights
```bash
qwertykey sidelight --mode 1 --color "#00FF00" --brightness 5
```

---

## Automatic Clock Sync via Cron / Systemd

To keep your keyboard's LCD clock accurate across system reboots or sleeps, add a cron job:

```bash
# Run every hour
0 * * * * qwertykey time >/dev/null 2>&1
```
