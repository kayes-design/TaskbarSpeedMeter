import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import subprocess
import os
import sys
from config import config, THEME_PRESETS, hex_to_rgb
from metrics import format_bytes
from win32_utils import set_autostart, is_autostart_enabled

class SettingsDialog:
    def __init__(self, on_apply_callback=None):
        self.on_apply = on_apply_callback
        self.root = None

    def show(self):
        if self.root is not None:
            try:
                self.root.lift()
                self.root.focus_force()
                return
            except Exception:
                self.root = None

        self.root = tk.Tk()
        self.root.title("Taskbar Speed Meter — Settings & Customizer")
        dlg_w, dlg_h = 600, 650
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - dlg_w) // 2)
        y = max(0, (sh - dlg_h) // 2)
        self.root.geometry(f"{dlg_w}x{dlg_h}+{x}+{y}")
        self.root.resizable(False, False)

        # Force window to foreground so it is never hidden behind browsers or taskbar
        self.root.attributes("-topmost", True)
        self.root.after(300, lambda: self.root.attributes("-topmost", False) if self.root else None)
        self.root.lift()
        self.root.focus_force()

        style = ttk.Style()
        try:
            style.theme_use('vista')
        except Exception:
            pass

        # Action Buttons bar — PACKED FIRST AT BOTTOM so it is NEVER pushed off screen!
        f_bottom = ttk.Frame(self.root, padding=(12, 10))
        f_bottom.pack(side='bottom', fill='x')

        btn_apply = ttk.Button(f_bottom, text="💾 Save & Apply Changes", command=self._apply_and_close)
        btn_apply.pack(side='right', padx=6)

        btn_live = ttk.Button(f_bottom, text="⚡ Apply Live", command=self._save_config_data)
        btn_live.pack(side='right', padx=6)

        btn_close = ttk.Button(f_bottom, text="Cancel", command=self.root.destroy)
        btn_close.pack(side='right', padx=6)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=(10, 0))

        # ================= TAB 1: Colors & Background =================
        tab_colors = ttk.Frame(notebook, padding=12)
        notebook.add(tab_colors, text="  🎨 Colors & Background  ")

        # Background mode
        lbl_bg = ttk.Label(tab_colors, text="Background Appearance:", font=("Segoe UI", 9, "bold"))
        lbl_bg.pack(anchor='w', pady=(0, 4))

        f_bg = ttk.Frame(tab_colors)
        f_bg.pack(fill='x', pady=2)

        self.var_bg = tk.StringVar(value=config.get("bg_mode", "taskbar"))
        bg_opts = [
            ("taskbar", "Auto Match Taskbar"),
            ("glass", "Acrylic Frosted Glass (Soft Dark - No Glare)"),
            ("dark", "Solid Dark (#121216)"),
            ("transparent", "Transparent (Text with Anti-Glare Shadow)"),
            ("custom", "Custom Background Color")
        ]
        cb_bg = ttk.Combobox(f_bg, textvariable=self.var_bg, state="readonly", values=[opt[0] for opt in bg_opts], width=20)
        cb_bg.pack(side='left', padx=(0, 10))

        # Custom BG Color Picker
        self.var_custom_bg = tk.StringVar(value=config.get("custom_bg_hex", "#1E1E24"))
        self.btn_bg_swatch = tk.Button(f_bg, width=3, height=1, bg=self.var_custom_bg.get(), relief='solid', borderwidth=1)
        self.btn_bg_swatch.pack(side='left', padx=4)

        def pick_bg_color():
            color = colorchooser.askcolor(color=self.var_custom_bg.get(), title="Choose Custom Background Color")
            if color and color[1]:
                hex_c = color[1].upper()
                self.var_custom_bg.set(hex_c)
                self.btn_bg_swatch.config(bg=hex_c)
                self.var_bg.set("custom")
                self._save_config_data()

        btn_pick_bg = ttk.Button(f_bg, text="Pick Color...", command=pick_bg_color)
        btn_pick_bg.pack(side='left', padx=4)

        ttk.Separator(tab_colors, orient='horizontal').pack(fill='x', pady=10)

        # Theme Presets
        f_pre = ttk.Frame(tab_colors)
        f_pre.pack(fill='x', pady=2)
        ttk.Label(f_pre, text="Quick Theme Presets:", font=("Segoe UI", 9, "bold")).pack(side='left')
        self.var_theme = tk.StringVar(value=config.get("theme_preset", "native"))
        cb_theme = ttk.Combobox(f_pre, textvariable=self.var_theme, state="readonly", values=list(THEME_PRESETS.keys()), width=16)
        cb_theme.pack(side='left', padx=10)

        def on_theme_select(event):
            preset_key = self.var_theme.get()
            if preset_key in THEME_PRESETS:
                t = THEME_PRESETS[preset_key]
                self.var_uniform.set(False)
                self.colors["color_net_down"].set(t["net_down"])
                self.colors["color_net_up"].set(t["net_up"])
                self.colors["color_cpu"].set(t["cpu"])
                self.colors["color_ram"].set(t["ram"])
                self.colors["color_disk_r"].set(t["disk_r"])
                self.colors["color_disk_w"].set(t["disk_w"])
                self.colors["color_label"].set(t["label"])
                self.update_color_swatches()
                self._save_config_data()

        cb_theme.bind("<<ComboboxSelected>>", on_theme_select)

        # Uniform Color Toggle
        f_uni = ttk.Frame(tab_colors)
        f_uni.pack(fill='x', pady=6)
        self.var_uniform = tk.BooleanVar(value=config.get("use_uniform_color", False))
        self.var_uniform_hex = tk.StringVar(value=config.get("uniform_color_hex", "#00E5FF"))

        chk_uni = ttk.Checkbutton(f_uni, text="Use single uniform color for all text", variable=self.var_uniform, command=self._save_config_data)
        chk_uni.pack(side='left')

        self.btn_uni_swatch = tk.Button(f_uni, width=3, height=1, bg=self.var_uniform_hex.get(), relief='solid', borderwidth=1)
        self.btn_uni_swatch.pack(side='left', padx=8)

        def pick_uniform_color():
            color = colorchooser.askcolor(color=self.var_uniform_hex.get(), title="Choose Uniform Text Color")
            if color and color[1]:
                hex_c = color[1].upper()
                self.var_uniform_hex.set(hex_c)
                self.btn_uni_swatch.config(bg=hex_c)
                self.var_uniform.set(True)
                self._save_config_data()

        ttk.Button(f_uni, text="Pick...", command=pick_uniform_color).pack(side='left')

        ttk.Separator(tab_colors, orient='horizontal').pack(fill='x', pady=8)

        # Individual Metric Colors Grid
        ttk.Label(tab_colors, text="Custom Metric Colors (Pick Any Color):", font=("Segoe UI", 9, "bold")).pack(anchor='w', pady=(0, 4))

        color_keys = [
            ("color_net_down", "Download Speed (↓)"),
            ("color_net_up", "Upload Speed (↑)"),
            ("color_cpu", "CPU Usage"),
            ("color_ram", "RAM Usage"),
            ("color_disk_r", "Disk Read (R)"),
            ("color_disk_w", "Disk Write (W)"),
            ("color_label", "Column Labels"),
            ("color_cpu_temp", "CPU Temp (Normal)"),
            ("color_temp_alert", "Alert Temp Color (Red/Black/Custom)"),
        ]

        self.colors = {}
        self.swatches = {}

        grid_frame = ttk.Frame(tab_colors)
        grid_frame.pack(fill='x', pady=2)

        for i, (ckey, clabel) in enumerate(color_keys):
            row = i // 2
            col_offset = (i % 2) * 3

            val = config.get(ckey, "#FFFFFF")
            if isinstance(val, list):
                val = f"#{val[0]:02X}{val[1]:02X}{val[2]:02X}"
            self.colors[ckey] = tk.StringVar(value=val)

            ttk.Label(grid_frame, text=clabel, width=22).grid(row=row, column=col_offset, sticky='w', pady=2)

            swatch = tk.Button(grid_frame, width=2, height=1, bg=val, relief='solid', borderwidth=1)
            swatch.grid(row=row, column=col_offset+1, padx=2, pady=2)
            self.swatches[ckey] = swatch

            def make_picker(k=ckey, sw=swatch):
                def pick():
                    color = colorchooser.askcolor(color=self.colors[k].get(), title=f"Choose Color for {k}")
                    if color and color[1]:
                        hex_c = color[1].upper()
                        self.colors[k].set(hex_c)
                        sw.config(bg=hex_c)
                        self.var_uniform.set(False)
                        self._save_config_data()
                return pick

            btn = ttk.Button(grid_frame, text="Pick", width=5, command=make_picker(ckey, swatch))
            btn.grid(row=row, column=col_offset+2, padx=(2, 10), pady=2)

        def update_swatches():
            self.btn_bg_swatch.config(bg=self.var_custom_bg.get())
            self.btn_uni_swatch.config(bg=self.var_uniform_hex.get())
            for k, sw in self.swatches.items():
                sw.config(bg=self.colors[k].get())
        self.update_color_swatches = update_swatches

        # ================= TAB 2: Typography & Layout =================
        tab_layout = ttk.Frame(notebook, padding=12)
        notebook.add(tab_layout, text="  📐 Layout & Typography  ")

        lbl_typo = ttk.Label(tab_layout, text="Typography & Font Sizing:", font=("Segoe UI", 9, "bold"))
        lbl_typo.pack(anchor='w', pady=(0, 6))

        f_t1 = ttk.Frame(tab_layout)
        f_t1.pack(fill='x', pady=3)
        ttk.Label(f_t1, text="Font Size:", width=14).pack(side='left')
        self.var_fsize = tk.IntVar(value=config.get("font_size", 9))
        cb_fsize = ttk.Combobox(f_t1, textvariable=self.var_fsize, state="readonly", values=[8, 9, 10, 11, 12, 13, 14], width=10)
        cb_fsize.pack(side='left', padx=6)
        cb_fsize.bind("<<ComboboxSelected>>", lambda e: self._save_config_data())

        ttk.Label(f_t1, text="Font Family:", width=12).pack(side='left', padx=(14, 0))
        self.var_ffam = tk.StringVar(value=config.get("font_family", "Segoe UI"))
        cb_ffam = ttk.Combobox(f_t1, textvariable=self.var_ffam, state="readonly", values=["Segoe UI", "Consolas", "Arial", "Tahoma", "Trebuchet MS"], width=14)
        cb_ffam.pack(side='left', padx=6)
        cb_ffam.bind("<<ComboboxSelected>>", lambda e: self._save_config_data())

        # Module Column Padding / Spacing Slider
        f_t2 = ttk.Frame(tab_layout)
        f_t2.pack(fill='x', pady=8)
        ttk.Label(f_t2, text="Column Spacing:", width=14).pack(side='left')
        self.var_pad = tk.IntVar(value=config.get("module_padding_x", 4))
        slider_pad = ttk.Scale(f_t2, from_=0, to=16, variable=self.var_pad, orient='horizontal')
        slider_pad.pack(side='left', fill='x', expand=True, padx=6)
        self.lbl_pad_val = ttk.Label(f_t2, text=f"{self.var_pad.get()} px")
        self.lbl_pad_val.pack(side='left', padx=4)

        def on_pad_slide(val):
            ival = int(float(val))
            self.lbl_pad_val.config(text=f"{ival} px")
            self.var_pad.set(ival)
            self._save_config_data()

        slider_pad.config(command=on_pad_slide)

        # Text Shadow Toggle
        self.var_shadow = tk.BooleanVar(value=config.get("text_shadow", True))
        ttk.Checkbutton(tab_layout, text="Enable anti-glare text drop-shadow (Recommended for transparent backgrounds)", variable=self.var_shadow, command=self._save_config_data).pack(anchor='w', pady=6)

        ttk.Separator(tab_layout, orient='horizontal').pack(fill='x', pady=10)

        # Active Modules
        ttk.Label(tab_layout, text="Active Modules on Widget:", font=("Segoe UI", 9, "bold")).pack(anchor='w', pady=(0, 4))

        self.var_net = tk.BooleanVar(value=config.get("show_net", True))
        self.var_cpu = tk.BooleanVar(value=config.get("show_cpu", True))
        self.var_cpu_temp = tk.BooleanVar(value=config.get("show_cpu_temp", True))
        self.var_gpu = tk.BooleanVar(value=config.get("show_gpu", False))
        self.var_ram = tk.BooleanVar(value=config.get("show_ram", True))
        self.var_disk = tk.BooleanVar(value=config.get("show_disk", True))

        f_mods = ttk.Frame(tab_layout)
        f_mods.pack(fill='x', pady=2)
        ttk.Checkbutton(f_mods, text="⚡ Network Speed", variable=self.var_net, command=self._save_config_data).grid(row=0, column=0, sticky='w', padx=10, pady=2)
        ttk.Checkbutton(f_mods, text="⚙️ CPU Usage (%)", variable=self.var_cpu, command=self._save_config_data).grid(row=0, column=1, sticky='w', padx=10, pady=2)
        ttk.Checkbutton(f_mods, text="🌡️ CPU Temperature (°C)", variable=self.var_cpu_temp, command=self._save_config_data).grid(row=1, column=0, sticky='w', padx=10, pady=2)
        ttk.Checkbutton(f_mods, text="🎮 GPU Usage & Temp (Off by default)", variable=self.var_gpu, command=self._save_config_data).grid(row=1, column=1, sticky='w', padx=10, pady=2)
        ttk.Checkbutton(f_mods, text="🧠 RAM Usage (%)", variable=self.var_ram, command=self._save_config_data).grid(row=2, column=0, sticky='w', padx=10, pady=2)
        ttk.Checkbutton(f_mods, text="💾 Disk I/O (R / W)", variable=self.var_disk, command=self._save_config_data).grid(row=2, column=1, sticky='w', padx=10, pady=2)

        ttk.Separator(tab_layout, orient='horizontal').pack(fill='x', pady=8)

        # Thermal Thresholds & Alerts
        ttk.Label(tab_layout, text="🌡️ Thermal Thresholds & Custom Alert Color:", font=("Segoe UI", 9, "bold")).pack(anchor='w', pady=(0, 2))
        self.var_alert_color = tk.BooleanVar(value=config.get("enable_temp_alert_color", True))
        ttk.Checkbutton(tab_layout, text="Enable Alert Color when temperature exceeds threshold", variable=self.var_alert_color, command=self._save_config_data).pack(anchor='w', pady=2)

        f_thresh = ttk.Frame(tab_layout)
        f_thresh.pack(fill='x', pady=2)
        ttk.Label(f_thresh, text="CPU Alert Threshold:", width=18).pack(side='left')
        self.var_cpu_thresh = tk.IntVar(value=config.get("cpu_temp_alert_threshold", 85))
        sp_cpu = ttk.Spinbox(f_thresh, from_=50, to=105, textvariable=self.var_cpu_thresh, width=6, command=self._save_config_data)
        sp_cpu.pack(side='left', padx=4)
        ttk.Label(f_thresh, text="°C (Default: 85°C)").pack(side='left', padx=(0, 14))

        ttk.Label(f_thresh, text="GPU Alert Threshold:", width=18).pack(side='left')
        self.var_gpu_thresh = tk.IntVar(value=config.get("gpu_temp_alert_threshold", 80))
        sp_gpu = ttk.Spinbox(f_thresh, from_=50, to=105, textvariable=self.var_gpu_thresh, width=6, command=self._save_config_data)
        sp_gpu.pack(side='left', padx=4)
        ttk.Label(f_thresh, text="°C (Default: 80°C)").pack(side='left')

        ttk.Separator(tab_layout, orient='horizontal').pack(fill='x', pady=10)

        # Docking & Taskbar Offset
        ttk.Label(tab_layout, text="Positioning & Taskbar Safe Margin:", font=("Segoe UI", 9, "bold")).pack(anchor='w', pady=(0, 4))
        self.var_dock = tk.BooleanVar(value=config.get("dock_to_taskbar", True))
        self.var_lock = tk.BooleanVar(value=config.get("is_locked", False))
        self.var_autostart = tk.BooleanVar(value=is_autostart_enabled())

        ttk.Checkbutton(tab_layout, text="📌 Dock to Taskbar (Snaps automatically beside System Tray)", variable=self.var_dock, command=self._save_config_data).pack(anchor='w', pady=2)
        ttk.Checkbutton(tab_layout, text="🔒 Lock Position (Prevents accidental mouse dragging anywhere)", variable=self.var_lock, command=self._save_config_data).pack(anchor='w', pady=2)
        ttk.Checkbutton(tab_layout, text="🚀 Launch automatically on Windows Startup", variable=self.var_autostart, command=self._save_config_data).pack(anchor='w', pady=2)

        # Taskbar Spacing Offset slider
        f_slider = ttk.Frame(tab_layout)
        f_slider.pack(fill='x', pady=(6, 0))
        ttk.Label(f_slider, text="Taskbar Offset:", width=14).pack(side='left')
        self.var_offset = tk.IntVar(value=config.get("taskbar_offset_x", 0))
        slider = ttk.Scale(f_slider, from_=-50, to=250, variable=self.var_offset, orient='horizontal')
        slider.pack(side='left', fill='x', expand=True, padx=6)
        self.lbl_offset_val = ttk.Label(f_slider, text=f"{self.var_offset.get()} px")
        self.lbl_offset_val.pack(side='left', padx=4)

        def on_offset_slide(val):
            ival = int(float(val))
            self.lbl_offset_val.config(text=f"{ival} px")
            self.var_offset.set(ival)
            self._save_config_data()

        slider.config(command=on_offset_slide)

        # ================= TAB 3: Data Usage & Tools =================
        tab_data = ttk.Frame(notebook, padding=12)
        notebook.add(tab_data, text="  📊 Data Usage & Tools  ")

        today_down = format_bytes(config.get("today_down_bytes", 0))
        today_up = format_bytes(config.get("today_up_bytes", 0))
        today_tot = format_bytes(config.get("today_down_bytes", 0) + config.get("today_up_bytes", 0))

        month_down = format_bytes(config.get("month_down_bytes", 0))
        month_up = format_bytes(config.get("month_up_bytes", 0))
        month_tot = format_bytes(config.get("month_down_bytes", 0) + config.get("month_up_bytes", 0))

        lbl_usage = ttk.Label(tab_data, text="Internet Data Consumption History:", font=("Segoe UI", 9, "bold"))
        lbl_usage.pack(anchor='w', pady=(0, 6))

        card_frame = ttk.LabelFrame(tab_data, text=" Bandwidth Statistics ", padding=10)
        card_frame.pack(fill='x', pady=4)

        ttk.Label(card_frame, text=f"• Today's Total: {today_tot} (↓ {today_down}  |  ↑ {today_up})", font=("Segoe UI", 9, "bold")).pack(anchor='w', pady=3)
        ttk.Label(card_frame, text=f"• This Month: {month_tot} (↓ {month_down}  |  ↑ {month_up})", font=("Segoe UI", 9)).pack(anchor='w', pady=3)

        def reset_data_usage():
            if messagebox.askyesno("Reset Counter", "Reset today and this month's bandwidth statistics to 0?"):
                config.set("today_down_bytes", 0)
                config.set("today_up_bytes", 0)
                config.set("month_down_bytes", 0)
                config.set("month_up_bytes", 0)
                messagebox.showinfo("Reset", "Counters have been reset successfully.")

        ttk.Button(card_frame, text="Reset Usage Counters", command=reset_data_usage).pack(anchor='e', pady=(6, 0))

        ttk.Separator(tab_data, orient='horizontal').pack(fill='x', pady=12)

        lbl_wifi = ttk.Label(tab_data, text="Wi-Fi Password Revealer:", font=("Segoe UI", 9, "bold"))
        lbl_wifi.pack(anchor='w', pady=(0, 6))

        def reveal_wifi_passwords():
            try:
                res = subprocess.check_output(['netsh', 'wlan', 'show', 'profiles'], text=True, errors='ignore')
                profiles = [line.split(":", 1)[1].strip() for line in res.splitlines() if "All User Profile" in line]
                if not profiles:
                    messagebox.showinfo("Wi-Fi Passwords", "No saved Wi-Fi profiles found.")
                    return
                msg_lines = []
                for p in profiles[:8]:
                    p_cmd = subprocess.check_output(['netsh', 'wlan', 'show', 'profile', f'name={p}', 'key=clear'], text=True, errors='ignore')
                    pwd = "Open / No Pass"
                    for pline in p_cmd.splitlines():
                        if "Key Content" in pline:
                            pwd = pline.split(":", 1)[1].strip()
                            break
                    msg_lines.append(f"• {p}:  {pwd}")
                messagebox.showinfo("Saved Wi-Fi Passwords", "\n".join(msg_lines))
            except Exception as e:
                messagebox.showerror("Wi-Fi Error", f"Unable to read Wi-Fi profiles: {e}")

        ttk.Button(tab_data, text="🔍 Show Saved Wi-Fi Passwords", command=reveal_wifi_passwords).pack(anchor='w', pady=4)

        ttk.Separator(tab_data, orient='horizontal').pack(fill='x', pady=10)
        ttk.Label(tab_data, text="Live Hardware Telemetry & Thermal Sensors:", font=("Segoe UI", 9, "bold")).pack(anchor='w', pady=(0, 4))
        from dashboard_window import open_dashboard_window
        ttk.Button(tab_data, text="📊 Open Hardware & Sensors Dashboard", command=open_dashboard_window).pack(anchor='w', pady=4)

        self.root.mainloop()

    def _save_config_data(self):
        config.set("bg_mode", self.var_bg.get())
        config.set("custom_bg_hex", self.var_custom_bg.get())
        config.set("theme_preset", self.var_theme.get())

        config.set("use_uniform_color", self.var_uniform.get())
        config.set("uniform_color_hex", self.var_uniform_hex.get())

        for k, var in self.colors.items():
            config.set(k, var.get())

        config.set("font_size", int(self.var_fsize.get()))
        config.set("font_family", self.var_ffam.get())
        config.set("module_padding_x", int(self.var_pad.get()))
        config.set("text_shadow", self.var_shadow.get())

        config.set("show_net", self.var_net.get())
        config.set("show_cpu", self.var_cpu.get())
        config.set("show_cpu_temp", self.var_cpu_temp.get())
        config.set("show_gpu", self.var_gpu.get())
        config.set("show_gpu_temp", self.var_gpu.get())
        config.set("show_ram", self.var_ram.get())
        config.set("show_disk", self.var_disk.get())

        config.set("cpu_temp_alert_threshold", int(self.var_cpu_thresh.get()))
        config.set("gpu_temp_alert_threshold", int(self.var_gpu_thresh.get()))
        config.set("enable_temp_alert_color", self.var_alert_color.get())

        config.set("dock_to_taskbar", self.var_dock.get())
        config.set("is_locked", self.var_lock.get())
        config.set("taskbar_offset_x", int(self.var_offset.get()))

        set_autostart(self.var_autostart.get())
        config.set("autostart", self.var_autostart.get())

        config.save()

        if self.on_apply:
            self.on_apply()

    def _apply_and_close(self):
        self._save_config_data()
        self.root.destroy()
        self.root = None

def open_settings_dialog(on_apply_callback=None):
    try:
        if getattr(sys, 'frozen', False):
            app_exe = sys.executable
            subprocess.Popen([app_exe, "--settings"])
            return
        else:
            main_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
            if os.path.exists(main_py):
                subprocess.Popen([sys.executable, main_py, "--settings"])
                return
    except Exception as e:
        print(f"[Settings] Subprocess launch error: {e}", file=sys.stderr)

    import threading
    t = threading.Thread(target=lambda: SettingsDialog(on_apply_callback=on_apply_callback).show(), daemon=True)
    t.start()
