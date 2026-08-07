"""
Base class for AI providers.
Defines the interface all providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from enum import Enum


class AccessType(Enum):
    """How to access the AI provider"""
    API = "api"              # Direct API calls
    WEB = "web"              # Browser/web automation
    WEBSOCKET = "websocket"  # WebSocket connections
    HYBRID = "hybrid"        # Combined API + web fallback


class ProviderType(Enum):
    """Type of AI provider"""
    CHAT = "chat"           # Chat models
    COMPLETION = "completion"  # Text completion
    MULTIMODAL = "multimodal"  # Can handle images, audio, etc
    LOCAL = "local"         # Local/self-hosted


@dataclass
class ModelInfo:
    """Information about a specific model"""
    id: str                 # Model identifier
    name: str               # Human-readable name
    provider: str           # Provider name (e.g., 'claude', 'openai')
    type: ProviderType      # Type of model
    context_window: int = 4096  # Max context tokens
    max_output: int = 2048  # Max output tokens
    supports_vision: bool = False  # Can process images
    supports_audio: bool = False   # Can process audio
    cost_per_1k_input: float = 0.0    # Cost per 1K input tokens
    cost_per_1k_output: float = 0.0   # Cost per 1K output tokens
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProviderConfig:
    """Configuration for an AI provider"""
    provider_name: str      # Name of the provider (e.g., 'claude', 'openai')
    access_type: AccessType = AccessType.API  # How to access
    
    # API Configuration
    api_key: Optional[str] = None              # API key for authentication
    api_base_url: Optional[str] = None         # Custom API endpoint
    api_version: Optional[str] = None          # API version
    
    # Web Configuration (for web-based access)
    browser_type: str = "chromium"             # "chromium", "firefox", "webkit"
    headless: bool = True                      # Run browser headless
    timeout: int = 30                          # Timeout in seconds
    
    # Model Selection
    model_id: Optional[str] = None             # Specific model to use
    model_name: Optional[str] = None           # Human-readable model name
    
    # Generation Parameters
    temperature: float = 0.7                   # Sampling temperature
    max_tokens: int = 2048                     # Max output tokens
    top_p: float = 0.9                         # Nucleus sampling
    top_k: int = 40                            # Top-k sampling
    
    # Retry and Timeout
    max_retries: int = 3                       # Max retry attempts
    retry_delay: float = 1.0                   # Delay between retries in seconds
    request_timeout: int = 60                  # Request timeout in seconds
    
    # System Configuration
    system_prompt: Optional[str] = None        # System message
    temperature_override: Optional[float] = None  # Override temperature per request
    
    # Advanced
    use_cache: bool = True                     # Use response caching
    cache_ttl: int = 3600                      # Cache TTL in seconds
    enable_logging: bool = False                # Log all API calls
    proxy: Optional[str] = None                # HTTP/HTTPS proxy
    
    # Custom metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


class AIProvider(ABC):
    """
    Abstract base class for AI providers.
    All providers must implement this interface.
    """
    
    def __init__(self, config: ProviderConfig):
        """
        Initialize the provider with configuration.
        
        Args:
            config: ProviderConfig instance
        """
        self.config = config
        self.name = config.provider_name
        self.access_type = config.access_type
        self._initialized = False
        self._available_models = []
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the provider (authenticate, test connection, etc).
        
        Returns:
            bool: True if initialization successful
        """
        pass
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Generate text from the provider.
        
        Args:
            prompt: The input prompt
            system_prompt: Optional system message override
            temperature: Optional temperature override
            max_tokens: Optional max tokens override
            **kwargs: Provider-specific parameters
            
        Returns:
            str: Generated text
            
        Raises:
            ProviderError: If generation fails
        """
        pass
    
    @abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """
        Generate text with streaming (yields tokens as they arrive).
        
        Args:
            prompt: The input prompt
            system_prompt: Optional system message override
            **kwargs: Provider-specific parameters
            
        Yields:
            str: Text chunks as they arrive
        """
        pass
    
    @abstractmethod
    async def list_models(self) -> List[ModelInfo]:
        """
        List available models from this provider.
        
        Returns:
            List[ModelInfo]: List of available models
        """
        pass
    
    @abstractmethod
    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """
        Get information about a specific model.
        
        Args:
            model_id: Model identifier
            
        Returns:
            Optional[ModelInfo]: Model information or None if not found
        """
        pass
    
    async def close(self):
        """Clean up resources (e.g., close browser for web-based providers)"""
        pass
    
    def __repr__(self):
        return f"{self.__class__.__name__}(provider={self.name}, access={self.access_type.value})"


class ProviderError(Exception):
    """Base exception for provider errors"""
    pass


class ProviderAuthError(ProviderError):
    """Authentication/authorization error"""
    pass


class ProviderConnectionError(ProviderError):
    """Connection error"""
    pass


class ProviderModelNotFound(ProviderError):
    """Model not found"""
    pass


class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded"""
    pass
