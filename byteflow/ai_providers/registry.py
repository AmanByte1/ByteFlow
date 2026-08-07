"""
Provider registry for managing and retrieving AI providers.
"""

from typing import Dict, Type, Optional
from .base import AIProvider, ProviderConfig, AccessType


class AIProviderRegistry:
    """
    Registry for managing AI providers.
    Allows registration and retrieval of providers by name.
    """
    
    _providers: Dict[str, Type[AIProvider]] = {}
    _instances: Dict[str, AIProvider] = {}
    
    @classmethod
    def register(cls, name: str, provider_class: Type[AIProvider]):
        """
        Register a provider class.
        
        Args:
            name: Provider name (e.g., 'claude', 'openai')
            provider_class: Provider class
        """
        if name in cls._providers:
            print(f"Warning: Overwriting existing provider '{name}'")
        cls._providers[name] = provider_class
    
    @classmethod
    def get_provider_class(cls, name: str) -> Optional[Type[AIProvider]]:
        """
        Get a provider class by name.
        
        Args:
            name: Provider name
            
        Returns:
            Provider class or None if not found
        """
        return cls._providers.get(name.lower())
    
    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names"""
        return sorted(list(cls._providers.keys()))
    
    @classmethod
    def create_instance(
        cls,
        name: str,
        config: ProviderConfig,
        cache: bool = True
    ) -> Optional[AIProvider]:
        """
        Create a provider instance.
        
        Args:
            name: Provider name
            config: Provider configuration
            cache: Cache the instance (reuse on subsequent calls)
            
        Returns:
            Provider instance or None if not found
        """
        provider_class = cls.get_provider_class(name)
        if not provider_class:
            return None
        
        # Check cache
        cache_key = f"{name}_{config.access_type.value}"
        if cache and cache_key in cls._instances:
            return cls._instances[cache_key]
        
        # Create new instance
        instance = provider_class(config)
        if cache:
            cls._instances[cache_key] = instance
        
        return instance
    
    @classmethod
    def clear_cache(cls):
        """Clear the instance cache"""
        cls._instances.clear()


def register_provider(name: str, provider_class: Type[AIProvider]):
    """
    Register a provider class with the global registry.
    
    Args:
        name: Provider name
        provider_class: Provider class
    """
    AIProviderRegistry.register(name, provider_class)


def get_provider(
    name: str,
    access_type: str = "api",
    api_key: Optional[str] = None,
    model_id: Optional[str] = None,
    **kwargs
) -> Optional[AIProvider]:
    """
    Get or create a provider instance.
    
    Args:
        name: Provider name (e.g., 'claude', 'openai', 'gemini')
        access_type: Access type - "api", "web", "websocket", "hybrid"
        api_key: API key (if using API access)
        model_id: Specific model to use
        **kwargs: Additional configuration parameters
        
    Returns:
        Provider instance or None if not found
        
    Example:
        # Using Claude API
        provider = get_provider('claude', api_key='sk-...')
        
        # Using ChatGPT web interface
        provider = get_provider('openai', access_type='web', 
                              headless=True, browser_type='chromium')
        
        # Using local Ollama
        provider = get_provider('ollama', model_id='llama2')
    """
    try:
        access_type_enum = AccessType(access_type.lower())
    except ValueError:
        print(f"Invalid access type: {access_type}. Using 'api'")
        access_type_enum = AccessType.API
    
    config = ProviderConfig(
        provider_name=name,
        access_type=access_type_enum,
        api_key=api_key,
        model_id=model_id,
        **kwargs
    )
    
    return AIProviderRegistry.create_instance(name, config)


def list_providers() -> list[str]:
    """List all available providers"""
    return AIProviderRegistry.list_providers()
