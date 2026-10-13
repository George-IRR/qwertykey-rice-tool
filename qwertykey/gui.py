"""
QwertyKey Rice Linux GUI
Full-featured desktop application for RGB lighting, LCD Screen synchronization,
TFT animations, custom per-key lighting, and keyboard settings.
"""

import sys
import os
import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QLabel, QPushButton, QComboBox, QSlider, QSpinBox,
    QColorDialog, QFileDialog, QProgressBar, QGroupBox, QGridLayout,
    QFrame, QMessageBox, QCheckBox, QStatusBar
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QBrush, QPen, QMovie, QPixmap

from .device import QwertyKeyDevice
from .protocol import LIGHT_MODES, SLEEP_TIMES, TFT_WIDTH, TFT_HEIGHT
from .layout import KeyboardLayout


class TFTUploadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)

    def __init__(self, dev, file_path):
        super().__init__()
        self.dev = dev
        self.file_path = file_path

    def run(self):
        try:
            self.dev.upload_tft_gif(self.file_path, progress_callback=self.progress.emit)
            self.finished.emit(True, "TFT display updated successfully!")
        except Exception as e:
            self.finished.emit(False, str(e))


class KeyButton(QPushButton):
    def __init__(self, key_info, parent=None):
        super().__init__(parent)
        self.key_info = key_info
        self.rgb = (40, 40, 40)
        self.selected = False
        self.setText(key_info.name)
        self.update_style()

    def set_color(self, r, g, b):
        self.rgb = (r, g, b)
        self.update_style()

    def set_selected(self, selected):
        self.selected = selected
        self.update_style()

    def update_style(self):
        r, g, b = self.rgb
        border = "2px solid #00E5FF" if self.selected else "1px solid #333333"
        text_color = "#FFFFFF" if (r*0.299 + g*0.587 + b*0.114) < 150 else "#000000"
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({r}, {g}, {b});
                color: {text_color};
                border: {border};
                border-radius: 4px;
                font-family: monospace;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                border: 2px solid #FFFFFF;
            }}
        """)


class VisualKeyboard(QFrame):
    keyClicked = pyqtSignal(object)

    def __init__(self, layout=None, parent=None):
        super().__init__(parent)
        self.layout_data = layout or KeyboardLayout()
        self.key_buttons = {}
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: #121214; border: 2px solid #28282D; border-radius: 8px;")
        # Set fixed size based on key coordinates
        # Bounding box is 762 x 241, with padding ~800 x 280
        self.setFixedSize(800, 275)

        for k in self.layout_data.keys:
            btn = KeyButton(k, self)
            # Offset x by -10, y by -10
            btn.setGeometry(k.x - 10, k.y - 10, k.width, k.height)
            btn.clicked.connect(lambda checked, b=btn: self.on_key_clicked(b))
            self.key_buttons[k.light_index] = btn

    def on_key_clicked(self, btn):
        self.keyClicked.emit(btn)

    def set_all_colors(self, r, g, b):
        for btn in self.key_buttons.values():
            btn.set_color(r, g, b)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QwertyKey Rice 60% - Linux Control Center")
        self.resize(880, 720)
        self.setMinimumSize(850, 680)

        self.dev = None
        self.selected_color = QColor(255, 0, 0)
        self.custom_key_colors = {}
        self.selected_key_btn = None

        self.init_device()
        self.init_ui()
        self.apply_dark_theme()

        # Periodic battery and clock refresh
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_status_bar)
        self.status_timer.start(10000)
        self.update_status_bar()

    def init_device(self):
        try:
            self.dev = QwertyKeyDevice()
            self.dev.open()
        except Exception as e:
            self.dev = None
            print(f"Device connection warning: {e}")

    def closeEvent(self, event):
        if self.dev:
            try:
                self.dev.close()
            except Exception:
                pass
        event.accept()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # Header Info Bar
        header = QHBoxLayout()
        title = QLabel("⌨ QWERTYKEY RICE 60%")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setStyleSheet("color: #00E5FF;")
        header.addWidget(title)

        header.addStretch()

        self.lbl_connection = QLabel("Status: Detecting...")
        self.lbl_connection.setStyleSheet("color: #AAAAAA; font-weight: bold;")
        header.addWidget(self.lbl_connection)

        self.lbl_battery = QLabel("Battery: --%")
        self.lbl_battery.setStyleSheet("color: #00FF66; font-weight: bold; margin-left: 15px;")
        header.addWidget(self.lbl_battery)

        main_layout.addLayout(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_lighting_tab(), "Backlight RGB")
        self.tabs.addTab(self.create_custom_rgb_tab(), "Per-Key Custom RGB")
        self.tabs.addTab(self.create_tft_tab(), "TFT Screen & GIF")
        self.tabs.addTab(self.create_settings_tab(), "Keyboard Settings")
        main_layout.addWidget(self.tabs)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready.")

    def create_lighting_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # Visual Keyboard Preview
        self.preview_kb = VisualKeyboard()
        kb_container = QHBoxLayout()
        kb_container.addStretch()
        kb_container.addWidget(self.preview_kb)
        kb_container.addStretch()
        layout.addLayout(kb_container)

        # Lighting Controls Group
        grp = QGroupBox("Lighting Parameters")
        grp_layout = QGridLayout(grp)
        grp_layout.setSpacing(10)

        # Effect selector
        grp_layout.addWidget(QLabel("Effect Mode:"), 0, 0)
        self.combo_modes = QComboBox()
        for mid, info in sorted(LIGHT_MODES.items()):
            self.combo_modes.addItem(f"{mid:02d}: {info['name']}", mid)
        self.combo_modes.setCurrentIndex(11) # Rolling
        self.combo_modes.currentIndexChanged.connect(self.on_light_param_changed)
        grp_layout.addWidget(self.combo_modes, 0, 1)

        # Rainbow / Palette
        self.chk_rainbow = QCheckBox("Rainbow / Multi-Color")
        self.chk_rainbow.setChecked(True)
        self.chk_rainbow.stateChanged.connect(self.on_light_param_changed)
        grp_layout.addWidget(self.chk_rainbow, 0, 2)

        # Color picker
        grp_layout.addWidget(QLabel("Static Color:"), 1, 0)
        self.btn_color_pick = QPushButton()
        self.btn_color_pick.setFixedSize(60, 26)
        self.btn_color_pick.clicked.connect(self.choose_static_color)
        self.update_color_button()
        grp_layout.addWidget(self.btn_color_pick, 1, 1)

        # Brightness Slider
        grp_layout.addWidget(QLabel("Brightness:"), 2, 0)
        self.slider_brightness = QSlider(Qt.Horizontal)
        self.slider_brightness.setRange(0, 5)
        self.slider_brightness.setValue(5)
        self.lbl_brightness_val = QLabel("5")
        self.slider_brightness.valueChanged.connect(lambda v: (self.lbl_brightness_val.setText(str(v)), self.on_light_param_changed()))
        b_box = QHBoxLayout()
        b_box.addWidget(self.slider_brightness)
        b_box.addWidget(self.lbl_brightness_val)
        grp_layout.addLayout(b_box, 2, 1)

        # Speed Slider
        grp_layout.addWidget(QLabel("Speed:"), 3, 0)
        self.slider_speed = QSlider(Qt.Horizontal)
        self.slider_speed.setRange(1, 5)
        self.slider_speed.setValue(3)
        self.lbl_speed_val = QLabel("3")
        self.slider_speed.valueChanged.connect(lambda v: (self.lbl_speed_val.setText(str(v)), self.on_light_param_changed()))
        s_box = QHBoxLayout()
        s_box.addWidget(self.slider_speed)
        s_box.addWidget(self.lbl_speed_val)
        grp_layout.addLayout(s_box, 3, 1)

        # Direction
        grp_layout.addWidget(QLabel("Direction:"), 4, 0)
        self.combo_dir = QComboBox()
        self.combo_dir.addItem("Left / Top", 1)
        self.combo_dir.addItem("Right / Bottom", 2)
        self.combo_dir.currentIndexChanged.connect(self.on_light_param_changed)
        grp_layout.addWidget(self.combo_dir, 4, 1)

        layout.addWidget(grp)

        # Apply Button
        btn_apply = QPushButton("Apply Lighting to Keyboard")
        btn_apply.setFixedHeight(38)
        btn_apply.setStyleSheet("background-color: #00E5FF; color: #000000; font-weight: bold; font-size: 13px;")
        btn_apply.clicked.connect(self.apply_lighting)
        layout.addWidget(btn_apply)

        layout.addStretch()
        return tab

    def create_custom_rgb_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        info_lbl = QLabel("Click individual keys on the layout below to assign custom RGB colors:")
        info_lbl.setStyleSheet("color: #AAAAAA;")
        layout.addWidget(info_lbl)

        # Interactive Keyboard Canvas
        self.custom_kb = VisualKeyboard()
        self.custom_kb.keyClicked.connect(self.on_custom_key_clicked)
        kb_container = QHBoxLayout()
        kb_container.addStretch()
        kb_container.addWidget(self.custom_kb)
        kb_container.addStretch()
        layout.addLayout(kb_container)

        # Controls bar
        ctrl_box = QHBoxLayout()
        
        self.lbl_selected_key = QLabel("Selected Key: None")
        self.lbl_selected_key.setFont(QFont("Arial", 11, QFont.Bold))
        ctrl_box.addWidget(self.lbl_selected_key)

        ctrl_box.addSpacing(20)
        ctrl_box.addWidget(QLabel("Pick Key Color:"))
        self.btn_custom_color = QPushButton()
        self.btn_custom_color.setFixedSize(50, 26)
        self.btn_custom_color.setStyleSheet(f"background-color: {self.selected_color.name()}; border-radius: 4px;")
        self.btn_custom_color.clicked.connect(self.choose_custom_color)
        ctrl_box.addWidget(self.btn_custom_color)

        btn_fill_all = QPushButton("Fill All Keys")
        btn_fill_all.clicked.connect(self.fill_all_keys)
        ctrl_box.addWidget(btn_fill_all)

        btn_clear_all = QPushButton("Reset All to Off")
        btn_clear_all.clicked.connect(self.clear_all_keys)
        ctrl_box.addWidget(btn_clear_all)

        ctrl_box.addStretch()
        layout.addLayout(ctrl_box)

        # Apply Custom Button
        btn_apply = QPushButton("Upload Custom RGB Layout")
        btn_apply.setFixedHeight(38)
        btn_apply.setStyleSheet("background-color: #00E5FF; color: #000000; font-weight: bold; font-size: 13px;")
        btn_apply.clicked.connect(self.apply_custom_rgb)
        layout.addWidget(btn_apply)

        layout.addStretch()
        return tab

    def create_tft_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        # Screen Clock Sync Box
        clock_grp = QGroupBox("LCD Clock & Time Synchronization")
        clock_layout = QHBoxLayout(clock_grp)
        self.lbl_sys_time = QLabel()
        self.lbl_sys_time.setStyleSheet("font-size: 13px; font-weight: bold; color: #00E5FF;")
        self.time_update_timer = QTimer(self)
        self.time_update_timer.timeout.connect(lambda: self.lbl_sys_time.setText(f"System Clock: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
        self.time_update_timer.start(1000)
        self.lbl_sys_time.setText(f"System Clock: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        clock_layout.addWidget(self.lbl_sys_time)

        clock_layout.addStretch()

        btn_sync_now = QPushButton("Sync Clock to LCD")
        btn_sync_now.setFixedHeight(32)
        btn_sync_now.clicked.connect(self.sync_clock)
        clock_layout.addWidget(btn_sync_now)

        layout.addWidget(clock_grp)

        # GIF / Image Upload Box
        tft_grp = QGroupBox("TFT Display Custom GIF / Image (160x96)")
        tft_layout = QVBoxLayout(tft_grp)
        tft_layout.setSpacing(10)

        file_box = QHBoxLayout()
        self.lbl_file = QLabel("No file selected")
        self.lbl_file.setStyleSheet("color: #888888;")
        btn_browse = QPushButton("Select GIF / Image...")
        btn_browse.clicked.connect(self.browse_tft_file)
        file_box.addWidget(btn_browse)
        file_box.addWidget(self.lbl_file)
        file_box.addStretch()
        tft_layout.addLayout(file_box)

        # Animated Preview
        prev_box = QHBoxLayout()
        self.lbl_tft_preview = QLabel("Preview Area\n(160x96)")
        self.lbl_tft_preview.setFixedSize(160, 96)
        self.lbl_tft_preview.setAlignment(Qt.AlignCenter)
        self.lbl_tft_preview.setStyleSheet("border: 2px dashed #444444; background-color: #000000; color: #666666;")
        prev_box.addStretch()
        prev_box.addWidget(self.lbl_tft_preview)
        prev_box.addStretch()
        tft_layout.addLayout(prev_box)

        # Progress bar
        self.prog_tft = QProgressBar()
        self.prog_tft.setValue(0)
        self.prog_tft.setTextVisible(True)
        tft_layout.addWidget(self.prog_tft)

        # Upload Button
        self.btn_upload_tft = QPushButton("Upload Animation to LCD Screen")
        self.btn_upload_tft.setFixedHeight(38)
        self.btn_upload_tft.setStyleSheet("background-color: #00E5FF; color: #000000; font-weight: bold;")
        self.btn_upload_tft.clicked.connect(self.upload_tft_animation)
        tft_layout.addWidget(self.btn_upload_tft)

        layout.addWidget(tft_grp)
        layout.addStretch()
        return tab

    def create_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)

        grp = QGroupBox("Device Behavior & Power")
        g_layout = QGridLayout(grp)
        g_layout.setSpacing(12)

        # Sleep Time
        g_layout.addWidget(QLabel("Sleep Timer:"), 0, 0)
        self.combo_sleep = QComboBox()
        self.combo_sleep.addItem("Disabled (No Sleep)", 0)
        self.combo_sleep.addItem("1 Minute", 1)
        self.combo_sleep.addItem("5 Minutes (Default)", 5)
        self.combo_sleep.addItem("30 Minutes", 30)
        self.combo_sleep.setCurrentIndex(2)
        g_layout.addWidget(self.combo_sleep, 0, 1)

        # Debounce Delay
        g_layout.addWidget(QLabel("Debounce Delay (ms):"), 1, 0)
        self.spin_debounce = QSpinBox()
        self.spin_debounce.setRange(1, 10)
        self.spin_debounce.setValue(1)
        g_layout.addWidget(self.spin_debounce, 1, 1)

        layout.addWidget(grp)

        # Side lights box
        side_grp = QGroupBox("Side Light Bar")
        s_layout = QGridLayout(side_grp)
        
        s_layout.addWidget(QLabel("Side Light Mode:"), 0, 0)
        self.combo_side_mode = QComboBox()
        self.combo_side_mode.addItem("Off", 0)
        self.combo_side_mode.addItem("Static", 1)
        self.combo_side_mode.addItem("Breath", 2)
        self.combo_side_mode.addItem("Rainbow", 3)
        self.combo_side_mode.setCurrentIndex(1)
        s_layout.addWidget(self.combo_side_mode, 0, 1)

        btn_apply_side = QPushButton("Apply Side Light")
        btn_apply_side.clicked.connect(self.apply_side_light)
        s_layout.addWidget(btn_apply_side, 1, 1)
        layout.addWidget(side_grp)

        # Save Settings Button
        btn_save = QPushButton("Save Settings to Device")
        btn_save.setFixedHeight(38)
        btn_save.setStyleSheet("background-color: #00E5FF; color: #000000; font-weight: bold;")
        btn_save.clicked.connect(self.apply_settings)
        layout.addWidget(btn_save)

        layout.addStretch()
        return tab

    # ---- Logic & Actions ----

    def update_status_bar(self):
        if not self.dev or not os.path.exists(self.dev.hidraw_path):
            self.lbl_connection.setText("Status: Disconnected")
            self.lbl_connection.setStyleSheet("color: #FF4444; font-weight: bold;")
            self.lbl_battery.setText("Battery: --%")
            return

        try:
            st = self.dev.get_battery_status()
            batt = st.get("battery", 0)
            batt_str = f"{batt}%" if batt > 0 else "Wired Mode"
            self.lbl_battery.setText(f"Battery: {batt_str}")
            self.lbl_connection.setText("Status: Connected (/dev/hidraw)")
            self.lbl_connection.setStyleSheet("color: #00FF66; font-weight: bold;")
        except Exception:
            self.lbl_connection.setText("Status: Device Busy")

    def update_color_button(self):
        self.btn_color_pick.setStyleSheet(f"background-color: {self.selected_color.name()}; border: 1px solid #FFFFFF; border-radius: 4px;")

    def choose_static_color(self):
        c = QColorDialog.getColor(self.selected_color, self, "Select RGB Color")
        if c.isValid():
            self.selected_color = c
            self.update_color_button()
            self.on_light_param_changed()

    def on_light_param_changed(self):
        # Update preview keyboard
        if self.chk_rainbow.isChecked():
            # Rainbow preview mock
            colors = [
                (255, 0, 0), (255, 127, 0), (255, 255, 0),
                (0, 255, 0), (0, 0, 255), (139, 0, 255)
            ]
            for idx, btn in self.preview_kb.key_buttons.items():
                col = colors[idx % len(colors)]
                btn.set_color(*col)
        else:
            r, g, b = self.selected_color.red(), self.selected_color.green(), self.selected_color.blue()
            self.preview_kb.set_all_colors(r, g, b)

    def apply_lighting(self):
        if not self.dev:
            QMessageBox.critical(self, "Error", "Device not connected!")
            return
        mode_idx = self.combo_modes.currentData()
        r = self.selected_color.red()
        g = self.selected_color.green()
        b = self.selected_color.blue()
        bright = self.slider_brightness.value()
        spd = self.slider_speed.value()
        direct = self.combo_dir.currentData()
        rainbow = 1 if self.chk_rainbow.isChecked() else 0

        try:
            self.dev.set_lighting(
                mode=mode_idx,
                r=r, g=g, b=b,
                brightness=bright,
                speed=spd,
                direction=direct,
                colorful=rainbow
            )
            self.status_bar.showMessage(f"Applied lighting mode {self.combo_modes.currentText()}.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply lighting: {e}")

    def on_custom_key_clicked(self, btn):
        if self.selected_key_btn:
            self.selected_key_btn.set_selected(False)
        self.selected_key_btn = btn
        btn.set_selected(True)
        self.lbl_selected_key.setText(f"Selected Key: {btn.key_info.name} (Idx: {btn.key_info.light_index})")
        # Apply currently active color
        r, g, b = self.selected_color.red(), self.selected_color.green(), self.selected_color.blue()
        btn.set_color(r, g, b)
        self.custom_key_colors[btn.key_info.light_index] = (r, g, b)

    def choose_custom_color(self):
        c = QColorDialog.getColor(self.selected_color, self, "Select Key Color")
        if c.isValid():
            self.selected_color = c
            self.btn_custom_color.setStyleSheet(f"background-color: {c.name()}; border-radius: 4px;")
            if self.selected_key_btn:
                self.on_custom_key_clicked(self.selected_key_btn)

    def fill_all_keys(self):
        r, g, b = self.selected_color.red(), self.selected_color.green(), self.selected_color.blue()
        for idx, btn in self.custom_kb.key_buttons.items():
            btn.set_color(r, g, b)
            self.custom_key_colors[idx] = (r, g, b)

    def clear_all_keys(self):
        for idx, btn in self.custom_kb.key_buttons.items():
            btn.set_color(15, 15, 15)
            self.custom_key_colors[idx] = (0, 0, 0)

    def apply_custom_rgb(self):
        if not self.dev:
            QMessageBox.critical(self, "Error", "Device not connected!")
            return
        try:
            self.dev.set_custom_light(self.custom_key_colors)
            self.status_bar.showMessage("Uploaded custom per-key lighting.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to upload custom RGB: {e}")

    def sync_clock(self):
        if not self.dev:
            QMessageBox.critical(self, "Error", "Device not connected!")
            return
        try:
            now = datetime.datetime.now()
            self.dev.sync_time(now)
            self.status_bar.showMessage("LCD clock synchronized with system time.", 3000)
            QMessageBox.information(self, "Success", "LCD clock synchronized successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to sync time: {e}")

    def browse_tft_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Image or GIF", "", "Image Files (*.gif *.png *.jpg *.jpeg *.bmp)")
        if path:
            self.tft_file_path = path
            self.lbl_file.setText(os.path.basename(path))
            # Load animated preview or pixmap
            if path.lower().endswith(".gif"):
                movie = QMovie(path)
                movie.setScaledSize(self.lbl_tft_preview.size())
                self.lbl_tft_preview.setMovie(movie)
                movie.start()
            else:
                pix = QPixmap(path).scaled(160, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.lbl_tft_preview.setPixmap(pix)

    def upload_tft_animation(self):
        if not hasattr(self, "tft_file_path") or not self.tft_file_path:
            QMessageBox.warning(self, "Warning", "Please select a GIF or image file first.")
            return
        if not self.dev:
            QMessageBox.critical(self, "Error", "Device not connected!")
            return

        self.btn_upload_tft.setEnabled(False)
        self.prog_tft.setValue(0)
        self.status_bar.showMessage("Uploading animation to LCD screen...")

        self.upload_thread = TFTUploadThread(self.dev, self.tft_file_path)
        self.upload_thread.progress.connect(self.prog_tft.setValue)
        self.upload_thread.finished.connect(self.on_tft_finished)
        self.upload_thread.start()

    def on_tft_finished(self, success, msg):
        self.btn_upload_tft.setEnabled(True)
        if success:
            self.status_bar.showMessage(msg, 4000)
            QMessageBox.information(self, "Success", msg)
        else:
            self.status_bar.showMessage("TFT Upload failed.", 4000)
            QMessageBox.critical(self, "Upload Failed", msg)

    def apply_settings(self):
        if not self.dev:
            QMessageBox.critical(self, "Error", "Device not connected!")
            return
        sleep_val = self.combo_sleep.currentData()
        debounce_val = self.spin_debounce.value()
        try:
            self.dev.set_settings(sleep_time=sleep_val, key_respondtime=debounce_val)
            self.status_bar.showMessage("Saved keyboard settings successfully.", 3000)
            QMessageBox.information(self, "Saved", "Keyboard settings applied successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")

    def apply_side_light(self):
        if not self.dev:
            QMessageBox.critical(self, "Error", "Device not connected!")
            return
        mode = self.combo_side_mode.currentData()
        try:
            self.dev.set_side_light(mode=mode, r=self.selected_color.red(), g=self.selected_color.green(), b=self.selected_color.blue())
            self.status_bar.showMessage("Applied side light settings.", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply side light: {e}")

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #18181B;
            }
            QWidget {
                color: #EEEEEE;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #27272A;
                background-color: #1E1E24;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #141417;
                color: #A1A1AA;
                padding: 10px 18px;
                margin-right: 4px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #1E1E24;
                color: #00E5FF;
                border-bottom: 2px solid #00E5FF;
            }
            QGroupBox {
                border: 1px solid #3F3F46;
                border-radius: 6px;
                margin-top: 14px;
                padding-top: 16px;
                font-weight: bold;
                color: #E4E4E7;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #27272A;
                color: #FFFFFF;
                border: 1px solid #3F3F46;
                border-radius: 5px;
                padding: 6px 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3F3F46;
                border-color: #71717A;
            }
            QComboBox, QSpinBox {
                background-color: #27272A;
                color: #FFFFFF;
                border: 1px solid #3F3F46;
                border-radius: 4px;
                padding: 5px 8px;
            }
            QProgressBar {
                border: 1px solid #3F3F46;
                border-radius: 4px;
                text-align: center;
                background-color: #141417;
                color: #FFFFFF;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #00E5FF;
                border-radius: 3px;
            }
            QStatusBar {
                background-color: #141417;
                color: #A1A1AA;
            }
        """)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
