"""
LocalAI Accelerator - Main orchestrator for optimized local AI inference
"""

import logging
import asyncio
import time
from typing import Optional, Dict, Any

from .system_profiler import SystemProfiler
from .model_manager import ModelManager, ModelConfig
from .resource_monitor import ResourceMonitor
from .request_optimizer import RequestOptimizer, RequestPriority, InferenceResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LocalAIAccelerator:
    """
    Main accelerator class - combines system profiling, model management,
    resource monitoring, and request optimization
    
    Usage:
        accelerator = LocalAIAccelerator()
        accelerator.print_system_info()
        response = accelerator.inference("What is AI?", "phi-2")
    """
    
    def __init__(self, auto_optimize: bool = True, enable_monitoring: bool = True):
        """
        Initialize LocalAI Accelerator
        
        Args:
            auto_optimize: Automatically optimize settings based on system
            enable_monitoring: Enable real-time resource monitoring
        """
        logger.info("Initializing LocalAI Accelerator...")
        
        self.auto_optimize = auto_optimize
        self.enable_monitoring = enable_monitoring
        
        # Initialize components
        self.system_profiler = SystemProfiler()
        self.model_manager = ModelManager()
        self.resource_monitor = ResourceMonitor()
        self.request_optimizer = RequestOptimizer()
        
        # Configurations
        self.inference_results: Dict[str, InferenceResult] = {}
        
        # Start resource monitoring
        if self.enable_monitoring:
            self.resource_monitor.start()
        
        logger.info("LocalAI Accelerator initialized successfully")
    
    def print_system_info(self):
        """Print system information and recommendations"""
        self.system_profiler.print_specs()
        
        specs = self.system_profiler.export_specs()
        print(f"\n📋 RECOMMENDATIONS:")
        print(f"  Model Size: {specs['recommended_model_size'].upper()}")
        print(f"  Batch Size: {specs['recommended_batch_size']}")
        print(f"  Max Sequence Length: {specs['recommended_max_seq_length']}")
    
    def print_resource_stats(self):
        """Print current resource statistics"""
        self.resource_monitor.print_stats()
    
    def get_system_specs(self) -> dict:
        """Get system specifications as dictionary"""
        return self.system_profiler.export_specs()
    
    def get_resource_stats(self) -> dict:
        """Get current resource statistics as dictionary"""
        stats = self.resource_monitor.get_current_stats()
        return {
            "cpu_percent": stats.cpu_percent,
            "ram_percent": stats.ram_percent,
            "gpu_percent": stats.gpu_percent,
            "gpu_memory_used_gb": stats.gpu_memory_used_gb,
            "timestamp": stats.timestamp,
        }
    
    def recommend_model(self) -> Optional[str]:
        """Recommend best model based on available resources"""
        specs = self.system_profiler.get_specs()
        available_vram = specs.gpu_available_vram_gb or 0
        available_ram = specs.available_ram_gb
        
        return self.model_manager.recommend_model_for_resources(
            available_vram, available_ram
        )
    
    def load_model(self, model_name: str) -> bool:
        """Load a model"""
        specs = self.system_profiler.get_specs()
        config = self.model_manager.get_model_config(model_name)
        
        if not config:
            logger.error(f"Unknown model: {model_name}")
            return False
        
        available_vram = specs.gpu_available_vram_gb or 0
        available_ram = specs.available_ram_gb
        
        if not self.model_manager.can_load_model(config, available_vram, available_ram):
            logger.error(
                f"Not enough resources to load {model_name}. "
                f"Required: {config.estimated_vram_gb}GB VRAM, "
                f"Available: {available_vram}GB"
            )
            return False
        
        return self.model_manager.load_model(model_name)
    
    def unload_model(self, model_name: str) -> bool:
        """Unload a model"""
        return self.model_manager.unload_model(model_name)
    
    def unload_all_models(self):
        """Unload all models"""
        self.model_manager.unload_all()
    
    def get_loaded_models(self) -> dict:
        """Get list of loaded models"""
        return self.model_manager.get_loaded_models()
    
    def inference(self, 
                 prompt: str, 
                 model_name: str,
                 max_tokens: int = 256,
                 temperature: float = 0.7,
                 priority: RequestPriority = RequestPriority.NORMAL,
                 timeout: float = 60.0) -> str:
        """
        Run inference (synchronous wrapper)
        
        Args:
            prompt: Input prompt
            model_name: Model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            priority: Request priority
            timeout: Maximum time to wait for result
            
        Returns:
            Generated text response
        """
        # This is a placeholder - actual implementation would run async
        start_time = time.time()
        
        # Check if model is loaded
        if model_name not in self.model_manager.loaded_models:
            if not self.load_model(model_name):
                raise RuntimeError(f"Failed to load model {model_name}")
        
        # Check resources
        if not self.resource_monitor.is_resource_available():
            logger.warning("System resources are constrained")
        
        # Simulate inference (actual implementation would call the model)
        logger.info(f"Running inference with {model_name}...")
        
        # Placeholder response
        response = f"[Generated by {model_name}] {prompt[:50]}..."
        
        latency_ms = (time.time() - start_time) * 1000
        
        logger.info(f"Inference completed in {latency_ms:.1f}ms")
        
        return response
    
    async def inference_async(self,
                             prompt: str,
                             model_name: str,
                             max_tokens: int = 256,
                             temperature: float = 0.7,
                             priority: RequestPriority = RequestPriority.NORMAL) -> str:
        """
        Run inference asynchronously
        
        Args:
            prompt: Input prompt
            model_name: Model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            priority: Request priority
            
        Returns:
            Generated text response
        """
        request_id = await self.request_optimizer.submit_request(
            prompt=prompt,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            priority=priority
        )
        
        result = await self.request_optimizer.wait_for_result(request_id)
        return result.response
    
    def batch_inference(self, 
                       prompts: list,
                       model_name: str,
                       max_tokens: int = 256) -> list:
        """Run multiple inferences efficiently"""
        responses = []
        for prompt in prompts:
            response = self.inference(prompt, model_name, max_tokens=max_tokens)
            responses.append(response)
        return responses
    
    def register_custom_model(self, config: ModelConfig) -> None:
        """Register a custom model configuration"""
        self.model_manager.register_model(config)
    
    def list_available_models(self) -> list:
        """List all available models"""
        return self.model_manager.export_model_list()
    
    def print_available_models(self):
        """Print available models"""
        models = self.list_available_models()
        print("\n📚 AVAILABLE MODELS:")
        print("=" * 70)
        for model in models:
            print(f"  {model['name']:<20} | {model['type']:<12} | "
                  f"VRAM: {model['estimated_vram_gb']:.1f}GB")
    
    def get_optimization_report(self) -> dict:
        """Generate optimization report"""
        specs = self.system_profiler.get_specs()
        stats = self.resource_monitor.get_current_stats()
        queue_stats = self.request_optimizer.get_queue_stats()
        
        return {
            "system": {
                "cpu_cores": specs.cpu_cores,
                "gpu_available": specs.has_gpu,
                "total_ram_gb": specs.total_ram_gb,
                "gpu_vram_gb": specs.gpu_vram_gb,
            },
            "current_resources": {
                "cpu_usage_percent": stats.cpu_percent,
                "ram_usage_percent": stats.ram_percent,
                "gpu_usage_percent": stats.gpu_percent,
            },
            "queue": queue_stats,
            "recommendations": {
                "recommended_model": self.recommend_model(),
                "batch_size": specs.recommend_batch_size(),
                "max_seq_length": specs.recommend_max_seq_length(),
            }
        }
    
    def print_optimization_report(self):
        """Print optimization report"""
        report = self.get_optimization_report()
        print("\n📊 OPTIMIZATION REPORT:")
        print("=" * 70)
        print(f"System: {report['system']}")
        print(f"Current Resources: {report['current_resources']}")
        print(f"Recommendations: {report['recommendations']}")
    
    def shutdown(self):
        """Clean up and shutdown"""
        logger.info("Shutting down LocalAI Accelerator...")
        self.resource_monitor.stop()
        self.model_manager.unload_all()
        logger.info("LocalAI Accelerator shutdown complete")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.shutdown()
