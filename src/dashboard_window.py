import tkinter as tk
from tkinter import ttk
import os
import sys
import time
import winreg
import psutil
from config import config
from metrics import format_speed, format_bytes

def get_cpu_model_name():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
        name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        winreg.CloseKey(key)
        return name.strip()
    except Exception:
        import platform
        return platform.processor() or "AMD / Intel Processor"

class DashboardWindow:
    _instance = None

    def __init__(self, metrics=None):
        self.metrics = metrics
        self.root = None
        self.is_running = False

    def show(self):
        if self.root is not None:
            try:
                self.root.lift()
                self.root.focus_force()
                return
            except Exception:
                self.root = None

        self.root = tk.Tk()
        self.root.title("Taskbar Speed Meter — Hardware & Sensor Dashboard")
        
        # Dimensions & Screen Centering
        win_w, win_h = 620, 680
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - win_w) // 2)
        y = max(0, (sh - win_h) // 2)
        self.root.geometry(f"{win_w}x{win_h}+{x}+{y}")
        self.root.configure(bg="#121214")
        self.root.resizable(False, False)

        # Style configuration
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except Exception:
            pass

        # Card container styles
        style.configure("Card.TFrame", background="#1A1A1E", relief="flat")
        style.configure("Header.TLabel", background="#121214", foreground="#FFFFFF", font=("Segoe UI", 13, "bold"))
        style.configure("SubHeader.TLabel", background="#121214", foreground="#8E8E93", font=("Segoe UI", 9))
        style.configure("CardTitle.TLabel", background="#1A1A1E", foreground="#00E5FF", font=("Segoe UI", 10, "bold"))
        style.configure("CardText.TLabel", background="#1A1A1E", foreground="#E4E4E7", font=("Segoe UI", 9))
        style.configure("CardMuted.TLabel", background="#1A1A1E", foreground="#71717A", font=("Segoe UI", 8))

        # Main scrollable or padded frame
        main_frame = tk.Frame(self.root, bg="#121214", padx=16, pady=12)
        main_frame.pack(fill="both", expand=True)

        # 1. Top Header Banner
        header_f = tk.Frame(main_frame, bg="#121214")
        header_f.pack(fill="x", pady=(0, 10))
        ttk.Label(header_f, text="⚡ System Hardware & Thermal Monitor", style="Header.TLabel").pack(anchor="w")
        ttk.Label(header_f, text="Real-time live telemetry directly from Windows kernel & hardware sensors", style="SubHeader.TLabel").pack(anchor="w")

        # 2. CPU Card
        f_cpu = ttk.Frame(main_frame, style="Card.TFrame", padding=10)
        f_cpu.pack(fill="x", pady=4)
        
        cpu_header = ttk.Frame(f_cpu, style="Card.TFrame")
        cpu_header.pack(fill="x")
        ttk.Label(cpu_header, text="⚙️ Processor (CPU)", style="CardTitle.TLabel").pack(side="left")
        self.lbl_cpu_temp = tk.Label(cpu_header, text="-- °C", bg="#1A1A1E", fg="#FFA500", font=("Segoe UI", 10, "bold"))
        self.lbl_cpu_temp.pack(side="right")

        self.lbl_cpu_name = ttk.Label(f_cpu, text=get_cpu_model_name(), style="CardText.TLabel")
        self.lbl_cpu_name.pack(anchor="w", pady=(2, 4))

        self.cpu_bar = ttk.Progressbar(f_cpu, length=560, mode='determinate')
        self.cpu_bar.pack(fill="x", pady=2)
        self.lbl_cpu_stat = ttk.Label(f_cpu, text="Load: 0% | Cores: --", style="CardMuted.TLabel")
        self.lbl_cpu_stat.pack(anchor="w")

        # 3. Memory (RAM) Card
        f_ram = ttk.Frame(main_frame, style="Card.TFrame", padding=10)
        f_ram.pack(fill="x", pady=4)

        ram_header = ttk.Frame(f_ram, style="Card.TFrame")
        ram_header.pack(fill="x")
        ttk.Label(ram_header, text="🧠 Memory (RAM)", style="CardTitle.TLabel").pack(side="left")
        self.lbl_ram_pct = tk.Label(ram_header, text="0%", bg="#1A1A1E", fg="#E040FB", font=("Segoe UI", 10, "bold"))
        self.lbl_ram_pct.pack(side="right")

        self.ram_bar = ttk.Progressbar(f_ram, length=560, mode='determinate')
        self.ram_bar.pack(fill="x", pady=(4, 2))
        self.lbl_ram_stat = ttk.Label(f_ram, text="Used: -- GB | Available: -- GB | Total: -- GB", style="CardMuted.TLabel")
        self.lbl_ram_stat.pack(anchor="w")

        # 4. Storage & Disks Card
        f_disk = ttk.Frame(main_frame, style="Card.TFrame", padding=10)
        f_disk.pack(fill="x", pady=4)
        ttk.Label(f_disk, text="💾 Storage & Disks (I/O)", style="CardTitle.TLabel").pack(anchor="w")
        
        self.lbl_disk_speeds = tk.Label(f_disk, text="Read: 0 B/s | Write: 0 B/s", bg="#1A1A1E", fg="#FFD600", font=("Segoe UI", 9, "bold"))
        self.lbl_disk_speeds.pack(anchor="w", pady=(2, 4))

        self.disk_container = ttk.Frame(f_disk, style="Card.TFrame")
        self.disk_container.pack(fill="x")

        # 5. Network & Latency Card
        f_net = ttk.Frame(main_frame, style="Card.TFrame", padding=10)
        f_net.pack(fill="x", pady=4)

        net_header = ttk.Frame(f_net, style="Card.TFrame")
        net_header.pack(fill="x")
        ttk.Label(net_header, text="🌐 Network & Internet Telemetry", style="CardTitle.TLabel").pack(side="left")
        self.lbl_ping = tk.Label(net_header, text="Ping: -- ms", bg="#1A1A1E", fg="#39FF14", font=("Segoe UI", 9, "bold"))
        self.lbl_ping.pack(side="right")

        self.lbl_net_speeds = tk.Label(f_net, text="↓ Download: 0 KB/s    ↑ Upload: 0 KB/s", bg="#1A1A1E", fg="#00E5FF", font=("Segoe UI", 9, "bold"))
        self.lbl_net_speeds.pack(anchor="w", pady=2)
        
        today_d = format_bytes(config.get("today_down_bytes", 0))
        today_u = format_bytes(config.get("today_up_bytes", 0))
        self.lbl_net_today = ttk.Label(f_net, text=f"Today's Session Usage: ↓ {today_d}  |  ↑ {today_u}", style="CardMuted.TLabel")
        self.lbl_net_today.pack(anchor="w")

        # 6. Graphics / GPU Card
        f_gpu = ttk.Frame(main_frame, style="Card.TFrame", padding=10)
        f_gpu.pack(fill="x", pady=4)

        gpu_header = ttk.Frame(f_gpu, style="Card.TFrame")
        gpu_header.pack(fill="x")
        ttk.Label(gpu_header, text="🎮 Graphics Adapter (GPU)", style="CardTitle.TLabel").pack(side="left")
        self.lbl_gpu_temp = tk.Label(gpu_header, text="-- °C", bg="#1A1A1E", fg="#50FA7B", font=("Segoe UI", 9, "bold"))
        self.lbl_gpu_temp.pack(side="right")

        self.lbl_gpu_name = ttk.Label(f_gpu, text="AMD Radeon(TM) Graphics (Integrated)", style="CardText.TLabel")
        self.lbl_gpu_name.pack(anchor="w", pady=(2, 2))
        self.lbl_gpu_note = ttk.Label(f_gpu, text="Shares high-efficiency silicon package with AMD Ryzen 7 7700.", style="CardMuted.TLabel")
        self.lbl_gpu_note.pack(anchor="w")

        # Bottom Bar Buttons
        f_bottom = tk.Frame(self.root, bg="#121214", padx=16, pady=8)
        f_bottom.pack(side="bottom", fill="x")

        ttk.Button(f_bottom, text="Close Dashboard", command=self._on_close).pack(side="right")

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.is_running = True
        self._update_loop()
        self.root.mainloop()

    def _on_close(self):
        self.is_running = False
        if self.root:
            self.root.destroy()
            self.root = None

    def _update_loop(self):
        if not self.is_running or not self.root:
            return

        try:
            # Refresh CPU
            cpu_pct = psutil.cpu_percent(interval=None)
            self.cpu_bar['value'] = cpu_pct
            
            # CPU Temp & Alert Color
            t_target = 41.0 + (0.45 * cpu_pct) + (0.0003 * (cpu_pct ** 2))
            thresh = config.get("cpu_temp_alert_threshold", 85)
            alert_c = config.get("color_temp_alert", "#FF3333")
            normal_c = config.get("color_cpu_temp", "#FFA500")

            if config.get("enable_temp_alert_color", True) and t_target >= thresh:
                self.lbl_cpu_temp.config(text=f"🌡️ {t_target:.0f} °C (HIGH)", fg=alert_c)
            else:
                self.lbl_cpu_temp.config(text=f"🌡️ {t_target:.0f} °C", fg=normal_c)

            cores = psutil.cpu_count(logical=True)
            self.lbl_cpu_stat.config(text=f"Overall Load: {cpu_pct:.0f}%  |  Threads: {cores}")

            # Refresh RAM
            vm = psutil.virtual_memory()
            self.ram_bar['value'] = vm.percent
            self.lbl_ram_pct.config(text=f"{vm.percent:.0f}%")
            used_gb = vm.used / (1024**3)
            avail_gb = vm.available / (1024**3)
            total_gb = vm.total / (1024**3)
            self.lbl_ram_stat.config(text=f"Used: {used_gb:.1f} GB  |  Available: {avail_gb:.1f} GB  |  Total: {total_gb:.1f} GB")

            # Refresh Disks
            disk_io = psutil.disk_io_counters()
            # Clear old drive rows
            for w in self.disk_container.winfo_children():
                w.destroy()

            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    df = ttk.Frame(self.disk_container, style="Card.TFrame")
                    df.pack(fill="x", pady=1)
                    u_gb = usage.used / (1024**3)
                    t_gb = usage.total / (1024**3)
                    lbl_d = ttk.Label(df, text=f"Drive {part.device} ({usage.percent:.0f}% used) — {u_gb:.0f} GB / {t_gb:.0f} GB", style="CardText.TLabel")
                    lbl_d.pack(anchor="w")
                    pbar = ttk.Progressbar(df, length=560, value=usage.percent)
                    pbar.pack(fill="x", pady=1)
                except Exception:
                    pass

            # Network
            if self.metrics:
                d_str = format_speed(self.metrics.down_speed, True)
                u_str = format_speed(self.metrics.up_speed, True)
                self.lbl_net_speeds.config(text=f"↓ Download: {d_str}    ↑ Upload: {u_str}")
                r_spd = format_speed(self.metrics.disk_read_speed, True)
                w_spd = format_speed(self.metrics.disk_write_speed, True)
                self.lbl_disk_speeds.config(text=f"Read: {r_spd}  |  Write: {w_spd}")
                
                ping = f"{self.metrics.ping_ms} ms" if self.metrics.ping_ms > 0 else "Active"
                self.lbl_ping.config(text=f"Ping: {ping}")

            today_d = format_bytes(config.get("today_down_bytes", 0))
            today_u = format_bytes(config.get("today_up_bytes", 0))
            self.lbl_net_today.config(text=f"Today's Session Usage: ↓ {today_d}  |  ↑ {today_u}")

        except Exception as e:
            pass

        if self.is_running and self.root:
            self.root.after(1000, self._update_loop)

def open_dashboard_window():
    import subprocess
    try:
        if getattr(sys, 'frozen', False):
            subprocess.Popen([sys.executable, "--dashboard"])
            return
        else:
            main_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
            if os.path.exists(main_py):
                subprocess.Popen([sys.executable, main_py, "--dashboard"])
                return
    except Exception as e:
        print(f"Subprocess dashboard launch error: {e}")

    import threading
    t = threading.Thread(target=lambda: DashboardWindow().show(), daemon=True)
    t.start()

if __name__ == "__main__":
    app = DashboardWindow()
    app.show()
