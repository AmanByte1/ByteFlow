"""
System Profiler - Detect CPU/GPU capabilities and available resources
"""

import psutil
import torch
import numpy as np
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class SystemSpecs:
    """System specifications"""
    cpu_cores: int
    cpu_threads: int
    cpu_freq_ghz: float
    total_ram_gb: float
    available_ram_gb: float
    
    has_gpu: bool
    gpu_name: Optional[str]
    gpu_vram_gb: Optional[float]
    gpu_available_vram_gb: Optional[float]
    
    cuda_version: Optional[str]
    torch_version: str
    
    def __str__(self):
        info = f"""
╔═══════════════════════════════════════╗
║    SYSTEM SPECIFICATIONS              ║
╚═══════════════════════════════════════╝

CPU:
  Cores: {self.cpu_cores}
  Threads: {self.cpu_threads}
  Frequency: {self.cpu_freq_ghz:.2f} GHz
  RAM: {self.available_ram_gb:.1f}GB / {self.total_ram_gb:.1f}GB

GPU:
  Available: {'✅ Yes' if self.has_gpu else '❌ No'}
  {'Name: ' + self.gpu_name if self.gpu_name else ''}
  {'VRAM: ' + f'{self.gpu_available_vram_gb:.1f}GB / {self.gpu_vram_gb:.1f}GB' if self.has_gpu else ''}
  {'CUDA: ' + self.cuda_version if self.cuda_version else ''}

Environment:
  PyTorch: {self.torch_version}
        """
        return info


class SystemProfiler:
    """Profiles system capabilities for optimal model loading"""
    
    def __init__(self):
        self.specs = self._profile_system()
    
    def _profile_system(self) -> SystemSpecs:
        """Profile the entire system"""
        # CPU profiling
        cpu_cores = psutil.cpu_count(logical=False)
        cpu_threads = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq().current / 1000  # Convert to GHz
        
        # RAM profiling
        mem = psutil.virtual_memory()
        total_ram = mem.total / (1024**3)  # Convert to GB
        available_ram = mem.available / (1024**3)
        
        # GPU profiling
        has_gpu = torch.cuda.is_available()
        gpu_name = None
        gpu_vram = None
        gpu_available_vram = None
        cuda_version = None
        
        if has_gpu:
            try:
                gpu_name = torch.cuda.get_device_name(0)
                gpu_vram = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                gpu_available_vram = (torch.cuda.get_device_properties(0).total_memory - 
                                     torch.cuda.memory_allocated()) / (1024**3)
                cuda_version = torch.version.cuda
            except Exception as e:
                logger.warning(f"Failed to get GPU info: {e}")
        
        return SystemSpecs(
            cpu_cores=cpu_cores,
            cpu_threads=cpu_threads,
            cpu_freq_ghz=cpu_freq,
            total_ram_gb=total_ram,
            available_ram_gb=available_ram,
            has_gpu=has_gpu,
            gpu_name=gpu_name,
            gpu_vram_gb=gpu_vram,
            gpu_available_vram_gb=gpu_available_vram,
            cuda_version=cuda_version,
            torch_version=torch.__version__,
        )
    
    def get_specs(self) -> SystemSpecs:
        """Get current system specifications"""
        return self.specs
    
    def recommend_model_size(self) -> str:
        """Recommend model size based on available resources"""
        available_ram = self.specs.available_ram_gb
        available_vram = self.specs.gpu_available_vram_gb or 0
        total_available = available_ram + available_vram
        
        if total_available < 4:
            return "tiny"  # < 1B params (125M - 500M)
        elif total_available < 8:
            return "small"  # 1B - 3B params
        elif total_available < 16:
            return "medium"  # 3B - 7B params
        elif total_available < 24:
            return "large"  # 7B - 13B params
        else:
            return "xlarge"  # 13B+ params
    
    def recommend_batch_size(self) -> int:
        """Recommend batch size based on available VRAM"""
        if not self.specs.has_gpu:
            return 1
        
        available_vram = self.specs.gpu_available_vram_gb or 0
        
        if available_vram < 4:
            return 1
        elif available_vram < 8:
            return 2
        elif available_vram < 16:
            return 4
        elif available_vram < 24:
            return 8
        else:
            return 16
    
    def recommend_max_seq_length(self) -> int:
        """Recommend max sequence length based on available memory"""
        available_vram = self.specs.gpu_available_vram_gb or 0
        available_ram = self.specs.available_ram_gb
        
        if available_vram > 0:
            # With GPU
            if available_vram < 6:
                return 512
            elif available_vram < 12:
                return 1024
            elif available_vram < 24:
                return 2048
            else:
                return 4096
        else:
            # CPU only
            if available_ram < 8:
                return 256
            elif available_ram < 16:
                return 512
            else:
                return 1024
    
    def print_specs(self):
        """Print system specifications"""
        print(self.specs)
    
    def export_specs(self) -> dict:
        """Export specs as dictionary"""
        return {
            "cpu_cores": self.specs.cpu_cores,
            "cpu_threads": self.specs.cpu_threads,
            "cpu_freq_ghz": self.specs.cpu_freq_ghz,
            "total_ram_gb": self.specs.total_ram_gb,
            "available_ram_gb": self.specs.available_ram_gb,
            "has_gpu": self.specs.has_gpu,
            "gpu_name": self.specs.gpu_name,
            "gpu_vram_gb": self.specs.gpu_vram_gb,
            "gpu_available_vram_gb": self.specs.gpu_available_vram_gb,
            "cuda_version": self.specs.cuda_version,
            "torch_version": self.specs.torch_version,
            "recommended_model_size": self.recommend_model_size(),
            "recommended_batch_size": self.recommend_batch_size(),
            "recommended_max_seq_length": self.recommend_max_seq_length(),
        }
