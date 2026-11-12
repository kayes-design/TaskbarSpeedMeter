import ctypes
from ctypes import wintypes
import time
from config import config, hex_to_argb, hex_to_rgb
from metrics import SystemMetrics, format_speed
from win32_utils import (
    user32, gdi32, kernel32,
    WS_POPUP, WS_VISIBLE, WS_CLIPSIBLINGS,
    WS_EX_TOOLWINDOW, WS_EX_TOPMOST, WS_EX_NOACTIVATE, WS_EX_LAYERED,
    SW_HIDE, SW_SHOWNOACTIVATE,
    HWND_TOPMOST, WM_DESTROY, WM_CLOSE, WM_TIMER,
    WM_LBUTTONDOWN, WM_LBUTTONUP, WM_RBUTTONUP, WM_MOUSEMOVE,
    WM_TRAYICON, get_taskbar_info, get_background_colors,
    ensure_interactive_desktop
)
from tray import SystemTray
from dashboard_window import open_dashboard_window

gp = ctypes.windll.gdiplus

# --- GDI+ Structures & Prototypes ---
class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ('BlendOp', wintypes.BYTE),
        ('BlendFlags', wintypes.BYTE),
        ('SourceConstantAlpha', wintypes.BYTE),
        ('AlphaFormat', wintypes.BYTE),
    ]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', ctypes.c_long),
        ('biHeight', ctypes.c_long),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', ctypes.c_long),
        ('biYPelsPerMeter', ctypes.c_long),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', wintypes.DWORD * 3)]

class GdiplusStartupInput(ctypes.Structure):
    _fields_ = [
        ('GdiplusVersion', wintypes.UINT),
        ('DebugEventCallback', ctypes.c_void_p),
        ('SuppressBackgroundThread', wintypes.BOOL),
        ('SuppressExternalCodecs', wintypes.BOOL)
    ]

class RectF(ctypes.Structure):
    _fields_ = [
        ('x', ctypes.c_float),
        ('y', ctypes.c_float),
        ('width', ctypes.c_float),
        ('height', ctypes.c_float)
    ]

# GDI+ Function Bindings
gp.GdiplusStartup.argtypes = [ctypes.POINTER(ctypes.c_ulong), ctypes.c_void_p, ctypes.c_void_p]
gp.GdiplusStartup.restype = ctypes.c_int
gp.GdiplusShutdown.argtypes = [ctypes.c_ulong]
gp.GdiplusShutdown.restype = None

gp.GdipCreateFromHDC.argtypes = [wintypes.HDC, ctypes.POINTER(ctypes.c_void_p)]
gp.GdipCreateFromHDC.restype = ctypes.c_int
gp.GdipDeleteGraphics.argtypes = [ctypes.c_void_p]
gp.GdipDeleteGraphics.restype = ctypes.c_int

gp.GdipSetTextRenderingHint.argtypes = [ctypes.c_void_p, ctypes.c_int]
gp.GdipSetTextRenderingHint.restype = ctypes.c_int
gp.GdipSetSmoothingMode.argtypes = [ctypes.c_void_p, ctypes.c_int]
gp.GdipSetSmoothingMode.restype = ctypes.c_int

