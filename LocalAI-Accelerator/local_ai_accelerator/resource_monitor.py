"""
Resource Monitor - Track CPU/GPU usage in real-time
"""

import psutil
import torch
import threading
import time
from dataclasses import dataclass
from typing import Optional
from collections import deque
import logging

logger = logging.getLogger(__name__)


@dataclass
class ResourceStats:
    """Real-time resource statistics"""
    timestamp: float
    cpu_percent: float
    cpu_cores_used: int
    ram_percent: float
    ram_used_gb: float
    gpu_percent: Optional[float]
    gpu_memory_percent: Optional[float]
    gpu_memory_used_gb: Optional[float]
    cpu_temp: Optional[float]
    
    def __str__(self):
        info = f"""
📊 RESOURCE STATS
├─ CPU: {self.cpu_percent:.1f}% ({self.cpu_cores_used} cores)
├─ RAM: {self.ram_percent:.1f}% ({self.ram_used_gb:.1f}GB)
├─ GPU: {self.gpu_percent:.1f}% ({self.gpu_memory_used_gb:.1f}GB) if GPU else "N/A"
└─ Temp: {self.cpu_temp:.1f}°C if CPU temp else "N/A"
        """
        return info


class ResourceMonitor:
    """Monitors system resources in real-time"""
    
    def __init__(self, history_size: int = 100, update_interval: float = 1.0):
        self.history_size = history_size
        self.update_interval = update_interval
        self.stats_history = deque(maxlen=history_size)
        self.is_running = False
        self.monitor_thread = None
    
    def start(self):
        """Start monitoring in background thread"""
        if self.is_running:
            return
        
        self.is_running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop,
            daemon=True,
            name="ResourceMonitor"
        )
        self.monitor_thread.start()
        logger.info("Resource monitor started")
    
    def stop(self):
        """Stop monitoring"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Resource monitor stopped")
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.is_running:
            try:
                stats = self._get_stats()
                self.stats_history.append(stats)
            except Exception as e:
                logger.error(f"Error collecting stats: {e}")
            
            time.sleep(self.update_interval)
    
    def _get_stats(self) -> ResourceStats:
        """Get current resource statistics"""
        # CPU stats
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_count = psutil.cpu_count()
        per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)
        cores_used = sum(1 for c in per_cpu if c > 10)  # Count cores above 10%
        
        # RAM stats
        mem = psutil.virtual_memory()
        ram_percent = mem.percent
        ram_used_gb = mem.used / (1024**3)
        
        # GPU stats
        gpu_percent = None
        gpu_memory_percent = None
        gpu_memory_used_gb = None
        
        if torch.cuda.is_available():
            try:
                gpu_memory_used = torch.cuda.memory_allocated() / (1024**3)
                gpu_memory_total = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                gpu_memory_used_gb = gpu_memory_used
                gpu_memory_percent = (gpu_memory_used / gpu_memory_total) * 100
                gpu_percent = gpu_memory_percent
            except Exception as e:
                logger.debug(f"Could not get GPU stats: {e}")
        
        # CPU temperature
        cpu_temp = None
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                # Try to get average temperature
                all_temps = []
                for name, entries in temps.items():
                    for entry in entries:
                        all_temps.append(entry.current)
                if all_temps:
                    cpu_temp = sum(all_temps) / len(all_temps)
        except Exception:
            pass
        
        return ResourceStats(
            timestamp=time.time(),
            cpu_percent=cpu_percent,
            cpu_cores_used=cores_used,
            ram_percent=ram_percent,
            ram_used_gb=ram_used_gb,
            gpu_percent=gpu_percent,
            gpu_memory_percent=gpu_memory_percent,
            gpu_memory_used_gb=gpu_memory_used_gb,
            cpu_temp=cpu_temp,
        )
    
    def get_current_stats(self) -> ResourceStats:
        """Get current resource statistics"""
        return self._get_stats()
    
    def get_average_stats(self, last_n: int = 10) -> ResourceStats:
        """Get average stats from last N readings"""
        if len(self.stats_history) < last_n:
            readings = list(self.stats_history)
        else:
            readings = list(self.stats_history)[-last_n:]
        
        if not readings:
            return self.get_current_stats()
        
        avg_cpu = sum(s.cpu_percent for s in readings) / len(readings)
        avg_ram = sum(s.ram_percent for s in readings) / len(readings)
        avg_gpu = None
        avg_gpu_mem = None
        
        if readings[0].gpu_percent is not None:
            avg_gpu = sum(s.gpu_percent for s in readings) / len(readings)
            avg_gpu_mem = sum(s.gpu_memory_used_gb for s in readings) / len(readings)
        
        return ResourceStats(
            timestamp=time.time(),
            cpu_percent=avg_cpu,
            cpu_cores_used=readings[-1].cpu_cores_used,
            ram_percent=avg_ram,
            ram_used_gb=readings[-1].ram_used_gb,
            gpu_percent=avg_gpu,
            gpu_memory_percent=avg_gpu,
            gpu_memory_used_gb=avg_gpu_mem,
            cpu_temp=readings[-1].cpu_temp,
        )
    
    def is_resource_available(self, 
                             min_cpu_available: float = 20,
                             min_ram_available: float = 1,
                             min_gpu_available: float = 0.5) -> bool:
        """Check if system has enough resources"""
        stats = self.get_current_stats()
        
        cpu_available = 100 - stats.cpu_percent > min_cpu_available
        ram_available = stats.ram_percent < 85  # Less than 85% used
        
        if torch.cuda.is_available() and stats.gpu_percent is not None:
            gpu_available = stats.gpu_percent < 90  # Less than 90% used
            return cpu_available and ram_available and gpu_available
        
        return cpu_available and ram_available
    
    def print_stats(self):
        """Print current statistics"""
        stats = self.get_current_stats()
        print(stats)
    
    def export_history(self) -> list:
        """Export stats history as list"""
        return [
            {
                "timestamp": s.timestamp,
                "cpu_percent": s.cpu_percent,
                "cpu_cores_used": s.cpu_cores_used,
                "ram_percent": s.ram_percent,
                "ram_used_gb": s.ram_used_gb,
                "gpu_percent": s.gpu_percent,
                "gpu_memory_used_gb": s.gpu_memory_used_gb,
                "cpu_temp": s.cpu_temp,
            }
            for s in self.stats_history
        ]
