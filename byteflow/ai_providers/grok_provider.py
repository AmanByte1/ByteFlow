"""
Grok Provider
Supports API-based access to X's Grok models (xAI).
"""

import os
import aiohttp
import asyncio
import json
from typing import List, Optional
from .base import (
    AIProvider, ProviderConfig, ModelInfo, ProviderType,
    ProviderError, ProviderAuthError, ProviderConnectionError
)
from .registry import register_provider


class GrokProvider(AIProvider):
    """Grok AI Provider - X's AI model"""
    
    AVAILABLE_MODELS = {
        'grok-1': ModelInfo(
            id='grok-1',
            name='Grok 1',
            provider='xai',
            type=ProviderType.CHAT,
            context_window=131072,  # 128K tokens
            max_output=4096,
            supports_vision=True,
            supports_audio=False,
            cost_per_1k_input=0.005,
            cost_per_1k_output=0.015,
        ),
        'grok-vision-beta': ModelInfo(
            id='grok-vision-beta',
            name='Grok Vision Beta',
            provider='xai',
            type=ProviderType.MULTIMODAL,
            context_window=131072,
            max_output=4096,
            supports_vision=True,
            supports_audio=False,
            cost_per_1k_input=0.005,
            cost_per_1k_output=0.015,
        ),
    }
    
    API_BASE_URL = "https://api.x.ai/v1"
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_key = config.api_key or os.getenv('XAI_API_KEY') or os.getenv('GROK_API_KEY')
        self.model_id = config.model_id or 'grok-1'
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        """Initialize the provider"""
        if not self.api_key:
            raise ProviderAuthError(
                "API key required. Set XAI_API_KEY or GROK_API_KEY or pass api_key parameter"
            )
        
        try:
            self.session = aiohttp.ClientSession()
            await self._test_connection()
            self._initialized = True
            return True
        except Exception as e:
            raise ProviderAuthError(f"Failed to authenticate with Grok: {str(e)}")
    
    async def _test_connection(self) -> None:
        """Test connection to Grok API"""
        if not self.session:
            return
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'model': self.model_id,
            'max_tokens': 10,
            'messages': [{'role': 'user', 'content': 'Hi'}]
        }
        
        async with self.session.post(
            f'{self.API_BASE_URL}/chat/completions',
            headers=headers,
            json=payload
        ) as resp:
            if resp.status == 401:
                raise ProviderAuthError("Invalid API key")
            elif resp.status != 200 and resp.status != 400:
                raise ProviderConnectionError(f"API returned status {resp.status}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate text using Grok API"""
        if not self._initialized:
            await self.initialize()
        
        if not self.session:
            raise ProviderConnectionError("Provider not initialized")
        
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        
        messages = []
        if system_prompt or self.config.system_prompt:
            messages.append({
                'role': 'system',
                'content': system_prompt or self.config.system_prompt
            })
        messages.append({'role': 'user', 'content': prompt})
        
        payload = {
            'model': self.model_id,
            'max_tokens': max_tok,
            'temperature': temp,
            'messages': messages,
        }
        
        try:
            async with self.session.post(
                f'{self.API_BASE_URL}/chat/completions',
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.request_timeout)
            ) as resp:
                if resp.status == 429:
                    raise ProviderError("Rate limit exceeded")
                elif resp.status != 200:
                    error_text = await resp.text()
                    raise ProviderError(f"API error: {resp.status} - {error_text}")
                
                data = await resp.json()
                return data['choices'][0]['message']['content']
        except asyncio.TimeoutError:
            raise ProviderConnectionError("Request timeout")
    
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """Stream text generation from Grok"""
        if not self._initialized:
            await self.initialize()
        
        if not self.session:
            raise ProviderConnectionError("Provider not initialized")
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
        
        messages = []
        if system_prompt or self.config.system_prompt:
            messages.append({
                'role': 'system',
                'content': system_prompt or self.config.system_prompt
            })
        messages.append({'role': 'user', 'content': prompt})
        
        payload = {
            'model': self.model_id,
            'max_tokens': self.config.max_tokens,
            'temperature': self.config.temperature,
            'stream': True,
            'messages': messages,
        }
        
        try:
            async with self.session.post(
                f'{self.API_BASE_URL}/chat/completions',
                headers=headers,
                json=payload,
            ) as resp:
                if resp.status != 200:
                    raise ProviderError(f"API error: {resp.status}")
                
                async for line in resp.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                if 'choices' in data and len(data['choices']) > 0:
                                    delta = data['choices'][0].get('delta', {})
                                    if 'content' in delta:
                                        yield delta['content']
                            except json.JSONDecodeError:
                                pass
        except asyncio.TimeoutError:
            raise ProviderConnectionError("Request timeout")
    
    async def list_models(self) -> List[ModelInfo]:
        """List available Grok models"""
        return list(self.AVAILABLE_MODELS.values())
    
    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model"""
        return self.AVAILABLE_MODELS.get(model_id)
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()


# Register the provider
register_provider('grok', GrokProvider)
register_provider('xai', GrokProvider)
