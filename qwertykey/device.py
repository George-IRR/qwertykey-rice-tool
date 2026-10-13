"""
QwertyKey Rice Device Driver
Direct Linux HID interface communication via /dev/hidraw.
"""

import os
import glob
import fcntl
import time
import datetime
from .protocol import (
    VENDOR_ID, PRODUCT_ID, INTERFACE_NUM, REPORT_LENGTH, CMD_DELAY,
    CMD_CONFIG_ENTER, CMD_CONFIG_INIT, CMD_CONFIG_APPLY, CMD_CONFIG_EXIT,
    CMD_TIME_INIT, CMD_CUSTOM_RGB_INIT, CMD_CUSTOM_RGB_READ,
    CMD_TFT_ENTER, CMD_BATTERY_QUERY, MAGIC_55AA,
    TFT_CHUNK_SIZE
)
from .tft import load_gif_or_image

def _HIDIOCSFEATURE(length):
    return (3 << 30) | (ord('H') << 8) | 0x06 | (length << 16)

def _HIDIOCGFEATURE(length):
    return (3 << 30) | (ord('H') << 8) | 0x07 | (length << 16)

class QwertyKeyDevice:
    def __init__(self, hidraw_path=None):
        self.hidraw_path = hidraw_path or self.find_device()
        self.fd = None

    @classmethod
    def find_device(cls, interface=INTERFACE_NUM):
        """Auto-discover the QwertyKey Rice hidraw device node."""
        target_vid = f"{VENDOR_ID:04X}"
        target_pid = f"{PRODUCT_ID:04X}"
        target_input = f"input{interface}"

        for path in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
            dev_name = os.path.basename(path)
            uevent_path = os.path.join(path, "device", "uevent")
            if not os.path.exists(uevent_path):
                continue
            with open(uevent_path, "r", errors="ignore") as f:
                content = f.read()
            if target_vid in content and target_pid in content and target_input in content:
                node = f"/dev/{dev_name}"
                if os.path.exists(node):
                    return node
        
        # Fallback: any node with matching VID/PID
        for path in sorted(glob.glob("/sys/class/hidraw/hidraw*")):
            dev_name = os.path.basename(path)
            uevent_path = os.path.join(path, "device", "uevent")
            if not os.path.exists(uevent_path):
                continue
            with open(uevent_path, "r", errors="ignore") as f:
                content = f.read()
            if target_vid in content and target_pid in content:
                node = f"/dev/{dev_name}"
                if os.path.exists(node):
                    return node

        return None

    def open(self):
        if not self.hidraw_path:
            raise FileNotFoundError("QwertyKey Rice keyboard not found on USB/hidraw!")
        if not os.path.exists(self.hidraw_path):
            raise FileNotFoundError(f"Device node {self.hidraw_path} does not exist.")
        self.fd = os.open(self.hidraw_path, os.O_RDWR)
        return self

    def close(self):
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def send_feature_report(self, payload):
        """
        Send a 64-byte payload as a 65-byte HID feature report (Report ID = 0x00).
        """
        if self.fd is None:
            raise RuntimeError("Device is not open.")
        buf = bytearray(REPORT_LENGTH)
        buf[0] = 0x00  # Report ID
        buf[1:1 + min(len(payload), 64)] = payload[:64]
        cmd = _HIDIOCSFEATURE(REPORT_LENGTH)
        fcntl.ioctl(self.fd, cmd, buf)

    def get_feature_report(self):
        """
        Read a 65-byte HID feature report from the device.
        """
        if self.fd is None:
            raise RuntimeError("Device is not open.")
        buf = bytearray(REPORT_LENGTH)
        cmd = _HIDIOCGFEATURE(REPORT_LENGTH)
        fcntl.ioctl(self.fd, cmd, buf)
        return bytes(buf)

    def send_command(self, payload, delay=CMD_DELAY):
        self.send_feature_report(payload)
        if delay > 0:
            time.sleep(delay)

    def set_lighting(self, mode=11, r=255, g=0, b=0, brightness=5, speed=3, direction=1, colorful=1):
        """
        Set keyboard lighting mode and parameters.
        mode: 0-19 (e.g. 11=Rolling, 1=Static, 7=Breath)
        r, g, b: 0-255
        brightness: 0-5
        speed: 1-5
        direction: 1 (Left/Up) or 2 (Right/Down)
        colorful: 1 for rainbow/spectrum, 0 for custom RGB
        """
        # Step 1: Config enter
        p1 = bytearray(64)
        p1[0:2] = CMD_CONFIG_ENTER
        self.send_command(p1)

        # Step 2: Config init
        p2 = bytearray(64)
        p2[0:2] = CMD_CONFIG_INIT
        p2[8] = 0x01
        self.send_command(p2)

        # Step 3: Mode and color packet
        p3 = bytearray(64)
        p3[0] = mode & 0xFF
        p3[1] = r & 0xFF
        p3[2] = g & 0xFF
        p3[3] = b & 0xFF
        p3[8] = colorful & 0xFF
        p3[9] = brightness & 0xFF
        p3[10] = speed & 0xFF
        p3[11] = direction & 0xFF
        p3[14:16] = MAGIC_55AA
        self.send_command(p3)

        # Step 4: Apply
        p4 = bytearray(64)
        p4[0:2] = CMD_CONFIG_APPLY
        self.send_command(p4)

        # Step 5: Save/Exit
        p5 = bytearray(64)
        p5[0:2] = CMD_CONFIG_EXIT
        self.send_command(p5)

    def set_side_light(self, mode=1, r=255, g=0, b=0, brightness=5, speed=3):
        """Set keyboard side light mode."""
        p1 = bytearray(64)
        p1[0:2] = CMD_CONFIG_ENTER
        self.send_command(p1)

        p2 = bytearray(64)
        p2[0:2] = CMD_CONFIG_INIT
        p2[8] = 0x01
        self.send_command(p2)

        p3 = bytearray(64)
        p3[0] = mode & 0xFF
        p3[1] = r & 0xFF
        p3[2] = g & 0xFF
        p3[3] = b & 0xFF
        p3[9] = brightness & 0xFF
        p3[10] = speed & 0xFF
        p3[14:16] = MAGIC_55AA
        self.send_command(p3)

        p4 = bytearray(64)
        p4[0:2] = CMD_CONFIG_APPLY
        self.send_command(p4)

        p5 = bytearray(64)
        p5[0:2] = CMD_CONFIG_EXIT
        self.send_command(p5)

    def sync_time(self, dt=None, screen_idx=0):
        """
        Synchronize system clock or specified datetime to keyboard LCD screen.
        """
        if dt is None:
            dt = datetime.datetime.now()

        # Step 1: Config enter
        p1 = bytearray(64)
        p1[0:2] = CMD_CONFIG_ENTER
        self.send_command(p1)

        # Step 2: Time init
        p2 = bytearray(64)
        p2[0:2] = CMD_TIME_INIT
        p2[8] = 0x01
        self.send_command(p2)

        # Step 3: Time payload
        p3 = bytearray(64)
        p3[0] = 0x00
        p3[1] = (screen_idx + 1) & 0xFF  # current screen index
        p3[2] = 0x5A
        p3[3] = (dt.year % 2000) & 0xFF
        p3[4] = dt.month & 0xFF
        p3[5] = dt.day & 0xFF
        p3[6] = dt.hour & 0xFF
        p3[7] = dt.minute & 0xFF
        p3[8] = dt.second & 0xFF
        p3[10] = ((dt.weekday() + 1) % 7) & 0xFF  # 0=Sunday
        p3[62:64] = MAGIC_55AA
        self.send_command(p3)

        # Step 4: Apply
        p4 = bytearray(64)
        p4[0:2] = CMD_CONFIG_APPLY
        self.send_command(p4)

    def set_settings(self, fn_switch=0, sleep_time=5, key_respondtime=1):
        """
        Set device behavior parameters:
        fn_switch: 0 or 1
        sleep_time: 0 (No sleep), 1, 5, 30 minutes
        key_respondtime: 1 (Debounce delay)
        """
        p1 = bytearray(64)
        p1[0:2] = CMD_CONFIG_ENTER
        self.send_command(p1)

        p2 = bytearray(64)
        p2[0:2] = bytes([0x04, 0x17])
        p2[2] = 0x01
        p2[8] = 0x01
        self.send_command(p2)

        p3 = bytearray(64)
        p3[0] = 0x00
        p3[1] = 0x01
        p3[2] = 0x01 if fn_switch else 0x00
        p3[5] = fn_switch & 0xFF
        p3[6] = sleep_time & 0xFF
        p3[8] = key_respondtime & 0xFF
        p3[62:64] = MAGIC_55AA
        self.send_command(p3)

        p4 = bytearray(64)
        p4[0:2] = CMD_CONFIG_APPLY
        self.send_command(p4)

    def get_battery_status(self):
        """
        Query battery level and status.
        Returns dict with:
        - battery: percentage (0-100)
        - connected: True
        """
        p = bytearray(64)
        p[0] = 0x20
        p[1] = 0x01
        self.send_command(p, delay=0.01)

        res = self.get_feature_report()
        # Byte 0 is Report ID (0x00), Byte 1 is 0x20, Byte 3 is percentage
        percentage = res[3] if len(res) > 3 else 100
        if percentage > 100:
            percentage = 100
        return {
            "battery": percentage,
            "connected": True
        }

    def set_custom_light(self, key_rgb_map):
        """
        Set per-key RGB lighting.
        key_rgb_map: dict of {light_index (1-103): (r, g, b)}
        """
        p1 = bytearray(64)
        p1[0:2] = CMD_CONFIG_ENTER
        self.send_command(p1)

        p2 = bytearray(64)
        p2[0:2] = CMD_CUSTOM_RGB_INIT
        p2[8] = 0x09  # 9 blocks
        self.send_command(p2)

        # 576 bytes buffer (9 blocks of 64 bytes)
        buf = bytearray(576)
        for idx, (r, g, b) in key_rgb_map.items():
            if 0 <= idx < 144:
                offset = idx * 4
                buf[offset] = idx & 0xFF
                buf[offset + 1] = r & 0xFF
                buf[offset + 2] = g & 0xFF
                buf[offset + 3] = b & 0xFF

        # Send in 64-byte chunks
        for i in range(0, 576, 64):
            self.send_command(buf[i:i+64])

        p4 = bytearray(64)
        p4[0:2] = CMD_CONFIG_APPLY
        self.send_command(p4)

        p5 = bytearray(64)
        p5[0:2] = CMD_CONFIG_EXIT
        self.send_command(p5)

    def upload_tft_gif(self, image_path, progress_callback=None):
        """
        Convert GIF or static image and upload to keyboard TFT screen.
        """
        num_frames, delays, frames = load_gif_or_image(image_path)
        
        # Calculate total size
        # Header (256 bytes) + frames (30720 bytes per frame)
        header = bytearray(256)
        header[0] = num_frames & 0xFF
        for i, d in enumerate(delays[:num_frames]):
            header[1 + i] = min(max(d // 10, 1), 255)

        full_payload = bytearray(header)
        for f in frames:
            full_payload.extend(f)

        # Step 1: Config enter
        p1 = bytearray(64)
        p1[0:2] = CMD_CONFIG_ENTER
        self.send_command(p1)

        # Step 2: TFT enter
        p2 = bytearray(64)
        p2[0:2] = CMD_TFT_ENTER
        self.send_command(p2)

        # Step 3: Stream chunks of 4096 bytes
        total_chunks = (len(full_payload) + TFT_CHUNK_SIZE - 1) // TFT_CHUNK_SIZE
        for i in range(total_chunks):
            chunk = full_payload[i * TFT_CHUNK_SIZE : (i + 1) * TFT_CHUNK_SIZE]
            if len(chunk) < TFT_CHUNK_SIZE:
                chunk = chunk + bytearray(TFT_CHUNK_SIZE - len(chunk))
            
            # Send 4096 bytes in 64-byte sub-reports
            for sub_i in range(0, TFT_CHUNK_SIZE, 64):
                self.send_command(chunk[sub_i : sub_i + 64], delay=0.002)

            if progress_callback:
                progress_callback(int((i + 1) / total_chunks * 100))

        # Step 4: Apply
        p4 = bytearray(64)
        p4[0:2] = CMD_CONFIG_APPLY
        self.send_command(p4)