gp.GdipCreateFontFamilyFromName.argtypes = [wintypes.LPCWSTR, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
gp.GdipCreateFontFamilyFromName.restype = ctypes.c_int
gp.GdipDeleteFontFamily.argtypes = [ctypes.c_void_p]
gp.GdipDeleteFontFamily.restype = ctypes.c_int

gp.GdipCreateFont.argtypes = [ctypes.c_void_p, ctypes.c_float, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
gp.GdipCreateFont.restype = ctypes.c_int
gp.GdipDeleteFont.argtypes = [ctypes.c_void_p]
gp.GdipDeleteFont.restype = ctypes.c_int

gp.GdipCreateStringFormat.argtypes = [ctypes.c_int, wintypes.LANGID, ctypes.POINTER(ctypes.c_void_p)]
gp.GdipCreateStringFormat.restype = ctypes.c_int
gp.GdipDeleteStringFormat.argtypes = [ctypes.c_void_p]
gp.GdipDeleteStringFormat.restype = ctypes.c_int

gp.GdipSetStringFormatAlign.argtypes = [ctypes.c_void_p, ctypes.c_int]
gp.GdipSetStringFormatAlign.restype = ctypes.c_int
gp.GdipSetStringFormatLineAlign.argtypes = [ctypes.c_void_p, ctypes.c_int]
gp.GdipSetStringFormatLineAlign.restype = ctypes.c_int

gp.GdipMeasureString.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(RectF), ctypes.c_void_p, ctypes.POINTER(RectF), ctypes.c_void_p, ctypes.c_void_p]
gp.GdipMeasureString.restype = ctypes.c_int

gp.GdipCreateSolidFill.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_void_p)]
gp.GdipCreateSolidFill.restype = ctypes.c_int
gp.GdipDeleteBrush.argtypes = [ctypes.c_void_p]
gp.GdipDeleteBrush.restype = ctypes.c_int

gp.GdipDrawString.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(RectF), ctypes.c_void_p, ctypes.c_void_p]
gp.GdipDrawString.restype = ctypes.c_int

gp.GdipCreatePen1.argtypes = [ctypes.c_uint32, ctypes.c_float, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)]
gp.GdipCreatePen1.restype = ctypes.c_int
gp.GdipDeletePen.argtypes = [ctypes.c_void_p]
gp.GdipDeletePen.restype = ctypes.c_int

gp.GdipDrawLine.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float]
gp.GdipDrawLine.restype = ctypes.c_int

gp.GdipDrawRectangle.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float]
gp.GdipDrawRectangle.restype = ctypes.c_int

WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_int64, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.UINT),
        ('style', wintypes.UINT),
        ('lpfnWndProc', WNDPROC),
        ('cbClsExtra', ctypes.c_int),
        ('cbWndExtra', ctypes.c_int),
        ('hInstance', wintypes.HINSTANCE),
        ('hIcon', wintypes.HICON),
        ('hCursor', wintypes.HICON),
        ('hbrBackground', wintypes.HBRUSH),
        ('lpszMenuName', wintypes.LPCWSTR),
        ('lpszClassName', wintypes.LPCWSTR),
        ('hIconSm', wintypes.HICON)
    ]

