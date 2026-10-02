"""
Model Manager - Load/unload models intelligently based on available resources
"""

import torch
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ModelType(Enum):
    """Model types supported"""
    LLAMA = "llama"
    TRANSFORMERS = "transformers"
    OLLAMA = "ollama"
    GGUF = "gguf"
    CUSTOM = "custom"


@dataclass
class ModelConfig:
    """Model configuration"""
    name: str
    model_type: ModelType
    estimated_vram_gb: float
    estimated_ram_gb: float
    max_tokens: int = 2048
    batch_size: int = 1
    quantization: Optional[str] = None  # "int8", "int4", "fp16", "fp32"
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
    
    def __str__(self):
        return f"""
Model: {self.name}
  Type: {self.model_type.value}
  Estimated Memory: {self.estimated_vram_gb:.1f}GB (GPU) + {self.estimated_ram_gb:.1f}GB (RAM)
  Max Tokens: {self.max_tokens}
  Batch Size: {self.batch_size}
  Quantization: {self.quantization or 'None'}
  Device: {self.device}
        """


class ModelManager:
    """Manages model loading and unloading"""
    
    # Predefined model configs
    MODELS = {
        "phi-2": ModelConfig(
            name="phi-2",
            model_type=ModelType.TRANSFORMERS,
            estimated_vram_gb=4.5,
            estimated_ram_gb=2,
            max_tokens=2048,
            quantization="int8",
        ),
        "phi-3": ModelConfig(
            name="phi-3",
            model_type=ModelType.TRANSFORMERS,
            estimated_vram_gb=8,
            estimated_ram_gb=3,
            max_tokens=4096,
            quantization="fp16",
        ),
        "qwen-2.5-7b": ModelConfig(
            name="qwen-2.5-7b",
            model_type=ModelType.TRANSFORMERS,
            estimated_vram_gb=6,
            estimated_ram_gb=2,
            max_tokens=2048,
            quantization="int8",
        ),
        "qwen-2.5-14b": ModelConfig(
            name="qwen-2.5-14b",
            model_type=ModelType.TRANSFORMERS,
            estimated_vram_gb=12,
            estimated_ram_gb=4,
            max_tokens=4096,
            quantization="fp16",
        ),
        "llama2-7b": ModelConfig(
            name="llama2-7b",
            model_type=ModelType.LLAMA,
            estimated_vram_gb=6,
            estimated_ram_gb=2,
            max_tokens=2048,
        ),
        "llama2-13b": ModelConfig(
            name="llama2-13b",
            model_type=ModelType.LLAMA,
            estimated_vram_gb=12,
            estimated_ram_gb=4,
            max_tokens=4096,
        ),
        "mistral-7b": ModelConfig(
            name="mistral-7b",
            model_type=ModelType.TRANSFORMERS,
            estimated_vram_gb=5,
            estimated_ram_gb=2,
            max_tokens=3200,
            quantization="int8",
        ),
    }
    
    def __init__(self):
        self.loaded_models: Dict[str, Any] = {}
        self.model_configs: Dict[str, ModelConfig] = {}
    
    def register_model(self, config: ModelConfig) -> None:
        """Register a custom model configuration"""
        self.model_configs[config.name] = config
        logger.info(f"Registered model: {config.name}")
    
    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """Get configuration for a model"""
        if model_name in self.model_configs:
            return self.model_configs[model_name]
        elif model_name in self.MODELS:
            return self.MODELS[model_name]
        return None
    
    def can_load_model(self, config: ModelConfig, available_vram_gb: float, 
                       available_ram_gb: float) -> bool:
        """Check if model can be loaded with available resources"""
        if torch.cuda.is_available():
            return available_vram_gb >= config.estimated_vram_gb
        else:
            return available_ram_gb >= config.estimated_ram_gb
    
    def load_model(self, model_name: str, device: str = "cuda") -> bool:
        """Load a model (placeholder - actual implementation depends on framework)"""
        if model_name in self.loaded_models:
            logger.info(f"Model {model_name} already loaded")
            return True
        
        config = self.get_model_config(model_name)
        if not config:
            logger.error(f"Unknown model: {model_name}")
            return False
        
        try:
            config.device = device
            self.loaded_models[model_name] = {
                "config": config,
                "model": None,  # Placeholder for actual model
                "loaded": True,
                "device": device,
            }
            logger.info(f"Loaded model: {model_name} on {device}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            return False
    
    def unload_model(self, model_name: str) -> bool:
        """Unload a model and free resources"""
        if model_name not in self.loaded_models:
            logger.warning(f"Model {model_name} not loaded")
            return False
        
        try:
            # Clean up model
            model_info = self.loaded_models[model_name]
            if model_info.get("model"):
                del model_info["model"]
            
            del self.loaded_models[model_name]
            
            # Clear CUDA cache if using GPU
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info(f"Unloaded model: {model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to unload model {model_name}: {e}")
            return False
    
    def unload_all(self) -> None:
        """Unload all loaded models"""
        models_to_unload = list(self.loaded_models.keys())
        for model_name in models_to_unload:
            self.unload_model(model_name)
        
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    def get_loaded_models(self) -> Dict[str, Dict]:
        """Get information about loaded models"""
        return {
            name: {
                "model_name": info["config"].name,
                "device": info["device"],
                "model_type": info["config"].model_type.value,
                "estimated_vram_gb": info["config"].estimated_vram_gb,
            }
            for name, info in self.loaded_models.items()
        }
    
    def recommend_model_for_resources(self, available_vram_gb: float,
                                     available_ram_gb: float,
                                     max_latency_ms: int = 1000) -> Optional[str]:
        """Recommend best model based on available resources"""
        suitable_models = []
        
        for model_name, config in self.MODELS.items():
            if self.can_load_model(config, available_vram_gb, available_ram_gb):
                suitable_models.append((model_name, config))
        
        if not suitable_models:
            return None
        
        # Sort by model size (prefer larger models if resources allow)
        suitable_models.sort(key=lambda x: x[1].estimated_vram_gb, reverse=True)
        return suitable_models[0][0]
    
    def print_model_info(self, model_name: str) -> None:
        """Print information about a model"""
        config = self.get_model_config(model_name)
        if config:
            print(config)
        else:
            print(f"Unknown model: {model_name}")
    
    def export_model_list(self) -> list:
        """Export list of all available models"""
        models = []
        
        for model_name, config in self.MODELS.items():
            models.append({
                "name": config.name,
                "type": config.model_type.value,
                "estimated_vram_gb": config.estimated_vram_gb,
                "estimated_ram_gb": config.estimated_ram_gb,
                "max_tokens": config.max_tokens,
                "quantization": config.quantization,
            })
        
        for model_name, config in self.model_configs.items():
            if model_name not in self.MODELS:
                models.append({
                    "name": config.name,
                    "type": config.model_type.value,
                    "estimated_vram_gb": config.estimated_vram_gb,
                    "estimated_ram_gb": config.estimated_ram_gb,
                    "max_tokens": config.max_tokens,
                    "quantization": config.quantization,
                })
        
        return models
