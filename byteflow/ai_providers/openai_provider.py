"""
OpenAI ChatGPT Provider
Supports both API-based and web-based access to ChatGPT models.
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


class OpenAIProvider(AIProvider):
    """OpenAI ChatGPT Provider"""
    
    AVAILABLE_MODELS = {
        'gpt-4-turbo': ModelInfo(
            id='gpt-4-turbo-preview',
            name='GPT-4 Turbo',
            provider='openai',
            type=ProviderType.MULTIMODAL,
            context_window=128000,
            max_output=4096,
            supports_vision=True,
            supports_audio=False,
            cost_per_1k_input=0.01,
            cost_per_1k_output=0.03,
        ),
        'gpt-4': ModelInfo(
            id='gpt-4',
            name='GPT-4',
            provider='openai',
            type=ProviderType.CHAT,
            context_window=8192,
            max_output=2048,
            supports_vision=True,
            supports_audio=False,
            cost_per_1k_input=0.03,
            cost_per_1k_output=0.06,
        ),
        'gpt-3.5-turbo': ModelInfo(
            id='gpt-3.5-turbo',
            name='GPT-3.5 Turbo',
            provider='openai',
            type=ProviderType.CHAT,
            context_window=16384,
            max_output=4096,
            supports_vision=False,
            supports_audio=False,
            cost_per_1k_input=0.0005,
            cost_per_1k_output=0.0015,
        ),
    }
    
    API_BASE_URL = "https://api.openai.com/v1"
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_key = config.api_key or os.getenv('OPENAI_API_KEY')
        self.model_id = config.model_id or 'gpt-4-turbo-preview'
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        """Initialize the provider"""
        if not self.api_key:
            raise ProviderAuthError(
                "API key required. Set OPENAI_API_KEY or pass api_key parameter"
            )
        
        try:
            self.session = aiohttp.ClientSession()
            await self._test_connection()
            self._initialized = True
            return True
        except Exception as e:
            raise ProviderAuthError(f"Failed to authenticate with OpenAI: {str(e)}")
    
    async def _test_connection(self) -> None:
        """Test connection to OpenAI API"""
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
        """Generate text using ChatGPT API"""
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
            'top_p': self.config.top_p,
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
        """Stream text generation from ChatGPT"""
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
        """List available ChatGPT models"""
        return list(self.AVAILABLE_MODELS.values())
    
    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model"""
        return self.AVAILABLE_MODELS.get(model_id)
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()


# Register the provider
register_provider('openai', OpenAIProvider)
register_provider('chatgpt', OpenAIProvider)