class SpeedMeterWindow:
    def __init__(self):
        # 1. GDI+ Startup
        self.gp_token = ctypes.c_ulong()
        si = GdiplusStartupInput(1, None, False, False)
        gp.GdiplusStartup(ctypes.byref(self.gp_token), ctypes.byref(si), None)

        self.hwnd = None
        self.metrics = SystemMetrics()
        self.tray = None
        self.is_dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.is_hidden_by_taskbar = False
        self.last_click_time = 0

        # Memory Surface Handles
        self.hdc_screen = user32.GetDC(0)
        self.hdc_mem = gdi32.CreateCompatibleDC(self.hdc_screen)
        self.hbm = None
        self.p_bits = None
        self.surface_w = 0
        self.surface_h = 0

        # GDI+ Font Handles
        self.gp_font_family = None
        self.gp_font_main = None
        self.gp_font_small = None
        self.gp_font_label = None
        self.str_format_center = None

        # Dimensions & Coordinates
        self.width = 240
        self.height = 36
        self.current_x = config.get("floating_x", 300)
        self.current_y = config.get("floating_y", 300)

        self.col_w_net = 60.0
        self.col_w_cpu = 40.0
        self.col_w_gpu = 40.0
        self.col_w_ram = 36.0
        self.col_w_disk = 60.0

        # Initialize Window & Surface
        self._init_window()
        self.tray = SystemTray(self.hwnd, WM_TRAYICON)
        self.recalculate_dimensions()
        self.reposition_window()

        # Start 1s Metrics Timer
        interval = config.get("refresh_interval_ms", 1000)
        user32.SetTimer(self.hwnd, 1, interval, None)

    def _init_window(self):
        ensure_interactive_desktop()
        self.wnd_proc = WNDPROC(self._window_procedure)
        class_name = "TaskbarSpeedMeterClass"

        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.style = 3
        wc.lpfnWndProc = self.wnd_proc
        wc.hInstance = kernel32.GetModuleHandleW(None)
        wc.hCursor = user32.LoadCursorW(None, 32512)
        wc.lpszClassName = class_name
        user32.RegisterClassExW(ctypes.byref(wc))

        ex_style = WS_EX_TOOLWINDOW | WS_EX_TOPMOST | WS_EX_NOACTIVATE | WS_EX_LAYERED
        style = WS_POPUP | WS_VISIBLE | WS_CLIPSIBLINGS

        self.hwnd = user32.CreateWindowExW(
            ex_style,
            class_name,
            "TaskbarSpeedMeter",
            style,
            self.current_x,
            self.current_y,
            self.width,
            self.height,
            None,
            None,
            wc.hInstance,
            None
        )

    def _init_fonts(self):
        if self.gp_font_main:
            gp.GdipDeleteFont(self.gp_font_main)
            self.gp_font_main = None
        if self.gp_font_small:
            gp.GdipDeleteFont(self.gp_font_small)
            self.gp_font_small = None
        if self.gp_font_label:
            gp.GdipDeleteFont(self.gp_font_label)
            self.gp_font_label = None
        if self.gp_font_family:
            gp.GdipDeleteFontFamily(self.gp_font_family)
            self.gp_font_family = None
        if self.str_format_center:
            gp.GdipDeleteStringFormat(self.str_format_center)
            self.str_format_center = None

        font_name = config.get("font_family", "Segoe UI")
        base_size = float(config.get("font_size", 9))

        self.gp_font_family = ctypes.c_void_p()
        gp.GdipCreateFontFamilyFromName(font_name, None, ctypes.byref(self.gp_font_family))

        # Original Font Sizing Restored (CPU % & RAM % at large scale!)
        sz_main = max(8.5, base_size * 1.05)   # Original large size for CPU % and RAM %
        sz_small = max(7.5, base_size * 0.95)  # Original size for Net & Disk
        sz_label = max(7.0, base_size * 0.90)  # Original size for labels

        self.gp_font_main = ctypes.c_void_p()
        self.gp_font_small = ctypes.c_void_p()
        self.gp_font_label = ctypes.c_void_p()

        # Style Bold = 1, UnitPoint = 2
        gp.GdipCreateFont(self.gp_font_family, ctypes.c_float(sz_main), 1, 2, ctypes.byref(self.gp_font_main))
        gp.GdipCreateFont(self.gp_font_family, ctypes.c_float(sz_small), 1, 2, ctypes.byref(self.gp_font_small))
        gp.GdipCreateFont(self.gp_font_family, ctypes.c_float(sz_label), 1, 2, ctypes.byref(self.gp_font_label))

        self.str_format_center = ctypes.c_void_p()
        gp.GdipCreateStringFormat(0, 0, ctypes.byref(self.str_format_center))
        gp.GdipSetStringFormatAlign(self.str_format_center, 1)     # Center horizontally
        gp.GdipSetStringFormatLineAlign(self.str_format_center, 1) # Center vertically

    def measure_text_gp(self, graphics, text, font):
        rf = RectF(0, 0, 1000.0, 100.0)
        bbox = RectF()
        gp.GdipMeasureString(graphics, text, len(text), font, ctypes.byref(rf), self.str_format_center, ctypes.byref(bbox), None, None)
        return float(bbox.width), float(bbox.height)

    def _ensure_surface(self, w, h):
        if self.hbm and self.surface_w == w and self.surface_h == h:
            return
        if self.hbm:
            gdi32.DeleteObject(self.hbm)
        self.surface_w = w
        self.surface_h = h

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h # Top-down DIB
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = 0

        self.p_bits = ctypes.c_void_p()
        self.hbm = gdi32.CreateDIBSection(self.hdc_mem, ctypes.byref(bmi), 0, ctypes.byref(self.p_bits), None, 0)
        gdi32.SelectObject(self.hdc_mem, self.hbm)

    def recalculate_dimensions(self):
        self._init_fonts()
        show_net = config.get("show_net", True)
        show_cpu = config.get("show_cpu", True)
        show_cpu_temp = config.get("show_cpu_temp", True)
        show_gpu = config.get("show_gpu", False)
        show_gpu_temp = config.get("show_gpu_temp", False)
        show_ram = config.get("show_ram", True)
        show_disk = config.get("show_disk", True)
        pad_x = float(config.get("module_padding_x", 4))
        base_sz = config.get("font_size", 9)

        graphics = ctypes.c_void_p()
        gp.GdipCreateFromHDC(self.hdc_screen, ctypes.byref(graphics))

        unit_bytes = config.get("unit_bytes", True)
        w_d, _ = self.measure_text_gp(graphics, "↓ 999.9 MB/s" if unit_bytes else "↓ 999.9 Mbps", self.gp_font_small)
        w_u, _ = self.measure_text_gp(graphics, "↑ 999.9 MB/s" if unit_bytes else "↑ 999.9 Mbps", self.gp_font_small)
        self.col_w_net = max(w_d, w_u) + 2.0

        if show_cpu_temp:
            w_cpul, _ = self.measure_text_gp(graphics, "CPU 99°C", self.gp_font_label)
            w_cpuv, _ = self.measure_text_gp(graphics, "100%", self.gp_font_main)
            self.col_w_cpu = max(w_cpuv, w_cpul) + 2.0
        else:
            w_cpuv, _ = self.measure_text_gp(graphics, "100%", self.gp_font_main)
            w_cpul, _ = self.measure_text_gp(graphics, "CPU", self.gp_font_label)
            self.col_w_cpu = max(w_cpuv, w_cpul) + 2.0

        if show_gpu:
            if show_gpu_temp:
                w_gpul, _ = self.measure_text_gp(graphics, "GPU 99°C", self.gp_font_label)
                w_gpuv, _ = self.measure_text_gp(graphics, "100%", self.gp_font_main)
                self.col_w_gpu = max(w_gpuv, w_gpul) + 2.0
            else:
                w_gpuv, _ = self.measure_text_gp(graphics, "100%", self.gp_font_main)
                w_gpul, _ = self.measure_text_gp(graphics, "GPU", self.gp_font_label)
                self.col_w_gpu = max(w_gpuv, w_gpul) + 2.0

        w_ramv, _ = self.measure_text_gp(graphics, "100%", self.gp_font_main)
        w_raml, _ = self.measure_text_gp(graphics, "RAM", self.gp_font_label)
        self.col_w_ram = max(w_ramv, w_raml) + 2.0

        w_diskr, _ = self.measure_text_gp(graphics, "R 999.9 MB/s", self.gp_font_small)
        w_diskw, _ = self.measure_text_gp(graphics, "W 999.9 MB/s", self.gp_font_small)
        self.col_w_disk = max(w_diskr, w_diskw) + 2.0

        gp.GdipDeleteGraphics(graphics)

        cols = []
        if show_net: cols.append(self.col_w_net)
        if show_cpu: cols.append(self.col_w_cpu)
        if show_gpu: cols.append(self.col_w_gpu)
        if show_ram: cols.append(self.col_w_ram)
        if show_disk: cols.append(self.col_w_disk)

        if cols:
            total_w = 8.0 + sum(cols) + (len(cols) - 1) * (2 * pad_x)
        else:
            total_w = 80.0

        self.width = int(total_w + 0.5)
        self.height = max(34, int(22 + base_sz * 1.8))
        self._ensure_surface(self.width, self.height)

    def reposition_window(self):
        self.recalculate_dimensions()
        docked = config.get("dock_to_taskbar", True)

        if docked:
            hwnd_tray, rc_taskbar, notify_left, is_auto_hide, is_retracted = get_taskbar_info()
            tb_left, tb_top, tb_right, tb_bottom = rc_taskbar
            tb_h = tb_bottom - tb_top

            if is_auto_hide and is_retracted and config.get("auto_hide_sync", True):
                if not self.is_hidden_by_taskbar:
                    user32.ShowWindow(self.hwnd, SW_HIDE)
                    self.is_hidden_by_taskbar = True
                return

            if self.is_hidden_by_taskbar:
                user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)
                self.is_hidden_by_taskbar = False

            y = tb_top + max(0, (tb_h - self.height) // 2)
            user_offset = config.get("taskbar_offset_x", 0)
            x = notify_left - self.width - 8 - user_offset

            self.current_x = x
            self.current_y = y
        else:
            if self.is_hidden_by_taskbar:
                user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)
                self.is_hidden_by_taskbar = False

            self.current_x = config.get("floating_x", 300)
            self.current_y = config.get("floating_y", 300)

        # Force HWND_TOPMOST so taskbar clicks/redraws NEVER bury the meter
        user32.SetWindowPos(
            self.hwnd, HWND_TOPMOST,
            self.current_x, self.current_y, self.width, self.height,
            0x0010 | 0x0040 # SWP_NOACTIVATE | SWP_SHOWWINDOW
        )
        self.render()

    def on_tick(self):
        if config.check_and_reload():
            self.reposition_window()
            return

        self.metrics.update()

        unit_bytes = config.get("unit_bytes", True)
        d_str = format_speed(self.metrics.down_speed, unit_bytes)
        u_str = format_speed(self.metrics.up_speed, unit_bytes)
        ping_str = f"Ping: {self.metrics.ping_ms} ms" if self.metrics.ping_ms > 0 else "Ping: Checking..."

        tip = f"Net: ↓ {d_str} ↑ {u_str} ({ping_str})\nCPU: {self.metrics.cpu_percent:.0f}%\nRAM: {self.metrics.ram_percent:.0f}% ({self.metrics.ram_used_gb:.1f}G)\nDisk: R {format_speed(self.metrics.disk_read_speed, True)} | W {format_speed(self.metrics.disk_write_speed, True)}"
        if self.tray:
            self.tray.update_tooltip(tip)

        if config.get("dock_to_taskbar", True):
            self.reposition_window()
        else:
            self.render()

    def render(self):
        if self.is_hidden_by_taskbar:
            return

        w = self.width
        h = self.height
        if w <= 0 or h <= 0 or not self.p_bits:
            return

        bg_mode = config.get("bg_mode", "taskbar")
        custom_bg_hex = config.get("custom_bg_hex", "#1E1E24")
        docked = config.get("dock_to_taskbar", True)

        active_bg_mode = bg_mode if not docked else ("taskbar" if bg_mode == "taskbar" else bg_mode)
        bg_rgb, is_dark = get_background_colors(active_bg_mode, custom_bg_hex)

        buf = (ctypes.c_uint32 * (w * h)).from_address(self.p_bits.value)

        # 1. Background Fill with Native Per-Pixel Alpha
        if active_bg_mode == "transparent":
            # True per-pixel alpha transparency! (Alpha=1 ensures entire rectangle is hit-testable)
            buf[:] = [0x01000000] * (w * h)
        elif active_bg_mode == "glass":
            opacity = config.get("glass_opacity", 0.88)
            argb_bg = hex_to_argb(custom_bg_hex, int(255 * opacity))
            buf[:] = [argb_bg] * (w * h)
        elif active_bg_mode == "taskbar":
            argb_bg = (0xFF << 24) | (bg_rgb[0] << 16) | (bg_rgb[1] << 8) | bg_rgb[2]
            buf[:] = [argb_bg] * (w * h)
        else:
            # Solid dark or custom
            argb_bg = hex_to_argb(custom_bg_hex, 255)
            buf[:] = [argb_bg] * (w * h)

        # 2. GDI+ Surface Rendering
        graphics = ctypes.c_void_p()
        gp.GdipCreateFromHDC(self.hdc_mem, ctypes.byref(graphics))
        gp.GdipSetTextRenderingHint(graphics, 3) # TextRenderingHintAntiAliasGridFit (Cleanest UI text!)
        gp.GdipSetSmoothingMode(graphics, 2)     # SmoothingModeAntiAlias

        # Outer border in floating mode if not transparent
        if not docked and active_bg_mode != "transparent":
            border_pen = ctypes.c_void_p()
            border_argb = 0x50FFFFFF if is_dark else 0x40000000
            gp.GdipCreatePen1(border_argb, 1.0, 2, ctypes.byref(border_pen))
            gp.GdipDrawRectangle(graphics, border_pen, 0.5, 0.5, float(w - 1), float(h - 1))
            gp.GdipDeletePen(border_pen)

        # Colors from config
        c_down = config.get_argb_color("color_net_down")
        c_up = config.get_argb_color("color_net_up")
        c_cpu = config.get_argb_color("color_cpu")
        c_ram = config.get_argb_color("color_ram")
        c_disk_r = config.get_argb_color("color_disk_r")
        c_disk_w = config.get_argb_color("color_disk_w")
        c_label = config.get_argb_color("color_label")
        
        # Temperature & Alert Colors
        c_cpu_temp = config.get_argb_color("color_cpu_temp")
        c_gpu_temp = config.get_argb_color("color_gpu_temp")
        c_alert = config.get_argb_color("color_temp_alert")
        cpu_thresh = float(config.get("cpu_temp_alert_threshold", 85))
        gpu_thresh = float(config.get("gpu_temp_alert_threshold", 80))
        enable_alert = config.get("enable_temp_alert_color", True)

        def draw_str(text, rf, argb, font):
            brush = ctypes.c_void_p()
            gp.GdipCreateSolidFill(ctypes.c_uint32(argb), ctypes.byref(brush))
            gp.GdipDrawString(graphics, text, len(text), font, ctypes.byref(rf), self.str_format_center, brush)
            gp.GdipDeleteBrush(brush)

        def draw_separator(x_pos):
            if active_bg_mode == "transparent":
                return
            sep_pen = ctypes.c_void_p()
            sep_argb = 0x30FFFFFF if is_dark else 0x25000000
            gp.GdipCreatePen1(sep_argb, 1.0, 2, ctypes.byref(sep_pen))
            gp.GdipDrawLine(graphics, sep_pen, float(x_pos), 7.0, float(x_pos), float(h - 7))
            gp.GdipDeletePen(sep_pen)

        row_h = (h - 4) / 2.0
        line1_y = 2.0
        line2_y = line1_y + row_h
        cur_x = 4.0
        pad_x = float(config.get("module_padding_x", 4))

        show_net = config.get("show_net", True)
        show_cpu = config.get("show_cpu", True)
        show_cpu_temp = config.get("show_cpu_temp", True)
        show_gpu = config.get("show_gpu", False)
        show_gpu_temp = config.get("show_gpu_temp", False)
        show_ram = config.get("show_ram", True)
        show_disk = config.get("show_disk", True)

        # 1. Network Speed
        if show_net:
            col_w = self.col_w_net
            unit_bytes = config.get("unit_bytes", True)
            d_str = format_speed(self.metrics.down_speed, unit_bytes)
            u_str = format_speed(self.metrics.up_speed, unit_bytes)
            rf1 = RectF(cur_x, line1_y, col_w, row_h)
            rf2 = RectF(cur_x, line2_y, col_w, row_h)
            draw_str(f"↓ {d_str}", rf1, c_down, self.gp_font_small)
            draw_str(f"↑ {u_str}", rf2, c_up, self.gp_font_small)
            cur_x += col_w
            if (show_cpu or show_gpu or show_ram or show_disk):
                cur_x += pad_x
                if pad_x >= 2:
                    draw_separator(cur_x)
                cur_x += pad_x

        # 2. CPU (With Inline Temperature & Restored Large Font!)
        if show_cpu:
            col_w = self.col_w_cpu
            rf1 = RectF(cur_x, line1_y, col_w, row_h)
            rf2 = RectF(cur_x, line2_y, col_w, row_h)
            if show_cpu_temp:
                t_color = c_alert if (enable_alert and self.metrics.cpu_temp >= cpu_thresh) else c_cpu_temp
                draw_str(f"CPU {self.metrics.cpu_temp:.0f}°C", rf1, t_color, self.gp_font_label)
                draw_str(f"{self.metrics.cpu_percent:.0f}%", rf2, c_cpu, self.gp_font_main)
            else:
                draw_str("CPU", rf1, c_label, self.gp_font_label)
                draw_str(f"{self.metrics.cpu_percent:.0f}%", rf2, c_cpu, self.gp_font_main)
            cur_x += col_w
            if (show_gpu or show_ram or show_disk):
                cur_x += pad_x
                if pad_x >= 2:
                    draw_separator(cur_x)
                cur_x += pad_x

        # 3. GPU (Optional, Default Off)
        if show_gpu:
            col_w = self.col_w_gpu
            rf1 = RectF(cur_x, line1_y, col_w, row_h)
            rf2 = RectF(cur_x, line2_y, col_w, row_h)
            c_gpu = config.get_argb_color("color_cpu")
            if show_gpu_temp:
                g_color = c_alert if (enable_alert and self.metrics.gpu_temp >= gpu_thresh) else c_gpu_temp
                draw_str(f"GPU {self.metrics.gpu_temp:.0f}°C", rf1, g_color, self.gp_font_label)
                draw_str(f"{self.metrics.gpu_percent:.0f}%", rf2, c_gpu, self.gp_font_main)
            else:
                draw_str("GPU", rf1, c_label, self.gp_font_label)
                draw_str(f"{self.metrics.gpu_percent:.0f}%", rf2, c_gpu, self.gp_font_main)
            cur_x += col_w
            if (show_ram or show_disk):
                cur_x += pad_x
                if pad_x >= 2:
                    draw_separator(cur_x)
                cur_x += pad_x

        # 4. RAM (Original Large Font Sizing Restored!)
        if show_ram:
            col_w = self.col_w_ram
            rf1 = RectF(cur_x, line1_y, col_w, row_h)
            rf2 = RectF(cur_x, line2_y, col_w, row_h)
            draw_str("RAM", rf1, c_label, self.gp_font_label)
            draw_str(f"{self.metrics.ram_percent:.0f}%", rf2, c_ram, self.gp_font_main)
            cur_x += col_w
            if show_disk:
                cur_x += pad_x
                if pad_x >= 2:
                    draw_separator(cur_x)
                cur_x += pad_x

        # 4. Disk
        if show_disk:
            col_w = self.col_w_disk
            r_spd = format_speed(self.metrics.disk_read_speed, True)
            w_spd = format_speed(self.metrics.disk_write_speed, True)
            rf1 = RectF(cur_x, line1_y, col_w, row_h)
            rf2 = RectF(cur_x, line2_y, col_w, row_h)
            draw_str(f"R {r_spd}", rf1, c_disk_r, self.gp_font_small)
            draw_str(f"W {w_spd}", rf2, c_disk_w, self.gp_font_small)
            cur_x += col_w

        gp.GdipDeleteGraphics(graphics)

        # 3. UpdateLayeredWindow with DWM Hardware Alpha Compositing
        pt_dst = wintypes.POINT(self.current_x, self.current_y)
        sz_dst = wintypes.SIZE(w, h)
        pt_src = wintypes.POINT(0, 0)
        blend = BLENDFUNCTION(0, 0, 255, 1) # AC_SRC_OVER, AC_SRC_ALPHA

        user32.UpdateLayeredWindow(
            self.hwnd, self.hdc_screen, ctypes.byref(pt_dst), ctypes.byref(sz_dst),
            self.hdc_mem, ctypes.byref(pt_src), 0, ctypes.byref(blend), 2 # ULW_ALPHA
        )

    def _window_procedure(self, hwnd, msg, wparam, lparam):
        if msg == WM_TIMER:
            self.on_tick()
            return 0

        elif msg == WM_LBUTTONDOWN:
            now = time.time()
            if now - self.last_click_time < 0.35:
                # Double click: toggle Docked in Taskbar vs Floating Mode!
                config.toggle("dock_to_taskbar")
                self.reposition_window()
                return 0
            self.last_click_time = now

            if config.get("is_locked", False):
                return 0

            if not config.get("dock_to_taskbar", True):
                self.is_dragging = True
                user32.SetCapture(hwnd)
                pt = wintypes.POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                rc = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rc))
                self.drag_offset_x = pt.x - rc.left
                self.drag_offset_y = pt.y - rc.top
            return 0

        elif msg == WM_MOUSEMOVE:
            if self.is_dragging:
                pt = wintypes.POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                new_x = pt.x - self.drag_offset_x
                new_y = pt.y - self.drag_offset_y
                self.current_x = new_x
                self.current_y = new_y
                user32.SetWindowPos(hwnd, 0, new_x, new_y, 0, 0, 0x0001 | 0x0004 | 0x0010)
                config.set("floating_x", new_x)
                config.set("floating_y", new_y)
            return 0

        elif msg == WM_LBUTTONUP:
            if self.is_dragging:
                self.is_dragging = False
                user32.ReleaseCapture()
            return 0

        elif msg == WM_RBUTTONUP:
            if self.tray:
                self.tray.show_context_menu(on_change_callback=lambda need_repos: self.reposition_window() if need_repos else self.render())
            return 0

        elif msg == 0x0208: # WM_MBUTTONUP (Middle Click: Open Dashboard)
            open_dashboard_window()
            return 0

        elif msg == WM_TRAYICON:
            event = lparam & 0xFFFF
            if event in (WM_RBUTTONUP, 0x0202):
                if self.tray:
                    self.tray.show_context_menu(on_change_callback=lambda need_repos: self.reposition_window() if need_repos else self.render())
            return 0

        elif msg == WM_DESTROY or msg == WM_CLOSE:
            self._cleanup()
            return 0

        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _cleanup(self):
        if self.tray:
            self.tray.remove()
        user32.KillTimer(self.hwnd, 1)

        if self.gp_font_main:
            gp.GdipDeleteFont(self.gp_font_main)
        if self.gp_font_small:
            gp.GdipDeleteFont(self.gp_font_small)
        if self.gp_font_label:
            gp.GdipDeleteFont(self.gp_font_label)
        if self.gp_font_family:
            gp.GdipDeleteFontFamily(self.gp_font_family)
        if self.str_format_center:
            gp.GdipDeleteStringFormat(self.str_format_center)

        if self.hbm:
            gdi32.DeleteObject(self.hbm)
        if self.hdc_mem:
            gdi32.DeleteDC(self.hdc_mem)
        if self.hdc_screen:
            user32.ReleaseDC(0, self.hdc_screen)

        if self.gp_token:
            gp.GdiplusShutdown(self.gp_token)

        user32.PostQuitMessage(0)

    def run(self):
        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
