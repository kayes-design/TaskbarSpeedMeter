import os
import sys
import shutil
import winreg
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

def install():
    res = user32.MessageBoxW(
        0,
        "Welcome to Taskbar Speed & Hardware Meter Setup!\n\n"
        "This will install the ultra-lightweight Taskbar Speed & Hardware Monitor to your PC.\n\n"
        "Do you want to proceed with the installation?",
        "Taskbar Speed Meter Setup",
        0x21 | 0x10000 # MB_OKCANCEL | MB_SETFOREGROUND
    )
    if res != 1: # IDOK
        return

    # Target directory: %LOCALAPPDATA%\Programs\TaskbarSpeedMeter
    local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    target_dir = os.path.join(local_app_data, "Programs", "TaskbarSpeedMeter")
    os.makedirs(target_dir, exist_ok=True)
    target_exe = os.path.join(target_dir, "TaskbarSpeedMeter.exe")

    # Source executable: embedded or adjacent
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    src_exe = os.path.join(base_dir, "TaskbarSpeedMeter.exe")
    if not os.path.exists(src_exe):
        # Look in dist folder if running in dev
        src_exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "dist", "TaskbarSpeedMeter.exe")

    if not os.path.exists(src_exe):
        user32.MessageBoxW(0, f"Error: Core application binary not found at:\n{src_exe}", "Setup Error", 0x10 | 0x10000)
        return

    # Kill any running instance before overwriting
    os.system("taskkill /f /im TaskbarSpeedMeter.exe >nul 2>&1")

    # Copy binary
    try:
        shutil.copy2(src_exe, target_exe)
    except Exception as e:
        user32.MessageBoxW(0, f"Error copying files: {e}", "Installation Error", 0x10 | 0x10000)
        return

    # Set Startup Run
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "TaskbarSpeedMeter", 0, winreg.REG_SZ, f'"{target_exe}"')
        winreg.CloseKey(key)
    except Exception as e:
        print(f"Startup reg error: {e}")

    # Create Desktop shortcut
    try:
        desktop = os.path.join(os.environ.get("USERPROFILE", os.path.expanduser("~")), "Desktop")
        desktop_lnk = os.path.join(desktop, "Taskbar Speed Meter.lnk")
        vbs_script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{desktop_lnk}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target_exe}"
oLink.WorkingDirectory = "{target_dir}"
oLink.Description = "Taskbar Speed & Hardware Monitor"
oLink.IconLocation = "{target_exe},0"
oLink.Save
'''
        vbs_path = os.path.join(target_dir, "temp_sc.vbs")
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_script)
        os.system(f'cscript //nologo "{vbs_path}"')
        try:
            os.remove(vbs_path)
        except:
            pass
    except Exception as e:
        print(f"Desktop shortcut error: {e}")

    # Create Start Menu shortcut
    try:
        app_data = os.environ.get("APPDATA", os.path.expanduser("~"))
        start_menu = os.path.join(app_data, "Microsoft", "Windows", "Start Menu", "Programs")
        start_lnk = os.path.join(start_menu, "Taskbar Speed Meter.lnk")
        vbs_script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "{start_lnk}"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "{target_exe}"
oLink.WorkingDirectory = "{target_dir}"
oLink.Description = "Taskbar Speed & Hardware Monitor"
oLink.IconLocation = "{target_exe},0"
oLink.Save
'''
        vbs_path = os.path.join(target_dir, "temp_sc2.vbs")
        with open(vbs_path, "w", encoding="utf-8") as f:
            f.write(vbs_script)
        os.system(f'cscript //nologo "{vbs_path}"')
        try:
            os.remove(vbs_path)
        except:
            pass
    except Exception as e:
        print(f"Start menu shortcut error: {e}")

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

    # Launch application
    os.startfile(target_exe)

    user32.MessageBoxW(
        0,
        "Installation Complete!\n\n"
        "Taskbar Speed Meter has been installed and is now active in your taskbar.\n\n"
        "• Right-click the widget or tray icon to customize metrics, units, and themes.\n"
        "• Double-click to toggle between Taskbar Docked and Floating mode.\n"
        "• It will automatically launch every time your computer starts.",
        "Taskbar Speed Meter",
        0x40 | 0x10000 # MB_ICONINFORMATION | MB_SETFOREGROUND
    )

if __name__ == "__main__":
    install()
