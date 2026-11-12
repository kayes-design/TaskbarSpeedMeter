import ctypes
from ctypes import wintypes
import sys
import os
import subprocess
from win32_utils import user32, gdi32, shell32, set_autostart, is_autostart_enabled
from config import config, THEME_PRESETS
from metrics import format_bytes
from settings_dialog import open_settings_dialog
from dashboard_window import open_dashboard_window

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
MF_POPUP = 0x00000010
MF_CHECKED = 0x00000008
MF_UNCHECKED = 0x00000000

# Command IDs
CMD_DASHBOARD = 999
CMD_SETTINGS_DIALOG = 1000
CMD_TOGGLE_NET = 1001
CMD_TOGGLE_CPU = 1002
CMD_TOGGLE_RAM = 1003
CMD_TOGGLE_DISK = 1004
CMD_TOGGLE_CPU_TEMP = 1007
CMD_TOGGLE_GPU = 1008

CMD_DOCK_TASKBAR = 1005
CMD_LOCK_POSITION = 1006

CMD_UNIT_BYTES = 1010
CMD_UNIT_BITS = 1011

CMD_THEME_BASE = 1100
THEME_KEYS = list(THEME_PRESETS.keys())

CMD_BG_BASE = 1200
BG_MODES = ["taskbar", "dark", "slate", "light", "transparent"]

CMD_FSIZE_BASE = 1300
FONT_SIZES = [8, 9, 10, 11, 12]

CMD_INTERVAL_500 = 1020
CMD_INTERVAL_1000 = 1021
CMD_INTERVAL_2000 = 1022

CMD_AUTOSTART = 1030
CMD_RESET_POS = 1040
CMD_WIFI_TOOLS = 1050
CMD_EXIT = 1999

class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('hWnd', wintypes.HWND),
        ('uID', wintypes.UINT),
        ('uFlags', wintypes.UINT),
        ('uCallbackMessage', wintypes.UINT),
        ('hIcon', wintypes.HICON),
        ('szTip', wintypes.WCHAR * 128),
        ('dwState', wintypes.DWORD),
        ('dwStateMask', wintypes.DWORD),
        ('szInfo', wintypes.WCHAR * 256),
        ('uTimeout', wintypes.UINT),
        ('szInfoTitle', wintypes.WCHAR * 64),
        ('dwInfoFlags', wintypes.DWORD),
        ('guidItem', ctypes.c_byte * 16),
        ('hBalloonIcon', wintypes.HICON),
    ]

class ICONINFO(ctypes.Structure):
    _fields_ = [
        ('fIcon', wintypes.BOOL),
        ('xHotspot', wintypes.DWORD),
        ('yHotspot', wintypes.DWORD),
        ('hbmMask', wintypes.HBITMAP),
        ('hbmColor', wintypes.HBITMAP),
    ]

def create_app_icon():
    hdc = user32.GetDC(0)
    hdc_mem = gdi32.CreateCompatibleDC(hdc)
    hbm_color = gdi32.CreateCompatibleBitmap(hdc, 16, 16)
    hbm_mask = gdi32.CreateBitmap(16, 16, 1, 1, None)

    old_bm = gdi32.SelectObject(hdc_mem, hbm_color)
    
    brush = gdi32.CreateSolidBrush(0x1E1E1E)
    rect = wintypes.RECT(0, 0, 16, 16)
    user32.FillRect(hdc_mem, ctypes.byref(rect), brush)
    gdi32.DeleteObject(brush)

    b_cyan = gdi32.CreateSolidBrush(0xFFE500)
    b_green = gdi32.CreateSolidBrush(0x76E600)
    b_orange = gdi32.CreateSolidBrush(0x0091FF)

    r1 = wintypes.RECT(2, 8, 5, 14)
    r2 = wintypes.RECT(6, 4, 9, 14)
    r3 = wintypes.RECT(10, 2, 13, 14)

    user32.FillRect(hdc_mem, ctypes.byref(r1), b_cyan)
    user32.FillRect(hdc_mem, ctypes.byref(r2), b_green)
    user32.FillRect(hdc_mem, ctypes.byref(r3), b_orange)

    gdi32.DeleteObject(b_cyan)
    gdi32.DeleteObject(b_green)
    gdi32.DeleteObject(b_orange)

    gdi32.SelectObject(hdc_mem, old_bm)
    gdi32.DeleteDC(hdc_mem)
    user32.ReleaseDC(0, hdc)

    ii = ICONINFO(True, 0, 0, hbm_mask, hbm_color)
    hicon = user32.CreateIconIndirect(ctypes.byref(ii))
    gdi32.DeleteObject(hbm_color)
    gdi32.DeleteObject(hbm_mask)
    return hicon

