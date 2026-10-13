"""
QwertyKey Rice TFT / LCD Screen Manager
Converts images and animated GIFs to RGB565 format and prepares upload payloads.
"""

import struct
from PIL import Image, ImageSequence
from .protocol import TFT_WIDTH, TFT_HEIGHT, TFT_MAX_FRAMES

def rgb_to_rgb565_le(r, g, b):
    """Convert 8-bit RGB components to 16-bit RGB565 in little endian bytes."""
    val = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return struct.pack("<H", val)

def process_image_frame(img):
    """
    Resize image to 160x96 and return raw RGB565 bytes.
    Size: 160 * 96 * 2 = 30,720 bytes.
    """
    frame = img.convert("RGB")
    if frame.size != (TFT_WIDTH, TFT_HEIGHT):
        # Resize preserving aspect ratio or fill
        frame = frame.resize((TFT_WIDTH, TFT_HEIGHT), Image.Resampling.LANCZOS)
    
    raw_bytes = bytearray()
    pixels = frame.load()
    for y in range(TFT_HEIGHT):
        for x in range(TFT_WIDTH):
            r, g, b = pixels[x, y]
            raw_bytes.extend(rgb_to_rgb565_le(r, g, b))
    return bytes(raw_bytes)

def load_gif_or_image(image_path, max_frames=TFT_MAX_FRAMES):
    """
    Load a static image or animated GIF, returning:
    - total_frames (int)
    - delays (list of int ms)
    - frames_data (list of bytes, each 30720 bytes)
    """
    img = Image.open(image_path)
    frames_data = []
    delays = []

    for frame in ImageSequence.Iterator(img):
        if len(frames_data) >= max_frames:
            break
        duration = frame.info.get("duration", 100) # default 100ms
        delays.append(duration)
        frames_data.append(process_image_frame(frame))

    if not frames_data:
        frames_data.append(process_image_frame(img))
        delays.append(100)

    return len(frames_data), delays, frames_data
