"""
AI Providers Module
==================

This module provides a unified interface to multiple AI providers.
Supports both API-based and web-based access to various AI models.

Supported Providers:
- Claude (Anthropic)
- ChatGPT (OpenAI)
- Gemini (Google)
- Grok (X)
- Ollama (Local)
- Custom Providers

Usage:
    from byteflow.ai_providers import get_provider, AIProvider
    
    # Using API
    provider = get_provider('claude', api_key='your-key')
    response = provider.generate("Hello!")
    
    # Using web interface
    provider = get_provider('chatgpt', access_type='web')
    response = provider.generate("Hello!")
"""

from .base import AIProvider, ProviderConfig, ModelInfo
from .registry import AIProviderRegistry, get_provider, register_provider
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider
from .google_provider import GoogleProvider
from .local_provider import OllamaProvider
from .grok_provider import GrokProvider

__all__ = [
    'AIProvider',
    'ProviderConfig', 
    'ModelInfo',
    'AIProviderRegistry',
    'get_provider',
    'register_provider',
    'AnthropicProvider',
    'OpenAIProvider',
    'GoogleProvider',
    'OllamaProvider',
    'GrokProvider',
]
