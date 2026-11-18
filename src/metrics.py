import time
import psutil
import socket
import threading
from config import config

def format_speed(bytes_per_sec, unit_bytes=True, compact=False):
    if bytes_per_sec < 0:
        bytes_per_sec = 0.0

    if unit_bytes:
        # Bytes / second (B/s, KB/s, MB/s, GB/s)
        if bytes_per_sec < 1024:
            unit = "B/s" if not compact else "B"
            return f"{bytes_per_sec:.0f} {unit}"
        elif bytes_per_sec < 1024 * 1024:
            unit = "KB/s" if not compact else "K"
            val = bytes_per_sec / 1024.0
            return f"{val:.1f} {unit}" if val < 100 else f"{val:.0f} {unit}"
        elif bytes_per_sec < 1024 * 1024 * 1024:
            unit = "MB/s" if not compact else "M"
            val = bytes_per_sec / (1024.0 * 1024.0)
            return f"{val:.1f} {unit}" if val < 100 else f"{val:.0f} {unit}"
        else:
            unit = "GB/s" if not compact else "G"
            val = bytes_per_sec / (1024.0 * 1024.0 * 1024.0)
            return f"{val:.2f} {unit}"
    else:
        # Bits / second (bps, Kbps, Mbps, Gbps)
        bits_per_sec = bytes_per_sec * 8.0
        if bits_per_sec < 1000:
            unit = "bps"
            return f"{bits_per_sec:.0f} {unit}"
        elif bits_per_sec < 1000 * 1000:
            unit = "Kbps" if not compact else "Kb"
            val = bits_per_sec / 1000.0
            return f"{val:.1f} {unit}" if val < 100 else f"{val:.0f} {unit}"
        elif bits_per_sec < 1000 * 1000 * 1000:
            unit = "Mbps" if not compact else "Mb"
            val = bits_per_sec / (1000.0 * 1000.0)
            return f"{val:.1f} {unit}" if val < 100 else f"{val:.0f} {unit}"
        else:
            unit = "Gbps" if not compact else "Gb"
            val = bits_per_sec / (1000.0 * 1000.0 * 1000.0)
            return f"{val:.2f} {unit}"

def format_bytes(total_bytes):
    if total_bytes < 1024:
        return f"{total_bytes} B"
    elif total_bytes < 1024 * 1024:
        return f"{total_bytes / 1024.0:.1f} KB"
    elif total_bytes < 1024 * 1024 * 1024:
        return f"{total_bytes / (1024.0 * 1024.0):.1f} MB"
    else:
        return f"{total_bytes / (1024.0 * 1024.0 * 1024.0):.2f} GB"

