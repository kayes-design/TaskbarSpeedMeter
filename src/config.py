import os
import json
import sys
from datetime import date

CONFIG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "TaskbarSpeedMeter")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")

# Theme Presets with HEX values
THEME_PRESETS = {
    "native": {
        "name": "Windows Native (Auto)",
        "net_down": "#00E5FF",
        "net_up": "#00E676",
        "cpu": "#FF9100",
        "ram": "#E040FB",
        "disk_r": "#FFD600",
        "disk_w": "#FF5252",
        "label": "#A0A0A5",
    },
    "cyberpunk": {
        "name": "Cyberpunk Neon",
        "net_down": "#00F0FF",
        "net_up": "#39FF14",
        "cpu": "#FF007F",
        "ram": "#B026FF",
        "disk_r": "#FFE600",
        "disk_w": "#FF3333",
        "label": "#00F0FF",
    },
    "matrix": {
        "name": "Matrix Terminal",
        "net_down": "#00FF66",
        "net_up": "#99FF99",
        "cpu": "#00CC50",
        "ram": "#33FF77",
        "disk_r": "#66FF99",
        "disk_w": "#00FF44",
        "label": "#00AA40",
    },
    "ocean": {
        "name": "Ocean Breeze",
        "net_down": "#00D2FF",
        "net_up": "#4FC3F7",
        "cpu": "#00B4D8",
        "ram": "#90E0EF",
        "disk_r": "#48CAE4",
        "disk_w": "#0077B6",
        "label": "#A5D6A7",
    },
    "amber": {
        "name": "Sunset Amber",
        "net_down": "#FFB74D",
        "net_up": "#FF9800",
        "cpu": "#FF5722",
        "ram": "#FF7043",
        "disk_r": "#FFCA28",
        "disk_w": "#F4511E",
        "label": "#FFE082",
    },
    "stealth": {
        "name": "Stealth Dark",
        "net_down": "#B4B4B4",
        "net_up": "#DCDCDC",
        "cpu": "#C8C8C8",
        "ram": "#AAAAAA",
        "disk_r": "#D2D2D2",
        "disk_w": "#F0F0F0",
        "label": "#888888",
    },
    "monochrome": {
        "name": "Clean White",
        "net_down": "#FFFFFF",
        "net_up": "#E0E0E0",
        "cpu": "#FFFFFF",
        "ram": "#E0E0E0",
        "disk_r": "#FFFFFF",
        "disk_w": "#E0E0E0",
        "label": "#CCCCCC",
    }
}

DEFAULT_CONFIG = {
    # Metrics
    "show_net": True,
    "show_cpu": True,
    "show_cpu_temp": True,        # Inline CPU temperature display
    "show_gpu": False,            # Default False: Disabled when no discrete GPU
    "show_gpu_temp": False,       # GPU temperature display
    "show_ram": True,
    "show_disk": True,
    "unit_bytes": True,           # True: KB/s, MB/s; False: Kbps, Mbps
    "refresh_interval_ms": 1000,
    
    # Temperature & Alerts
    "cpu_temp_alert_threshold": 85,  # Alert threshold for CPU in °C
    "gpu_temp_alert_threshold": 80,  # Alert threshold for GPU in °C
    "enable_temp_alert_color": True, # Switch color when exceeding threshold
    "color_cpu_temp": "#FFA500",     # Normal CPU temperature color
    "color_gpu_temp": "#50FA7B",     # Normal GPU temperature color
    "color_temp_alert": "#FF3333",   # High temp alert color (Red, Black, or ANY user choice)
    
    # Position & Docking
    "dock_to_taskbar": True,
    "is_locked": False,           # When True, prevents accidental dragging
    "taskbar_offset_x": 0,        # Margin from systray (pixels)
    "floating_x": 300,
    "floating_y": 300,
    "auto_hide_sync": True,
    "click_through": False,

    # Typography & Spacing
    "font_family": "Segoe UI",
    "font_size": 9,               # Options: 8, 9, 10, 11, 12, 13, 14
    "module_padding_x": 4,        # Compact spacing between columns (adjustable in settings from 0 to 16)
    "text_shadow": False,         # Smooth anti-aliasing with no artificial drop shadow by default

    # Background Styling
    "bg_mode": "taskbar",         # "taskbar", "glass", "dark", "custom", "transparent"
    "custom_bg_hex": "#1E1E24",   # Fully custom background HEX
    "glass_opacity": 0.88,        # Translucent glass opacity (0.5 to 1.0)
    
    # Color Customization
    "theme_preset": "native",
    "use_uniform_color": False,   # Apply 1 uniform color to all metrics
    "uniform_color_hex": "#00E5FF",
    
    # Individual Metric Colors (Fully Dynamic HEX)
    "color_net_down": "#00E5FF",
    "color_net_up": "#00E676",
    "color_cpu": "#FF9100",
    "color_ram": "#E040FB",
    "color_disk_r": "#FFD600",
    "color_disk_w": "#FF5252",
    "color_label": "#A0A0A5",

    # System
    "autostart": False,

    # Data Usage History
    "today_date": str(date.today()),
    "today_down_bytes": 0,
    "today_up_bytes": 0,
    "month_str": date.today().strftime("%Y-%m"),
    "month_down_bytes": 0,
    "month_up_bytes": 0,
}

