"""
Anthropic Claude Provider
Supports both API-based and web-based access to Claude models.
"""

import os
import aiohttp
import asyncio
from typing import List, Optional
from .base import (
    AIProvider, ProviderConfig, ModelInfo, ProviderType,
    ProviderError, ProviderAuthError, ProviderConnectionError
)
from .registry import register_provider


class AnthropicProvider(AIProvider):
    """Anthropic Claude AI Provider"""
    
    # Available Claude models
    AVAILABLE_MODELS = {
        'claude-opus-4-6': ModelInfo(
            id='claude-opus-4-6',
            name='Claude Opus 4.6',
            provider='anthropic',
            type=ProviderType.CHAT,
            context_window=200000,
            max_output=4096,
            supports_vision=True,
            supports_audio=False,
            cost_per_1k_input=0.015,
            cost_per_1k_output=0.075,
        ),
        'claude-sonnet-4-6': ModelInfo(
            id='claude-sonnet-4-6',
            name='Claude Sonnet 4.6',
            provider='anthropic',
            type=ProviderType.CHAT,
            context_window=200000,
            max_output=4096,
            supports_vision=True,
            supports_audio=False,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
        ),
        'claude-haiku-4-5': ModelInfo(
            id='claude-haiku-4-5',
            name='Claude Haiku 4.5',
            provider='anthropic',
            type=ProviderType.CHAT,
            context_window=200000,
            max_output=4096,
            supports_vision=True,
            supports_audio=False,
            cost_per_1k_input=0.0008,
            cost_per_1k_output=0.004,
        ),
    }
    
    API_BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2024-06-15"
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.client = None
        self.api_key = config.api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model_id = config.model_id or 'claude-opus-4-6'
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        """Initialize the provider and test authentication"""
        if not self.api_key:
            raise ProviderAuthError(
                "API key required. Set ANTHROPIC_API_KEY or pass api_key parameter"
            )
        
        try:
            # Create session
            self.session = aiohttp.ClientSession()
            
            # Verify API key by making a test call
            await self._test_connection()
            self._initialized = True
            return True
        except Exception as e:
            raise ProviderAuthError(f"Failed to authenticate with Anthropic: {str(e)}")
    
    async def _test_connection(self) -> None:
        """Test connection to Claude API"""
        if not self.session:
            return
        
        headers = {
            'x-api-key': self.api_key,
            'anthropic-version': self.API_VERSION,
            'content-type': 'application/json',
        }
        
        payload = {
            'model': self.model_id,
            'max_tokens': 100,
            'messages': [{'role': 'user', 'content': 'Hi'}]
        }
        
        async with self.session.post(
            f'{self.API_BASE_URL}/messages',
            headers=headers,
            json=payload
        ) as resp:
            if resp.status == 401:
                raise ProviderAuthError("Invalid API key")
            elif resp.status != 200:
                raise ProviderConnectionError(f"API returned status {resp.status}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate text using Claude API"""
        if not self._initialized:
            await self.initialize()
        
        if not self.session:
            raise ProviderConnectionError("Provider not initialized")
        
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens
        
        headers = {
            'x-api-key': self.api_key,
            'anthropic-version': self.API_VERSION,
            'content-type': 'application/json',
        }
        
        payload = {
            'model': self.model_id,
            'max_tokens': max_tok,
            'temperature': temp,
            'messages': [{'role': 'user', 'content': prompt}]
        }
        
        if system_prompt:
            payload['system'] = system_prompt
        elif self.config.system_prompt:
            payload['system'] = self.config.system_prompt
        
        try:
            async with self.session.post(
                f'{self.API_BASE_URL}/messages',
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.request_timeout)
            ) as resp:
                if resp.status == 429:
                    raise ProviderError("Rate limit exceeded")
                elif resp.status != 200:
                    raise ProviderError(f"API error: {resp.status}")
                
                data = await resp.json()
                return data['content'][0]['text']
        except asyncio.TimeoutError:
            raise ProviderConnectionError("Request timeout")
    
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """Stream text generation from Claude"""
        if not self._initialized:
            await self.initialize()
        
        if not self.session:
            raise ProviderConnectionError("Provider not initialized")
        
        headers = {
            'x-api-key': self.api_key,
            'anthropic-version': self.API_VERSION,
            'content-type': 'application/json',
        }
        
        payload = {
            'model': self.model_id,
            'max_tokens': self.config.max_tokens,
            'temperature': self.config.temperature,
            'stream': True,
            'messages': [{'role': 'user', 'content': prompt}]
        }
        
        if system_prompt:
            payload['system'] = system_prompt
        elif self.config.system_prompt:
            payload['system'] = self.config.system_prompt
        
        try:
            async with self.session.post(
                f'{self.API_BASE_URL}/messages',
                headers=headers,
                json=payload,
            ) as resp:
                if resp.status != 200:
                    raise ProviderError(f"API error: {resp.status}")
                
                async for line in resp.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            try:
                                import json
                                event = json.loads(line_str[6:])
                                if 'delta' in event and 'text' in event['delta']:
                                    yield event['delta']['text']
                            except:
                                pass
        except asyncio.TimeoutError:
            raise ProviderConnectionError("Request timeout")
    
    async def list_models(self) -> List[ModelInfo]:
        """List available Claude models"""
        return list(self.AVAILABLE_MODELS.values())
    
    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model"""
        return self.AVAILABLE_MODELS.get(model_id)
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()


# Register the provider
register_provider('claude', AnthropicProvider)
register_provider('anthropic', AnthropicProvider)