class SystemTray:
    def __init__(self, hwnd, callback_msg):
        self.hwnd = hwnd
        self.callback_msg = callback_msg
        self.hicon = create_app_icon()
        self.nid = NOTIFYICONDATAW()
        self.nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        self.nid.hWnd = hwnd
        self.nid.uID = 101
        self.nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        self.nid.uCallbackMessage = callback_msg
        self.nid.hIcon = self.hicon
        self.nid.szTip = "Taskbar Speed & Hardware Meter"
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(self.nid))

    def update_tooltip(self, text):
        self.nid.szTip = text[:127]
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(self.nid))

    def remove(self):
        shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(self.nid))
        if self.hicon:
            user32.DestroyIcon(self.hicon)

    def show_context_menu(self, on_change_callback):
        pt = wintypes.POINT()
        user32.GetCursorPos(ctypes.byref(pt))

        hmenu = user32.CreatePopupMenu()

        def check_flag(b):
            return MF_CHECKED if b else MF_UNCHECKED

        # 1. Open Dashboard & Settings
        user32.AppendMenuW(hmenu, MF_STRING, CMD_DASHBOARD, "📊 Hardware Dashboard & Telemetry...")
        user32.AppendMenuW(hmenu, MF_STRING, CMD_SETTINGS_DIALOG, "⚙️ Settings & Customizer...")
        user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None)

        # 2. Metrics Toggles
        user32.AppendMenuW(hmenu, MF_STRING | check_flag(config.get("show_net")), CMD_TOGGLE_NET, "⚡ Network Speed (↓ / ↑)")
        user32.AppendMenuW(hmenu, MF_STRING | check_flag(config.get("show_cpu")), CMD_TOGGLE_CPU, "⚙️ CPU Usage (%)")
        user32.AppendMenuW(hmenu, MF_STRING | check_flag(config.get("show_cpu_temp")), CMD_TOGGLE_CPU_TEMP, "🌡️ CPU Temperature (°C)")
        user32.AppendMenuW(hmenu, MF_STRING | check_flag(config.get("show_gpu")), CMD_TOGGLE_GPU, "🎮 GPU Monitor (Off by default)")
        user32.AppendMenuW(hmenu, MF_STRING | check_flag(config.get("show_ram")), CMD_TOGGLE_RAM, "🧠 RAM Usage (%)")
        user32.AppendMenuW(hmenu, MF_STRING | check_flag(config.get("show_disk")), CMD_TOGGLE_DISK, "💾 Disk Activity (R / W)")

        user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None)

        # 3. Docking & Locking
        user32.AppendMenuW(hmenu, MF_STRING | check_flag(config.get("dock_to_taskbar")), CMD_DOCK_TASKBAR, "📌 Dock to Taskbar")
        user32.AppendMenuW(hmenu, MF_STRING | check_flag(config.get("is_locked")), CMD_LOCK_POSITION, "🔒 Lock Position (Prevent Dragging)")

        # 4. Themes Submenu
        hmenu_themes = user32.CreatePopupMenu()
        cur_theme = config.get("theme_preset", "native")
        for i, k in enumerate(THEME_KEYS):
            t_name = THEME_PRESETS[k]["name"]
            user32.AppendMenuW(hmenu_themes, MF_STRING | check_flag(cur_theme == k), CMD_THEME_BASE + i, t_name)
        user32.AppendMenuW(hmenu, MF_POPUP, hmenu_themes, "🎨 Color Theme")

        # 5. Background Style Submenu
        hmenu_bg = user32.CreatePopupMenu()
        cur_bg = config.get("bg_mode", "taskbar")
        bg_labels = {
            "taskbar": "Auto Match Taskbar",
            "dark": "Pure Dark (#121216)",
            "slate": "Acrylic Slate (#1E1E28)",
            "light": "Clean Soft Light",
            "transparent": "Transparent"
        }
        for i, k in enumerate(BG_MODES):
            user32.AppendMenuW(hmenu_bg, MF_STRING | check_flag(cur_bg == k), CMD_BG_BASE + i, bg_labels.get(k, k))
        user32.AppendMenuW(hmenu, MF_POPUP, hmenu_bg, "🖼️ Background Style")

        # 6. Font Size Submenu
        hmenu_fsize = user32.CreatePopupMenu()
        cur_fsize = config.get("font_size", 9)
        f_labels = {8: "8pt (Tiny)", 9: "9pt (Compact)", 10: "10pt (Normal)", 11: "11pt (Large)", 12: "12pt (Extra Large)"}
        for i, sz in enumerate(FONT_SIZES):
            user32.AppendMenuW(hmenu_fsize, MF_STRING | check_flag(cur_fsize == sz), CMD_FSIZE_BASE + i, f_labels.get(sz, f"{sz}pt"))
        user32.AppendMenuW(hmenu, MF_POPUP, hmenu_fsize, "🔤 Font Size")

        # 7. Speed Units Submenu
        hmenu_units = user32.CreatePopupMenu()
        unit_bytes = config.get("unit_bytes", True)
        user32.AppendMenuW(hmenu_units, MF_STRING | check_flag(unit_bytes), CMD_UNIT_BYTES, "Bytes (B/s, KB/s, MB/s)")
        user32.AppendMenuW(hmenu_units, MF_STRING | check_flag(not unit_bytes), CMD_UNIT_BITS, "Bits (bps, Kbps, Mbps)")
        user32.AppendMenuW(hmenu, MF_POPUP, hmenu_units, "🔄 Speed Unit")

        # 8. Refresh Rate Submenu
        hmenu_rate = user32.CreatePopupMenu()
        interval = config.get("refresh_interval_ms", 1000)
        user32.AppendMenuW(hmenu_rate, MF_STRING | check_flag(interval == 500), CMD_INTERVAL_500, "500 ms (Fast)")
        user32.AppendMenuW(hmenu_rate, MF_STRING | check_flag(interval == 1000), CMD_INTERVAL_1000, "1000 ms (Normal)")
        user32.AppendMenuW(hmenu_rate, MF_STRING | check_flag(interval == 2000), CMD_INTERVAL_2000, "2000 ms (Battery Saver)")
        user32.AppendMenuW(hmenu, MF_POPUP, hmenu_rate, "⏱️ Refresh Rate")

        user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None)

        # Autostart & Tools
        autostart = is_autostart_enabled()
        user32.AppendMenuW(hmenu, MF_STRING | check_flag(autostart), CMD_AUTOSTART, "🚀 Start with Windows")
        user32.AppendMenuW(hmenu, MF_STRING, CMD_WIFI_TOOLS, "📶 Saved Wi-Fi Passwords")

        if not config.get("dock_to_taskbar"):
            user32.AppendMenuW(hmenu, MF_STRING, CMD_RESET_POS, "📍 Reset Position")

        user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(hmenu, MF_STRING, CMD_EXIT, "❌ Exit")

        user32.SetForegroundWindow(self.hwnd)
        cmd = user32.TrackPopupMenuEx(hmenu, 0x0100 | 0x0002, pt.x, pt.y, self.hwnd, None)
        user32.DestroyMenu(hmenu)

        if cmd == 0:
            return

        need_reposition = False

        if cmd == CMD_DASHBOARD:
            open_dashboard_window()
            return
        elif cmd == CMD_SETTINGS_DIALOG:
            open_settings_dialog(on_apply_callback=lambda: on_change_callback(True))
            return
        elif cmd == CMD_TOGGLE_NET:
            config.toggle("show_net")
            need_reposition = True
        elif cmd == CMD_TOGGLE_CPU:
            config.toggle("show_cpu")
            need_reposition = True
        elif cmd == CMD_TOGGLE_CPU_TEMP:
            config.toggle("show_cpu_temp")
            need_reposition = True
        elif cmd == CMD_TOGGLE_GPU:
            config.toggle("show_gpu")
            config.toggle("show_gpu_temp")
            need_reposition = True
        elif cmd == CMD_TOGGLE_RAM:
            config.toggle("show_ram")
            need_reposition = True
        elif cmd == CMD_TOGGLE_DISK:
            config.toggle("show_disk")
            need_reposition = True
        elif cmd == CMD_DOCK_TASKBAR:
            config.toggle("dock_to_taskbar")
            need_reposition = True
        elif cmd == CMD_LOCK_POSITION:
            config.toggle("is_locked")
        elif CMD_THEME_BASE <= cmd < CMD_THEME_BASE + len(THEME_KEYS):
            idx = cmd - CMD_THEME_BASE
            config.apply_theme_preset(THEME_KEYS[idx])
        elif CMD_BG_BASE <= cmd < CMD_BG_BASE + len(BG_MODES):
            idx = cmd - CMD_BG_BASE
            config.set("bg_mode", BG_MODES[idx])
        elif CMD_FSIZE_BASE <= cmd < CMD_FSIZE_BASE + len(FONT_SIZES):
            idx = cmd - CMD_FSIZE_BASE
            config.set("font_size", FONT_SIZES[idx])
            need_reposition = True
        elif cmd == CMD_UNIT_BYTES:
            config.set("unit_bytes", True)
        elif cmd == CMD_UNIT_BITS:
            config.set("unit_bytes", False)
        elif cmd == CMD_INTERVAL_500:
            config.set("refresh_interval_ms", 500)
            user32.SetTimer(self.hwnd, 1, 500, None)
        elif cmd == CMD_INTERVAL_1000:
            config.set("refresh_interval_ms", 1000)
            user32.SetTimer(self.hwnd, 1, 1000, None)
        elif cmd == CMD_INTERVAL_2000:
            config.set("refresh_interval_ms", 2000)
            user32.SetTimer(self.hwnd, 1, 2000, None)
        elif cmd == CMD_AUTOSTART:
            new_val = not autostart
            set_autostart(new_val)
            config.set("autostart", new_val)
        elif cmd == CMD_RESET_POS:
            config.set("floating_x", 300)
            config.set("floating_y", 300)
            need_reposition = True
        elif cmd == CMD_WIFI_TOOLS:
            try:
                res = subprocess.check_output(['netsh', 'wlan', 'show', 'profiles'], text=True, errors='ignore')
                profiles = [line.split(":", 1)[1].strip() for line in res.splitlines() if "All User Profile" in line]
                msg_lines = []
                for p in profiles[:6]:
                    p_cmd = subprocess.check_output(['netsh', 'wlan', 'show', 'profile', f'name={p}', 'key=clear'], text=True, errors='ignore')
                    pwd = "Open / No Pass"
                    for pline in p_cmd.splitlines():
                        if "Key Content" in pline:
                            pwd = pline.split(":", 1)[1].strip()
                            break
                    msg_lines.append(f"• {p}:  {pwd}")
                user32.MessageBoxW(0, "\n".join(msg_lines) if msg_lines else "No Wi-Fi profiles found.", "Saved Wi-Fi Passwords", 0x40 | 0x10000)
            except Exception as e:
                user32.MessageBoxW(0, f"Error: {e}", "Wi-Fi Tool", 0x10 | 0x10000)
        elif cmd == CMD_EXIT:
            user32.PostMessageW(self.hwnd, 0x0010, 0, 0)
            return

        if on_change_callback:
            on_change_callback(need_reposition)
