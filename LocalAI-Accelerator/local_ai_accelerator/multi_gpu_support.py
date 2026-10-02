"""
Multi-GPU Support - Inspired by TensorRT-LLM
Tensor parallelism and pipeline parallelism for distributed inference
"""

import torch
import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ParallelismType(Enum):
    """Types of parallelism"""
    TENSOR = "tensor"
    PIPELINE = "pipeline"
    HYBRID = "hybrid"


@dataclass
class GPUConfig:
    """Configuration for a GPU"""
    device_id: int
    device_name: str
    total_memory_gb: float
    compute_capability: str
    supports_tf32: bool = True
    supports_bf16: bool = True


class GPUDetector:
    """Detect and enumerate available GPUs"""
    
    def __init__(self):
        self.gpus = []
        self.device_count = torch.cuda.device_count()
        self._detect_gpus()
    
    def _detect_gpus(self) -> None:
        """Detect all available GPUs"""
        for i in range(self.device_count):
            props = torch.cuda.get_device_properties(i)
            memory = torch.cuda.get_device_properties(i).total_memory / (1024**3)
            
            config = GPUConfig(
                device_id=i,
                device_name=props.name,
                total_memory_gb=memory,
                compute_capability=f"{props.major}.{props.minor}",
                supports_tf32=props.major >= 8,
                supports_bf16=props.major >= 8,
            )
            self.gpus.append(config)
            logger.info(f"GPU {i}: {config.device_name} ({memory:.1f}GB)")
    
    def get_optimal_config(self, num_gpus: Optional[int] = None) -> List[GPUConfig]:
        """Get optimal GPU configuration"""
        if num_gpus is None:
            num_gpus = self.device_count
        
        num_gpus = min(num_gpus, self.device_count)
        
        # Sort by memory
        sorted_gpus = sorted(self.gpus, key=lambda x: x.total_memory_gb, reverse=True)
        return sorted_gpus[:num_gpus]
    
    def print_gpu_info(self) -> None:
        """Print GPU information"""
        print(f"\n{'╔' + '═'*70 + '╗'}")
        print(f"║{'GPU CONFIGURATION':^70}║")
        print(f"{'╚' + '═'*70 + '╝'}")
        print(f"Total GPUs: {self.device_count}")
        
        for gpu in self.gpus:
            print(f"\nGPU {gpu.device_id}: {gpu.device_name}")
            print(f"  Memory: {gpu.total_memory_gb:.1f}GB")
            print(f"  Compute Capability: {gpu.compute_capability}")
            print(f"  TF32: {gpu.supports_tf32}, BF16: {gpu.supports_bf16}")