def hex_to_argb(hex_str, alpha=255):
    if not hex_str:
        return (alpha << 24) | 0xFFFFFF
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return (alpha << 24) | (r << 16) | (g << 8) | b
    elif len(hex_str) == 8:
        a = int(hex_str[0:2], 16)
        r = int(hex_str[2:4], 16)
        g = int(hex_str[4:6], 16)
        b = int(hex_str[6:8], 16)
        return (a << 24) | (r << 16) | (g << 8) | b
    return (alpha << 24) | 0xFFFFFF

def hex_to_rgb(hex_str):
    if not hex_str:
        return (255, 255, 255)
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 3:
        hex_str = ''.join([c*2 for c in hex_str])
    try:
        return (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))
    except Exception:
        return (255, 255, 255)

def rgb_to_colorref(r, g, b):
    """Win32 COLORREF is 0x00BBGGRR"""
    return (b << 16) | (g << 8) | r

def hex_to_colorref(hex_str):
    r, g, b = hex_to_rgb(hex_str)
    return rgb_to_colorref(r, g, b)

class Config:
    def __init__(self):
        self.data = dict(DEFAULT_CONFIG)
        self.last_mtime = 0
        self.load()

    def load(self):
        try:
            if os.path.exists(CONFIG_FILE):
                self.last_mtime = os.path.getmtime(CONFIG_FILE)
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self.data.update(saved)
        except Exception as e:
            print(f"[Config] Error loading: {e}", file=sys.stderr)

    def check_and_reload(self):
        try:
            if os.path.exists(CONFIG_FILE):
                mtime = os.path.getmtime(CONFIG_FILE)
                if mtime > self.last_mtime:
                    self.load()
                    return True
        except Exception:
            pass
        return False

    def save(self):
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            self.last_mtime = os.path.getmtime(CONFIG_FILE)
        except Exception as e:
            print(f"[Config] Error saving: {e}", file=sys.stderr)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def toggle(self, key):
        val = not self.data.get(key, False)
        self.data[key] = val
        self.save()
        return val

    def apply_theme_preset(self, preset_key):
        if preset_key in THEME_PRESETS:
            theme = THEME_PRESETS[preset_key]
            self.data["theme_preset"] = preset_key
            self.data["use_uniform_color"] = False
            self.data["color_net_down"] = theme["net_down"]
            self.data["color_net_up"] = theme["net_up"]
            self.data["color_cpu"] = theme["cpu"]
            self.data["color_ram"] = theme["ram"]
            self.data["color_disk_r"] = theme["disk_r"]
            self.data["color_disk_w"] = theme["disk_w"]
            self.data["color_label"] = theme["label"]
            self.save()

    def apply_uniform_color(self, hex_color):
        self.data["use_uniform_color"] = True
        self.data["uniform_color_hex"] = hex_color
        self.data["color_net_down"] = hex_color
        self.data["color_net_up"] = hex_color
        self.data["color_cpu"] = hex_color
        self.data["color_ram"] = hex_color
        self.data["color_disk_r"] = hex_color
        self.data["color_disk_w"] = hex_color
        self.data["color_label"] = hex_color
        self.save()

    def get_color(self, key):
        if self.data.get("use_uniform_color", False):
            return hex_to_colorref(self.data.get("uniform_color_hex", "#FFFFFF"))
        hex_val = self.data.get(key, "#FFFFFF")
        if isinstance(hex_val, list):
            # Backwards compatibility if old config had RGB list
            return rgb_to_colorref(*hex_val)
        return hex_to_colorref(hex_val)

    def get_argb_color(self, key, alpha=255):
        if self.data.get("use_uniform_color", False):
            return hex_to_argb(self.data.get("uniform_color_hex", "#FFFFFF"), alpha)
        hex_val = self.data.get(key, "#FFFFFF")
        if isinstance(hex_val, list):
            r, g, b = hex_val[0], hex_val[1], hex_val[2]
            return (alpha << 24) | (r << 16) | (g << 8) | b
        return hex_to_argb(hex_val, alpha)

    def add_data_usage(self, down_bytes, up_bytes):
        today = str(date.today())
        month = date.today().strftime("%Y-%m")

        if self.data.get("today_date") != today:
            self.data["today_date"] = today
            self.data["today_down_bytes"] = 0
            self.data["today_up_bytes"] = 0

        if self.data.get("month_str") != month:
            self.data["month_str"] = month
            self.data["month_down_bytes"] = 0
            self.data["month_up_bytes"] = 0

        self.data["today_down_bytes"] = self.data.get("today_down_bytes", 0) + int(down_bytes)
        self.data["today_up_bytes"] = self.data.get("today_up_bytes", 0) + int(up_bytes)
        self.data["month_down_bytes"] = self.data.get("month_down_bytes", 0) + int(down_bytes)
        self.data["month_up_bytes"] = self.data.get("month_up_bytes", 0) + int(up_bytes)

config = Config()
