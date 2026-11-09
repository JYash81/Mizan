"""Safe local hardware detection service for CPU, RAM, OS, and GPU inspection."""

from __future__ import annotations

import logging
import os
import platform
import shutil
import subprocess
from typing import Any

from app.models.hardware import EvidenceType

logger = logging.getLogger(__name__)


def detect_cpu_info() -> tuple[str, int | None, int | None]:
    """Detect CPU model name, physical cores, and logical cores without external tools."""
    cpu_model = platform.processor() or "Unknown CPU"
    logical_cores = os.cpu_count() or 1
    physical_cores = logical_cores // 2 if logical_cores > 1 else 1

    # On Windows, read exact brand name from Registry
    if platform.system() == "Windows":
        try:
            import winreg

            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
            )
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            if name:
                cpu_model = str(name).strip()
        except Exception as exc:
            logger.debug("Windows registry CPU detection fallback: %s", exc)

    # On Linux, inspect /proc/cpuinfo
    elif platform.system() == "Linux" and os.path.exists("/proc/cpuinfo"):
        try:
            with open("/proc/cpuinfo", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("model name"):
                        cpu_model = line.split(":", 1)[1].strip()
                        break
        except Exception as exc:
            logger.debug("/proc/cpuinfo detection fallback: %s", exc)

    return cpu_model, physical_cores, logical_cores


def detect_memory_mb() -> tuple[int, int]:
    """Detect total system RAM and currently available RAM in Megabytes."""
    total_mb = 8192
    available_mb = 4096

    # 1. Try psutil if installed
    try:
        import psutil  # type: ignore[import-not-found]

        v = psutil.virtual_memory()
        return int(v.total // (1024 * 1024)), int(v.available // (1024 * 1024))
    except ImportError:
        pass

    # 2. Windows ctypes fallback
    if platform.system() == "Windows":
        try:
            import ctypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))  # type: ignore[attr-defined]
            total_mb = int(stat.ullTotalPhys // (1024 * 1024))
            available_mb = int(stat.ullAvailPhys // (1024 * 1024))
            return total_mb, available_mb
        except Exception as exc:
            logger.debug("Windows ctypes memory detection fallback: %s", exc)

    # 3. Linux /proc/meminfo fallback
    elif platform.system() == "Linux" and os.path.exists("/proc/meminfo"):
        try:
            mem_dict: dict[str, int] = {}
            with open("/proc/meminfo", encoding="utf-8") as f:
                for line in f:
                    parts = line.split(":")
                    if len(parts) == 2:
                        key = parts[0].strip()
                        val = parts[1].strip().split()[0]
                        mem_dict[key] = int(val)
            if "MemTotal" in mem_dict:
                total_mb = mem_dict["MemTotal"] // 1024
            if "MemAvailable" in mem_dict:
                available_mb = mem_dict["MemAvailable"] // 1024
            elif "MemFree" in mem_dict:
                available_mb = mem_dict["MemFree"] // 1024
            return total_mb, available_mb
        except Exception as exc:
            logger.debug("/proc/meminfo detection fallback: %s", exc)

    return total_mb, available_mb


def detect_nvidia_gpu() -> tuple[bool, dict[str, Any] | None, str | None]:
    """Check for NVIDIA GPU via safe bounded nvidia-smi execution without system modification."""
    n_smi = shutil.which("nvidia-smi")
    if not n_smi:
        return False, None, "nvidia-smi utility not found in PATH; no dedicated NVIDIA GPU detected"

    try:
        proc = subprocess.run(
            [
                n_smi,
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=True,
        )
        line = proc.stdout.strip().splitlines()[0]
        parts = [p.strip() for p in line.split(",")]
        gpu_name = parts[0] if len(parts) > 0 else "NVIDIA GPU"
        vram_mb = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        driver = parts[2] if len(parts) > 2 else "Unknown"

        return True, {"name": gpu_name, "vram_mb": vram_mb, "driver_version": driver}, None
    except Exception as exc:
        return False, None, f"nvidia-smi execution skipped or failed: {str(exc)}"


def inspect_local_hardware() -> dict[str, Any]:
    """Perform a comprehensive safe local inspection of CPU, RAM, OS, and GPU."""
    cpu_model, physical_cores, logical_cores = detect_cpu_info()
    total_ram_mb, available_ram_mb = detect_memory_mb()
    has_gpu, gpu_info, gpu_limitation = detect_nvidia_gpu()

    limitations: list[str] = [
        "Memory detection reports current OS load; ~3 GB is reserved for OS and runtime.",
    ]
    if gpu_limitation:
        limitations.append(gpu_limitation)

    return {
        "cpu_model": cpu_model,
        "physical_cores": physical_cores,
        "logical_cores": logical_cores,
        "system_ram_mb": total_ram_mb,
        "available_ram_mb": available_ram_mb,
        "os_name": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "has_nvidia_gpu": has_gpu,
        "gpu_info": gpu_info,
        "evidence_type": EvidenceType.MEASURED,
        "detection_limitations": "; ".join(limitations),
    }
