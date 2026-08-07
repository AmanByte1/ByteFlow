"""
Local Ollama Provider
Supports local LLM models through Ollama.
"""

import os
import aiohttp
import asyncio
import json
from typing import List, Optional
from .base import (
    AIProvider, ProviderConfig, ModelInfo, ProviderType,
    ProviderError, ProviderConnectionError
)
from .registry import register_provider


class OllamaProvider(AIProvider):
    """Ollama Local Provider - Run LLMs locally"""
    
    AVAILABLE_MODELS = {
        'llama2': ModelInfo(
            id='llama2',
            name='Llama 2 7B',
            provider='ollama',
            type=ProviderType.CHAT,
            context_window=4096,
            max_output=2048,
            supports_vision=False,
            supports_audio=False,
        ),
        'llama2-uncensored': ModelInfo(
            id='llama2-uncensored',
            name='Llama 2 Uncensored',
            provider='ollama',
            type=ProviderType.CHAT,
            context_window=4096,
            max_output=2048,
            supports_vision=False,
            supports_audio=False,
        ),
        'mistral': ModelInfo(
            id='mistral',
            name='Mistral 7B',
            provider='ollama',
            type=ProviderType.CHAT,
            context_window=8192,
            max_output=2048,
            supports_vision=False,
            supports_audio=False,
        ),
        'neural-chat': ModelInfo(
            id='neural-chat',
            name='Neural Chat 7B',
            provider='ollama',
            type=ProviderType.CHAT,
            context_window=4096,
            max_output=2048,
            supports_vision=False,
            supports_audio=False,
        ),
        'dolphin-mixtral': ModelInfo(
            id='dolphin-mixtral',
            name='Dolphin Mixtral 8x7B',
            provider='ollama',
            type=ProviderType.CHAT,
            context_window=32000,
            max_output=4096,
            supports_vision=False,
            supports_audio=False,
        ),
    }
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.api_base_url or os.getenv('OLLAMA_API_URL', 'http://localhost:11434')
        self.model_id = config.model_id or 'llama2'
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        """Initialize the provider and test connection to Ollama"""
        try:
            self.session = aiohttp.ClientSession()
            await self._test_connection()
            self._initialized = True
            return True
        except Exception as e:
            raise ProviderConnectionError(
                f"Failed to connect to Ollama at {self.base_url}: {str(e)}"
            )
    
    async def _test_connection(self) -> None:
        """Test connection to Ollama server"""
        if not self.session:
            return
        
        try:
            async with self.session.get(
                f'{self.base_url}/api/tags',
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status != 200:
                    raise ProviderConnectionError(
                        f"Ollama server returned status {resp.status}"
                    )
        except asyncio.TimeoutError:
            raise ProviderConnectionError(
                "Could not connect to Ollama server. "
                "Make sure Ollama is running: ollama serve"
            )
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate text using Ollama"""
        if not self._initialized:
            await self.initialize()
        
        if not self.session:
            raise ProviderConnectionError("Provider not initialized")
        
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens
        
        # Build the prompt with system message if provided
        full_prompt = prompt
        if system_prompt or self.config.system_prompt:
            sys_msg = system_prompt or self.config.system_prompt
            full_prompt = f"[SYSTEM]\n{sys_msg}\n\n[USER]\n{prompt}"
        
        payload = {
            'model': self.model_id,
            'prompt': full_prompt,
            'stream': False,
            'options': {
                'temperature': temp,
                'num_predict': max_tok,
                'top_p': self.config.top_p,
            }
        }
        
        try:
            async with self.session.post(
                f'{self.base_url}/api/generate',
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.request_timeout)
            ) as resp:
                if resp.status != 200:
                    raise ProviderError(f"API error: {resp.status}")
                
                data = await resp.json()
                return data.get('response', '')
        except asyncio.TimeoutError:
            raise ProviderConnectionError("Request timeout")
    
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """Stream text generation from Ollama"""
        if not self._initialized:
            await self.initialize()
        
        if not self.session:
            raise ProviderConnectionError("Provider not initialized")
        
        # Build the prompt with system message if provided
        full_prompt = prompt
        if system_prompt or self.config.system_prompt:
            sys_msg = system_prompt or self.config.system_prompt
            full_prompt = f"[SYSTEM]\n{sys_msg}\n\n[USER]\n{prompt}"
        
        payload = {
            'model': self.model_id,
            'prompt': full_prompt,
            'stream': True,
            'options': {
                'temperature': self.config.temperature,
                'num_predict': self.config.max_tokens,
            }
        }
        
        try:
            async with self.session.post(
                f'{self.base_url}/api/generate',
                json=payload
            ) as resp:
                if resp.status != 200:
                    raise ProviderError(f"API error: {resp.status}")
                
                async for line in resp.content:
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8').strip())
                            if 'response' in data:
                                yield data['response']
                        except json.JSONDecodeError:
                            pass
        except asyncio.TimeoutError:
            raise ProviderConnectionError("Request timeout")
    
    async def list_models(self) -> List[ModelInfo]:
        """List available Ollama models"""
        if not self._initialized:
            await self.initialize()
        
        if not self.session:
            return list(self.AVAILABLE_MODELS.values())
        
        try:
            async with self.session.get(f'{self.base_url}/api/tags') as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = []
                    for model in data.get('models', []):
                        model_name = model['name'].split(':')[0]
                        if model_name in self.AVAILABLE_MODELS:
                            models.append(self.AVAILABLE_MODELS[model_name])
                    return models if models else list(self.AVAILABLE_MODELS.values())
        except:
            pass
        
        return list(self.AVAILABLE_MODELS.values())
    
    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model"""
        return self.AVAILABLE_MODELS.get(model_id)
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()


# Register the provider
register_provider('ollama', OllamaProvider)
register_provider('local', OllamaProvider)
