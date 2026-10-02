"""
LocalAI Accelerator - Optimize local AI model inference with intelligent CPU/GPU management

Core Features:
    - System profiling (CPU/GPU detection)
    - Resource monitoring (real-time tracking)
    - Model management (load/unload)
    - Request optimization (queuing & prioritization)
    - Paged attention (vLLM-inspired)
    - Continuous batching (efficient request handling)
    - Multi-GPU support (tensor & pipeline parallelism)
    - Kernel fusion (CUDA optimization)

Usage:
    # Basic
    from local_ai_accelerator import LocalAIAccelerator
    accelerator = LocalAIAccelerator()
    response = accelerator.inference("What is AI?", "phi-2")
    
    # Advanced (with all optimizations)
    from local_ai_accelerator import AdvancedLocalAIAccelerator
    accelerator = AdvancedLocalAIAccelerator(num_gpus=2)
    response = accelerator.advanced_inference("Your prompt", "phi-2")
"""

__version__ = "2.0.0"
__author__ = "LocalAI Community"

# Core modules
from .system_profiler import SystemProfiler
from .model_manager import ModelManager
from .resource_monitor import ResourceMonitor
from .request_optimizer import RequestOptimizer
from .accelerator import LocalAIAccelerator

# Advanced modules (vLLM, SGLang, TensorRT-LLM inspired)
from .paged_attention import (
    PagedAttentionConfig,
    PagedAttentionOptimizer,
    PagedAttentionScheduler,
)
from .continuous_batching import (
    BatchConfig,
    ContinuousBatcher,
    DynamicBatchingScheduler,
    TokenBasedScheduler,
)
from .multi_gpu_support import (
    GPUDetector,
    TensorParallelism,
    PipelineParallelism,
    HybridParallelism,
    DistributedInferenceEngine,
    ParallelismType,
)
from .kernel_optimization import (
    KernelOptimizer,
    AttentionOptimizer,
    KernelFusionEngine,
    OptimizationProfile,
)
from .advanced_accelerator import AdvancedLocalAIAccelerator

# Framework bridges (vLLM, SGLang, TensorRT-LLM integration)
from .framework_bridges import (
    FrameworkBridge,
    FrameworkType,
    FrameworkConfig,
    vLLMBridge,
    SGLangBridge,
    TensorRTLLMBridge,
    FrameworkBridgeFactory,
    FrameworkComparator,
)

# ByteFlow integration
from .byteflow_integration import (
    AcceleratedByteFlowInference,
    ByteFlowAcceleratorPipeline,
    ByteFlowConfig,
)

__all__ = [
    # Core
    "SystemProfiler",
    "ModelManager",
    "ResourceMonitor",
    "RequestOptimizer",
    "LocalAIAccelerator",
    # Advanced
    "PagedAttentionConfig",
    "PagedAttentionOptimizer",
    "PagedAttentionScheduler",
    "BatchConfig",
    "ContinuousBatcher",
    "DynamicBatchingScheduler",
    "TokenBasedScheduler",
    "GPUDetector",
    "TensorParallelism",
    "PipelineParallelism",
    "HybridParallelism",
    "DistributedInferenceEngine",
    "ParallelismType",
    "KernelOptimizer",
    "AttentionOptimizer",
    "KernelFusionEngine",
    "OptimizationProfile",
    "AdvancedLocalAIAccelerator",
    # Framework Bridges
    "FrameworkBridge",
    "FrameworkType",
    "FrameworkConfig",
    "vLLMBridge",
    "SGLangBridge",
    "TensorRTLLMBridge",
    "FrameworkBridgeFactory",
    "FrameworkComparator",
    # ByteFlow Integration
    "AcceleratedByteFlowInference",
    "ByteFlowAcceleratorPipeline",
    "ByteFlowConfig",
]
