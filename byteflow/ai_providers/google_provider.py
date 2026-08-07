"""
Google Gemini Provider
Supports API-based access to Google's Gemini models.
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


class GoogleProvider(AIProvider):
    """Google Gemini Provider"""
    
    AVAILABLE_MODELS = {
        'gemini-pro': ModelInfo(
            id='gemini-pro',
            name='Gemini Pro',
            provider='google',
            type=ProviderType.CHAT,
            context_window=32000,
            max_output=8192,
            supports_vision=False,
            supports_audio=False,
            cost_per_1k_input=0.00035,
            cost_per_1k_output=0.00053,
        ),
        'gemini-pro-vision': ModelInfo(
            id='gemini-pro-vision',
            name='Gemini Pro Vision',
            provider='google',
            type=ProviderType.MULTIMODAL,
            context_window=32000,
            max_output=8192,
            supports_vision=True,
            supports_audio=False,
            cost_per_1k_input=0.00035,
            cost_per_1k_output=0.00053,
        ),
        'gemini-1.5-pro': ModelInfo(
            id='gemini-1.5-pro',
            name='Gemini 1.5 Pro',
            provider='google',
            type=ProviderType.MULTIMODAL,
            context_window=1000000,  # 1 million tokens
            max_output=8192,
            supports_vision=True,
            supports_audio=True,
            cost_per_1k_input=0.00175,
            cost_per_1k_output=0.00525,
        ),
    }
    
    API_BASE_URL = "https://generativelanguage.googleapis.com"
    API_VERSION = "v1beta"
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.api_key = config.api_key or os.getenv('GOOGLE_API_KEY')
        self.model_id = config.model_id or 'gemini-pro'
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self) -> bool:
        """Initialize the provider"""
        if not self.api_key:
            raise ProviderAuthError(
                "API key required. Set GOOGLE_API_KEY or pass api_key parameter"
            )
        
        try:
            self.session = aiohttp.ClientSession()
            await self._test_connection()
            self._initialized = True
            return True
        except Exception as e:
            raise ProviderAuthError(f"Failed to authenticate with Google: {str(e)}")
    
    async def _test_connection(self) -> None:
        """Test connection to Google API"""
        if not self.session:
            return
        
        url = (
            f'{self.API_BASE_URL}/{self.API_VERSION}/models/'
            f'{self.model_id}:generateContent?key={self.api_key}'
        )
        
        payload = {
            'contents': [{
                'parts': [{'text': 'Hi'}]
            }]
        }
        
        async with self.session.post(url, json=payload) as resp:
            if resp.status == 400:
                error = await resp.json()
                if 'API key not valid' in str(error):
                    raise ProviderAuthError("Invalid API key")
            if resp.status not in [200, 400]:  # 400 is expected for test
                raise ProviderConnectionError(f"API returned status {resp.status}")
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate text using Gemini API"""
        if not self._initialized:
            await self.initialize()
        
        if not self.session:
            raise ProviderConnectionError("Provider not initialized")
        
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens
        
        url = (
            f'{self.API_BASE_URL}/{self.API_VERSION}/models/'
            f'{self.model_id}:generateContent?key={self.api_key}'
        )
        
        contents = []
        if system_prompt or self.config.system_prompt:
            contents.append({
                'role': 'user',
                'parts': [{'text': system_prompt or self.config.system_prompt}]
            })
        
        contents.append({
            'role': 'user',
            'parts': [{'text': prompt}]
        })
        
        payload = {
            'contents': contents,
            'generationConfig': {
                'temperature': temp,
                'maxOutputTokens': max_tok,
                'topP': self.config.top_p,
                'topK': self.config.top_k,
            }
        }
        
        try:
            async with self.session.post(
                url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.config.request_timeout)
            ) as resp:
                if resp.status == 429:
                    raise ProviderError("Rate limit exceeded")
                elif resp.status != 200:
                    error_text = await resp.text()
                    raise ProviderError(f"API error: {resp.status} - {error_text}")
                
                data = await resp.json()
                if 'candidates' in data and len(data['candidates']) > 0:
                    content = data['candidates'][0]['content']
                    if 'parts' in content and len(content['parts']) > 0:
                        return content['parts'][0]['text']
                return ""
        except asyncio.TimeoutError:
            raise ProviderConnectionError("Request timeout")
    
    async def stream_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ):
        """Stream text generation from Gemini"""
        if not self._initialized:
            await self.initialize()
        
        if not self.session:
            raise ProviderConnectionError("Provider not initialized")
        
        url = (
            f'{self.API_BASE_URL}/{self.API_VERSION}/models/'
            f'{self.model_id}:streamGenerateContent?key={self.api_key}'
        )
        
        contents = []
        if system_prompt or self.config.system_prompt:
            contents.append({
                'role': 'user',
                'parts': [{'text': system_prompt or self.config.system_prompt}]
            })
        
        contents.append({
            'role': 'user',
            'parts': [{'text': prompt}]
        })
        
        payload = {
            'contents': contents,
            'generationConfig': {
                'temperature': self.config.temperature,
                'maxOutputTokens': self.config.max_tokens,
                'topP': self.config.top_p,
            }
        }
        
        try:
            async with self.session.post(url, json=payload) as resp:
                if resp.status != 200:
                    raise ProviderError(f"API error: {resp.status}")
                
                async for line in resp.content:
                    if line:
                        line_str = line.decode('utf-8').strip()
                        try:
                            data = json.loads(line_str)
                            if 'candidates' in data and len(data['candidates']) > 0:
                                content = data['candidates'][0]['content']
                                if 'parts' in content and len(content['parts']) > 0:
                                    if 'text' in content['parts'][0]:
                                        yield content['parts'][0]['text']
                        except json.JSONDecodeError:
                            pass
        except asyncio.TimeoutError:
            raise ProviderConnectionError("Request timeout")
    
    async def list_models(self) -> List[ModelInfo]:
        """List available Gemini models"""
        return list(self.AVAILABLE_MODELS.values())
    
    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """Get information about a specific model"""
        return self.AVAILABLE_MODELS.get(model_id)
    
    async def close(self):
        """Close the session"""
        if self.session:
            await self.session.close()


# Register the provider
register_provider('google', GoogleProvider)
register_provider('gemini', GoogleProvider)
