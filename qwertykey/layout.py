"""
QwertyKey Rice Layout Manager
Loads keyboard geometry, key definitions, and matrix indices.
"""

import os
import xml.etree.ElementTree as ET

DEFAULT_XML_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "app", "layouts", "rgb-keyboard.xml")

class KeyInfo:
    def __init__(self, code, name, desc, key_index, light_index, row, col, x, y, width, height):
        self.code = code
        self.name = name
        self.desc = desc
        self.key_index = key_index
        self.light_index = light_index
        self.row = row
        self.col = col
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __repr__(self):
        return f"<Key {self.name} (idx={self.key_index}, light={self.light_index})>"

class KeyboardLayout:
    def __init__(self, xml_path=None):
        self.xml_path = xml_path or DEFAULT_XML_PATH
        self.keys = []
        self.key_by_index = {}
        self.key_by_light_index = {}
        self.load()

    def load(self):
        if not os.path.exists(self.xml_path):
            raise FileNotFoundError(f"Layout XML not found: {self.xml_path}")
        tree = ET.parse(self.xml_path)
        root = tree.getroot()

        kb_elem = root.find(".//Keyboard")
        self.col_count = int(kb_elem.get("col_count", 14)) if kb_elem is not None else 14
        self.row_count = int(kb_elem.get("row_count", 6)) if kb_elem is not None else 6

        for key_elem in root.findall(".//key"):
            row_col = key_elem.get("row_col", "0#0").split("#")
            row = int(row_col[0]) if len(row_col) > 0 else 0
            col = int(row_col[1]) if len(row_col) > 1 else 0

            k = KeyInfo(
                code=int(key_elem.get("code", "0"), 16),
                name=key_elem.get("name", ""),
                desc=key_elem.get("desc", ""),
                key_index=int(key_elem.get("key_index", "0")),
                light_index=int(key_elem.get("light_index", "0")),
                row=row,
                col=col,
                x=int(key_elem.get("rect_left", "0")),
                y=int(key_elem.get("rect_top", "0")),
                width=int(key_elem.get("rect_width", "40")),
                height=int(key_elem.get("rect_height", "35")),
            )
            self.keys.append(k)
            self.key_by_index[k.key_index] = k
            self.key_by_light_index[k.light_index] = k

    def get_all_keys(self):
        return self.keys
