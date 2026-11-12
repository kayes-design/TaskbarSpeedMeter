import sys
import os
import ctypes
from ctypes import wintypes
import shutil
import winreg

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from win32_utils import user32, kernel32, ensure_interactive_desktop, set_autostart
from window import SpeedMeterWindow

ERROR_ALREADY_EXISTS = 183

def set_high_dpi():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass

def get_install_paths():
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    target_dir = os.path.join(local_app_data, "Programs", "TaskbarSpeedMeter")
    target_exe = os.path.join(target_dir, "TaskbarSpeedMeter.exe")
    
    desktop = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
    desktop_lnk = os.path.join(desktop, "Taskbar Speed Meter.lnk")
    
    app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
    start_menu = os.path.join(app_data, "Microsoft", "Windows", "Start Menu", "Programs")
    start_lnk = os.path.join(start_menu, "Taskbar Speed Meter.lnk")

    return target_dir, target_exe, desktop_lnk, start_lnk

def create_shortcut(target_exe, lnk_path, work_dir):
    try:
        vbs_script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{lnk_path}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target_exe}"
oLink.WorkingDirectory = "{work_dir}"
oLink.Description = "Taskbar Speed & Hardware Monitor"
oLink.IconLocation = "{target_exe},0"
oLink.Save
'''
        vbs_path = os.path.join(work_dir, "temp_sc.vbs")
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_script)
        os.system(f'cscript //nologo "{vbs_path}"')
        try:
            os.remove(vbs_path)
        except:
            pass
    except Exception as e:
        print(f"Shortcut creation error: {e}")

def install_app():
    target_dir, target_exe, desktop_lnk, start_lnk = get_install_paths()
    os.makedirs(target_dir, exist_ok=True)

    src_exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])

    # Copy binary
    try:
        if os.path.abspath(src_exe).lower() != os.path.abspath(target_exe).lower():
            shutil.copy2(src_exe, target_exe)
    except Exception as e:
        print(f"Copy error: {e}")

    # Set Startup Run
    set_autostart(True)

    # Create Shortcuts
    create_shortcut(target_exe, desktop_lnk, target_dir)
    create_shortcut(target_exe, start_lnk, target_dir)

    # Register in Windows Add/Remove Programs
    try:
        un_key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\TaskbarSpeedMeter"
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, un_key_path)
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "Taskbar Speed & Hardware Meter")
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "TaskbarSpeedMeter")
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, f'"{target_exe}",0')
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, target_dir)
        winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, f'"{target_exe}" --uninstall')
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Uninstall reg error: {e}")

    # Launch installed app if run as setup
    if os.path.abspath(src_exe).lower() != os.path.abspath(target_exe).lower():
        os.startfile(target_exe)
        user32.MessageBoxW(0, "Taskbar Speed Meter has been successfully installed!\nIt is now running in your taskbar.", "Installation Complete", 0x40 | 0x10000)

def uninstall_app():
    target_dir, target_exe, desktop_lnk, start_lnk = get_install_paths()

    res = user32.MessageBoxW(0, "Are you sure you want to uninstall Taskbar Speed Meter?", "Uninstall Taskbar Speed Meter", 0x24 | 0x10000)
    if res != 6: # IDYES
        return

    # Disable startup
    set_autostart(False)

    # Remove shortcuts
    for lnk in [desktop_lnk, start_lnk]:
        try:
            if os.path.exists(lnk):
                os.remove(lnk)
        except Exception:
            pass

    # Remove uninstall registry
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall\TaskbarSpeedMeter")
    except Exception:
        pass

    user32.MessageBoxW(0, "Taskbar Speed Meter has been uninstalled successfully.\n(Application files will be cleaned up on restart).", "Uninstalled", 0x40 | 0x10000)

def main():
    if "--install" in sys.argv:
        install_app()
        return

    if "--uninstall" in sys.argv:
        uninstall_app()
        return

    if "--settings" in sys.argv:
        set_high_dpi()
        ensure_interactive_desktop()
        from settings_dialog import SettingsDialog
        dlg = SettingsDialog()
        dlg.show()
        return

    if "--dashboard" in sys.argv:
        set_high_dpi()
        ensure_interactive_desktop()
        from dashboard_window import DashboardWindow
        dash = DashboardWindow()
        dash.show()
        return

    # Single instance mutex
    mutex_name = "Global\\TaskbarSpeedMeterSingleInstanceMutex"
    h_mutex = kernel32.CreateMutexW(None, False, mutex_name)
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        user32.MessageBoxW(0, "Taskbar Speed Meter is already running in your taskbar / system tray.", "Taskbar Speed Meter", 0x40 | 0x10000)
        return

    set_high_dpi()
    ensure_interactive_desktop()

    app = SpeedMeterWindow()
    app.run()

if __name__ == "__main__":
    main()
