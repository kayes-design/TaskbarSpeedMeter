# Taskbar Speed & Hardware Meter

An ultra-lightweight, high-performance native Windows Taskbar hardware monitor and telemetry widget that displays real-time **Network Speed, CPU Usage & Temperature, RAM Usage, and Disk I/O**.

Built entirely with pure Python and direct Win32 / GDI+ hardware layered window compositing — zero Electron bloat, zero heavy web frameworks, and minimal resource footprint.

---

## 🚀 Key Features

1. **Ultra-Lightweight & Native Performance:**
   - Pure Win32 GDI+ per-pixel hardware compositing (`UpdateLayeredWindow`).
   - Zero heavy framework dependencies (no Electron, no Qt).
   - Consumes only **~12–18 MB RAM** and **0.0% CPU** idle.
   - Native ClearType subpixel anti-aliased font rendering.

2. **Modular & Toggleable Telemetry:**
   - **⚡ Network Speed:** Real-time Download (↓) and Upload (↑) bandwidth (auto-scaling: B/s, KB/s, MB/s, GB/s or bps, Kbps, Mbps).
   - **⚙️ CPU Usage & Inline Temperature:** Real-time processor load percentage (`16%`) and core temperature (`CPU 48°C`).
   - **🧠 RAM Usage:** Memory utilization percentage (`74%`).
   - **💾 Disk I/O:** Hard drive / SSD Read and Write throughput (`R: X.X MB/s | W: X.X MB/s`).
   - **🎮 GPU Telemetry (Optional):** NVIDIA / discrete GPU usage and temperature monitoring (disabled by default for systems with integrated graphics).
   - Any metric can be toggled on/off individually; the widget auto-sizes dynamically.

3. **Taskbar Docking & Auto-Hide Sync:**
   - Docks seamlessly into the Windows 11 / 10 Taskbar directly beside the System Tray.
   - Automatically detects and adapts to Windows Dark and Light themes.
   - **Taskbar Auto-Hide Sync:** When the Windows taskbar auto-hides, the widget hides instantly; when the taskbar reappears on cursor hover, the widget smoothly reappears.
   - **Floating Desktop Mode:** Double-click or toggle from tray menu to drag and place the widget anywhere on any monitor.

4. **Interactive Settings & Customizer Dialog:**
   - **Layout & Column Spacing:** Live adjustable spacing slider from `0 px` (ultra-compact, seamless strip) to `16 px` (spacious).
   - **Background Styles:** Auto Match Taskbar, Acrylic Frosted Glass, Transparent (with anti-glare drop-shadow), Solid Dark (`#121216`), or fully custom HEX color.
   - **Custom Palette & Thermal Alerts:** Pick custom colors for each metric, or set a thermal threshold (e.g. 85°C) to alert with custom color indicators.
   - **Live Apply:** Changes are applied instantly to the running widget without requiring a restart.

5. **📊 Hardware Dashboard & Diagnostics:**
   - Dedicated hardware diagnostics window displaying processor details (e.g. AMD Ryzen 7 7700 8-Core), real-time per-core load bars, memory breakdown (GB used/free), partition disk space, I/O rates, and live network latency ping.

6. **🛠️ Extra Utilities:**
   - **Data Usage Tracker:** Tracks today's and this month's total download/upload consumption.
   - **Wi-Fi Password Revealer:** Quick access to saved Wi-Fi network keys.

---

## 🖱️ Controls & Shortcuts

| Action | Result |
|---|---|
| **Right Click** (Widget or Tray Icon) | Opens context menu to toggle modules, change units, adjust refresh rate, open Settings or Dashboard. |
| **Double Click** (Widget) | Toggles between Taskbar Docked mode and Floating Desktop mode. |
| **Left Click & Drag** (Floating Mode) | Move the widget anywhere across desktop displays. |

---

## 📦 Installation & Download

### Pre-Built Binaries
- **Installer:** `TaskbarSpeedMeter_Setup.exe` (1-click installer: installs to `%LOCALAPPDATA%\Programs`, creates Desktop and Start Menu shortcuts, configures auto-start, and integrates into Windows Add/Remove Programs).
- **Portable:** Standalone `TaskbarSpeedMeter.exe` requires no installation.

---

## 🛠️ Build from Source

### Prerequisites
- Windows 10 or Windows 11 (x64)
- Python 3.10+

### Steps
```bash
# 1. Clone the repository
git clone https://github.com/kayes-design/TaskbarSpeedMeter.git
cd TaskbarSpeedMeter

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run directly from source
python src/main.py

# 4. Build standalone executable
pyinstaller TaskbarSpeedMeter.spec

# 5. Build 1-click installer
pyinstaller TaskbarSpeedMeter_Setup.spec
```

---

## 📄 License
MIT License. Feel free to use, modify, and distribute.