class TensorParallelism:
    """Distribute model across GPUs (tensor parallelism)"""
    
    def __init__(self, gpus: List[GPUConfig]):
        self.gpus = gpus
        self.num_gpus = len(gpus)
        logger.info(f"Initialized tensor parallelism with {self.num_gpus} GPUs")
    
    def split_model(self, model_size_gb: float) -> Dict:
        """Calculate model split across GPUs"""
        if model_size_gb / self.num_gpus > self.gpus[0].total_memory_gb * 0.9:
            raise RuntimeError("Model too large for tensor parallelism")
        
        per_gpu_size = model_size_gb / self.num_gpus
        
        return {
            'total_model_size_gb': model_size_gb,
            'per_gpu_size_gb': per_gpu_size,
            'num_gpus': self.num_gpus,
            'split_layers': list(range(0, model_size_gb // per_gpu_size)),
        }
    
    def get_communication_overhead(self) -> Dict:
        """Estimate communication overhead"""
        # Simplified calculation
        num_layers = 32  # Typical transformer
        hidden_size = 4096
        per_layer_comm = (2 * hidden_size * 4) / (1024**3)  # Simplified
        
        return {
            'all_reduce_overhead_ms': 10 * (self.num_gpus - 1),
            'per_layer_comm_gb': per_layer_comm,
            'total_comm_gb': per_layer_comm * num_layers * 2,
        }


class PipelineParallelism:
    """Distribute model stages across GPUs (pipeline parallelism)"""
    
    def __init__(self, gpus: List[GPUConfig], num_stages: int):
        self.gpus = gpus
        self.num_stages = min(num_stages, len(gpus))
        self.stages = self._create_stages()
        logger.info(f"Initialized pipeline parallelism with {self.num_stages} stages")
    
    def _create_stages(self) -> Dict:
        """Create pipeline stages"""
        stages = {}
        stages_per_gpu = self.num_stages // len(self.gpus)
        
        for i, stage in enumerate(range(self.num_stages)):
            gpu_id = stage // stages_per_gpu
            gpu_id = min(gpu_id, len(self.gpus) - 1)
            stages[stage] = {
                'gpu_id': gpu_id,
                'layers': [],  # Will be populated with model layers
            }
        
        return stages
    
    def get_pipeline_config(self) -> Dict:
        """Get pipeline configuration"""
        return {
            'num_stages': self.num_stages,
            'stages': self.stages,
            'bubble_overhead_percent': (self.num_stages - 1) / self.num_stages * 100,
        }


class HybridParallelism:
    """Combine tensor and pipeline parallelism"""
    
    def __init__(self, gpus: List[GPUConfig], 
                 tensor_parallel_size: int = 2,
                 pipeline_parallel_size: int = 2):
        self.gpus = gpus
        self.tensor_parallel_size = tensor_parallel_size
        self.pipeline_parallel_size = pipeline_parallel_size
        
        if tensor_parallel_size * pipeline_parallel_size > len(gpus):
            raise ValueError("Not enough GPUs for requested parallelism")
        
        self.tensor_parallel = TensorParallelism(
            gpus[:tensor_parallel_size]
        )
        self.pipeline_parallel = PipelineParallelism(
            gpus, pipeline_parallel_size
        )
        
        logger.info(f"Initialized hybrid parallelism: "
                   f"tensor={tensor_parallel_size}, pipeline={pipeline_parallel_size}")
    
    def get_config(self) -> Dict:
        """Get hybrid parallelism configuration"""
        return {
            'tensor_parallel_size': self.tensor_parallel_size,
            'pipeline_parallel_size': self.pipeline_parallel_size,
            'total_gpus': len(self.gpus),
            'tensor_config': self.tensor_parallel.split_model(7.0),
            'pipeline_config': self.pipeline_parallel.get_pipeline_config(),
        }


class DistributedInferenceEngine:
    """Main engine for distributed inference"""
    
    def __init__(self, num_gpus: Optional[int] = None,
                 parallelism_type: ParallelismType = ParallelismType.TENSOR):
        self.detector = GPUDetector()
        self.gpus = self.detector.get_optimal_config(num_gpus)
        self.parallelism_type = parallelism_type
        
        if parallelism_type == ParallelismType.TENSOR:
            self.parallelism = TensorParallelism(self.gpus)
        elif parallelism_type == ParallelismType.PIPELINE:
            self.parallelism = PipelineParallelism(self.gpus, len(self.gpus))
        else:  # HYBRID
            self.parallelism = HybridParallelism(
                self.gpus,
                tensor_parallel_size=2,
                pipeline_parallel_size=len(self.gpus) // 2
            )
        
        logger.info(f"Initialized distributed engine with {parallelism_type.value} "
                   f"parallelism using {len(self.gpus)} GPUs")
    
    def get_config(self) -> Dict:
        """Get current configuration"""
        return {
            'gpus': [
                {
                    'id': gpu.device_id,
                    'name': gpu.device_name,
                    'memory_gb': gpu.total_memory_gb,
                }
                for gpu in self.gpus
            ],
            'parallelism_type': self.parallelism_type.value,
            'parallelism_config': (
                self.parallelism.split_model(7.0) 
                if isinstance(self.parallelism, TensorParallelism)
                else self.parallelism.get_config()
            ),
        }
    
    def estimate_throughput(self, model_size_gb: float, batch_size: int) -> Dict:
        """Estimate throughput with distributed inference"""
        # Simplified estimation
        base_throughput = 1000  # tokens/sec on single GPU
        
        if isinstance(self.parallelism, TensorParallelism):
            # Tensor parallelism improves throughput with communication cost
            speedup = len(self.gpus) * 0.95  # 95% efficiency
        else:
            # Pipeline parallelism has more overhead
            speedup = len(self.gpus) * 0.80  # 80% efficiency
        
        return {
            'estimated_throughput_tokens_per_sec': int(base_throughput * speedup),
            'batch_size': batch_size,
            'speedup_factor': speedup,
            'parallel_gpus': len(self.gpus),
        }
    
    def print_config(self) -> None:
        """Print configuration"""
        self.detector.print_gpu_info()
        
        config = self.get_config()
        print(f"\nParallelism Type: {self.parallelism_type.value.upper()}")
        print(f"Using {len(self.gpus)} GPUs")
        
        throughput = self.estimate_throughput(7.0, 4)
        print(f"Estimated Throughput: {throughput['estimated_throughput_tokens_per_sec']} tokens/sec")
        print(f"Speedup Factor: {throughput['speedup_factor']:.1f}x")