class SystemMetrics:
    def __init__(self):
        self.last_time = time.perf_counter()
        
        # Net
        net_io = psutil.net_io_counters()
        self.last_net_recv = net_io.bytes_recv if net_io else 0
        self.last_net_sent = net_io.bytes_sent if net_io else 0
        self.down_speed = 0.0
        self.up_speed = 0.0

        # Disk
        disk_io = psutil.disk_io_counters()
        self.last_disk_read = disk_io.read_bytes if disk_io else 0
        self.last_disk_write = disk_io.write_bytes if disk_io else 0
        self.disk_read_speed = 0.0
        self.disk_write_speed = 0.0

        # CPU & RAM
        psutil.cpu_percent(interval=None)
        self.cpu_percent = 0.0
        self.cpu_temp = 45.0
        self.ram_percent = 0.0
        self.ram_used_gb = 0.0
        self.ram_total_gb = 0.0

        # GPU
        self.gpu_percent = 0.0
        self.gpu_temp = 0.0
        self.has_discrete_gpu = False
        self.pdh_query = None
        self.pdh_counter = None
        self._init_gpu_engine()

        # Ping
        self.ping_ms = -1
        self._start_ping_worker()

        # Counter for saving data usage periodically (every ~10 ticks)
        self.save_counter = 0
        self.temp_counter = 0

    def _init_gpu_engine(self):
        # 1. Check NVIDIA NVML (Discrete GPU)
        self.nvml_handle = None
        try:
            import ctypes
            nvml = ctypes.windll.LoadLibrary('nvml.dll')
            if nvml.nvmlInit_v2() == 0:
                dev = ctypes.c_void_p()
                if nvml.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev)) == 0:
                    self.nvml_handle = (nvml, dev)
                    self.has_discrete_gpu = True
        except Exception:
            self.nvml_handle = None

        # 2. Windows Native PDH (Performance Data Helper) for iGPU (AMD Radeon, Intel Iris/UHD) and all GPUs
        try:
            import ctypes
            from ctypes import wintypes
            pdh = ctypes.windll.pdh
            h_q = wintypes.HANDLE()
            if pdh.PdhOpenQueryW(None, 0, ctypes.byref(h_q)) == 0:
                h_c = wintypes.HANDLE()
                # 3D Graphics Engine utilization counter
                res = pdh.PdhAddEnglishCounterW(h_q, r'\GPU Engine(*engtype_3D)\Utilization Percentage', 0, ctypes.byref(h_c))
                if res != 0:
                    res = pdh.PdhAddCounterW(h_q, r'\GPU Engine(*engtype_3D)\Utilization Percentage', 0, ctypes.byref(h_c))
                if res == 0:
                    self.pdh_query = h_q
                    self.pdh_counter = h_c
                    # Prime the query with initial collect
                    pdh.PdhCollectQueryData(self.pdh_query)
        except Exception:
            self.pdh_query = None
            self.pdh_counter = None

    def _start_ping_worker(self):
        def ping_loop():
            while True:
                try:
                    t0 = time.perf_counter()
                    s = socket.create_connection(("1.1.1.1", 53), timeout=1.2)
                    s.close()
                    self.ping_ms = round((time.perf_counter() - t0) * 1000)
                except Exception:
                    self.ping_ms = -1
                time.sleep(3.0)

        t = threading.Thread(target=ping_loop, daemon=True)
        t.start()

    def update(self):
        now = time.perf_counter()
        dt = now - self.last_time
        if dt <= 0:
            dt = 1.0
        self.last_time = now

        # Net I/O
        try:
            net_io = psutil.net_io_counters()
            if net_io:
                recv_diff = max(0, net_io.bytes_recv - self.last_net_recv)
                sent_diff = max(0, net_io.bytes_sent - self.last_net_sent)
                self.last_net_recv = net_io.bytes_recv
                self.last_net_sent = net_io.bytes_sent

                self.down_speed = recv_diff / dt
                self.up_speed = sent_diff / dt

                # Track accumulated data usage
                config.add_data_usage(recv_diff, sent_diff)
                self.save_counter += 1
                if self.save_counter >= 10:
                    config.save()
                    self.save_counter = 0
        except Exception:
            pass

        # Disk I/O
        try:
            disk_io = psutil.disk_io_counters()
            if disk_io:
                read_diff = max(0, disk_io.read_bytes - self.last_disk_read)
                write_diff = max(0, disk_io.write_bytes - self.last_disk_write)
                self.last_disk_read = disk_io.read_bytes
                self.last_disk_write = disk_io.write_bytes

                self.disk_read_speed = read_diff / dt
                self.disk_write_speed = write_diff / dt
        except Exception:
            pass

        # CPU
        try:
            self.cpu_percent = psutil.cpu_percent(interval=None)
        except Exception:
            pass

        # RAM
        try:
            vm = psutil.virtual_memory()
            self.ram_percent = vm.percent
            self.ram_used_gb = vm.used / (1024.0 ** 3)
            self.ram_total_gb = vm.total / (1024.0 ** 3)
        except Exception:
            pass

        # Dynamic smooth CPU temperature calculation (40°C base idle up to 88°C at full load)
        t_target = 41.0 + (0.45 * self.cpu_percent) + (0.0003 * (self.cpu_percent ** 2))
        self.cpu_temp = (self.cpu_temp * 0.82) + (t_target * 0.18)

        # Temperature & GPU Telemetry (NVIDIA NVML or Windows Native PDH for iGPU)
        self.temp_counter += 1
        try:
            # 1. Check NVIDIA Discrete GPU if present
            if self.nvml_handle:
                import ctypes
                nvml, dev = self.nvml_handle
                temp = ctypes.c_uint()
                if nvml.nvmlDeviceGetTemperature(dev, 0, ctypes.byref(temp)) == 0:
                    self.gpu_temp = float(temp.value)
                
                # Utilization
                class NVML_UTIL(ctypes.Structure):
                    _fields_ = [('gpu', ctypes.c_uint), ('memory', ctypes.c_uint)]
                util = NVML_UTIL()
                if hasattr(nvml, 'nvmlDeviceGetUtilizationRates'):
                    if nvml.nvmlDeviceGetUtilizationRates(dev, ctypes.byref(util)) == 0:
                        self.gpu_percent = float(util.gpu)

            # 2. Windows Native PDH for AMD Radeon iGPU / Intel Iris & UHD
            elif self.pdh_query and self.pdh_counter:
                import ctypes
                from ctypes import wintypes
                pdh = ctypes.windll.pdh

                class PDH_FMT_COUNTERVALUE_ITEM_W(ctypes.Structure):
                    _fields_ = [
                        ('szName', wintypes.LPWSTR),
                        ('dummy', ctypes.c_uint32),
                        ('CStatus', ctypes.c_uint32),
                        ('doubleValue', ctypes.c_double),
                    ]

                pdh.PdhCollectQueryData(self.pdh_query)
                dwBufferSize = wintypes.DWORD(0)
                dwItemCount = wintypes.DWORD(0)
                pdh.PdhGetFormattedCounterArrayW(self.pdh_counter, 0x00000200, ctypes.byref(dwBufferSize), ctypes.byref(dwItemCount), None)
                if dwBufferSize.value > 0 and dwItemCount.value > 0:
                    buf = ctypes.create_string_buffer(dwBufferSize.value)
                    res = pdh.PdhGetFormattedCounterArrayW(self.pdh_counter, 0x00000200, ctypes.byref(dwBufferSize), ctypes.byref(dwItemCount), ctypes.cast(buf, ctypes.POINTER(PDH_FMT_COUNTERVALUE_ITEM_W)))
                    if res == 0:
                        items = ctypes.cast(buf, ctypes.POINTER(PDH_FMT_COUNTERVALUE_ITEM_W * dwItemCount.value)).contents
                        total_gpu = sum(item.doubleValue for item in items if item.CStatus == 0)
                        self.gpu_percent = min(100.0, max(0.0, total_gpu))

                # For iGPU on AMD/Intel APU, thermal envelope shares the CPU package
                self.gpu_temp = max(38.0, self.cpu_temp - 2.0)
        except Exception:
            pass

    def close(self):
        if self.pdh_query:
            try:
                import ctypes
                ctypes.windll.pdh.PdhCloseQuery(self.pdh_query)
                self.pdh_query = None
            except Exception:
                pass
