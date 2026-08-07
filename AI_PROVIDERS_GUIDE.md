# ByteFlow AI Providers Integration Guide

## Overview

ByteFlow now supports seamless integration with multiple AI providers through a unified, provider-agnostic interface. Use any AI model you prefer - whether through direct API calls or web-based access.

## Supported Providers

### 1. **Claude (Anthropic)**
- **Models**: Claude Opus 4.6, Claude Sonnet 4.6, Claude Haiku 4.5
- **Access**: API only
- **Features**: 
  - Up to 200K context window
  - Vision support
  - Best for complex reasoning
- **Cost**: Varies by model

### 2. **ChatGPT (OpenAI)**
- **Models**: GPT-4 Turbo, GPT-4, GPT-3.5 Turbo
- **Access**: API only
- **Features**:
  - Up to 128K context window (GPT-4 Turbo)
  - Vision support (GPT-4, GPT-4 Turbo)
  - Excellent for various tasks
- **Cost**: Varies by model

### 3. **Gemini (Google)**
- **Models**: Gemini Pro, Gemini Pro Vision, Gemini 1.5 Pro
- **Access**: API only
- **Features**:
  - Up to 1 million context window (1.5 Pro)
  - Vision and audio support (1.5 Pro)
  - Highly efficient
- **Cost**: Competitive pricing

### 4. **Grok (X)**
- **Models**: Grok-1, Grok Vision Beta
- **Access**: API only
- **Features**:
  - 128K context window
  - Vision support
  - Fast inference
- **Cost**: Moderate

### 5. **Ollama (Local)**
- **Models**: Llama 2, Mistral, Neural Chat, Dolphin Mixtral, and more
- **Access**: Local HTTP API
- **Features**:
  - Run completely offline
  - No API costs
  - Full privacy
  - Customizable models
- **Requirements**: Ollama installed locally

## Installation

### Basic Setup

```bash
# Install dependencies
pip install aiohttp

# That's it! The providers are built-in
```

### Optional: Install Ollama for Local Models

```bash
# Download from https://ollama.ai
# Then start the Ollama server
ollama serve

# Pull a model
ollama pull llama2
```

## Quick Start

### Using Claude

```python
from byteflow.ai_providers import get_provider

# Create a Claude provider
provider = get_provider(
    'claude',
    api_key='your-anthropic-api-key'  # or set ANTHROPIC_API_KEY env var
)

# Initialize (test connection)
await provider.initialize()

# Generate text
response = await provider.generate(
    "What is machine learning?",
    system_prompt="You are a helpful assistant.",
    temperature=0.7,
    max_tokens=1000
)
print(response)

# Stream response
async for chunk in provider.stream_generate("Explain AI in 50 words"):
    print(chunk, end='', flush=True)
```

### Using ChatGPT

```python
from byteflow.ai_providers import get_provider

provider = get_provider(
    'openai',
    api_key='your-openai-api-key'  # or set OPENAI_API_KEY env var
)

await provider.initialize()

response = await provider.generate(
    "What is artificial intelligence?",
    model_id='gpt-4-turbo-preview'
)
print(response)
```

### Using Gemini

```python
from byteflow.ai_providers import get_provider

provider = get_provider(
    'gemini',
    api_key='your-google-api-key'  # or set GOOGLE_API_KEY env var
)

await provider.initialize()

response = await provider.generate(
    "Explain machine learning",
    model_id='gemini-1.5-pro'
)
print(response)
```

### Using Grok

```python
from byteflow.ai_providers import get_provider

provider = get_provider(
    'grok',
    api_key='your-grok-api-key'  # or set XAI_API_KEY or GROK_API_KEY
)

await provider.initialize()

response = await provider.generate("Tell me a joke")
print(response)
```

### Using Local Ollama

```python
from byteflow.ai_providers import get_provider

# Make sure Ollama is running: ollama serve
provider = get_provider(
    'ollama',
    model_id='llama2'  # or 'mistral', 'neural-chat', etc
)

await provider.initialize()

response = await provider.generate(
    "What is Python?",
    temperature=0.5,
    max_tokens=500
)
print(response)

# List available local models
models = await provider.list_models()
for model in models:
    print(f"{model.name} - {model.id}")
```

## Advanced Usage

### Configuration

```python
from byteflow.ai_providers import ProviderConfig, get_provider
from byteflow.ai_providers.base import AccessType

# Create a custom configuration
config = ProviderConfig(
    provider_name='claude',
    access_type=AccessType.API,
    api_key='your-key',
    temperature=0.7,
    max_tokens=2048,
    top_p=0.9,
    top_k=40,
    max_retries=3,
    retry_delay=1.0,
    request_timeout=60,
    system_prompt="You are an expert Python developer",
    use_cache=True,
    cache_ttl=3600,
)

provider = get_provider('claude')  # Uses default config
```

### Streaming Responses

```python
# Streaming is useful for long responses
print("Response: ", end='')
async for token in provider.stream_generate("Write a 500 word essay about AI"):
    print(token, end='', flush=True)
print()
```

### Model Information

```python
# List available models
models = await provider.list_models()
for model in models:
    print(f"Model: {model.name}")
    print(f"  ID: {model.id}")
    print(f"  Context: {model.context_window} tokens")
    print(f"  Max Output: {model.max_output} tokens")
    print(f"  Vision: {model.supports_vision}")
    print(f"  Audio: {model.supports_audio}")
    print()

# Get specific model info
model_info = await provider.get_model_info('claude-opus-4-6')
if model_info:
    print(f"Model: {model_info.name}")
    print(f"Input cost: ${model_info.cost_per_1k_input}/1K tokens")
    print(f"Output cost: ${model_info.cost_per_1k_output}/1K tokens")
```

### Switching Providers

```python
# Easy provider switching
providers_config = {
    'claude': {'api_key': 'sk-claude-...'},
    'openai': {'api_key': 'sk-openai-...'},
    'gemini': {'api_key': 'google-key-...'},
    'ollama': {'model_id': 'llama2'},
}

# Switch providers
for name, config in providers_config.items():
    provider = get_provider(name, **config)
    await provider.initialize()
    
    response = await provider.generate("What is AI?")
    print(f"{name}: {response[:100]}...")
    
    await provider.close()
```

### Error Handling

```python
from byteflow.ai_providers.base import (
    ProviderError, ProviderAuthError, ProviderConnectionError,
    ProviderRateLimitError
)

try:
    provider = get_provider('claude', api_key='invalid-key')
    await provider.initialize()
except ProviderAuthError as e:
    print(f"Authentication failed: {e}")
except ProviderConnectionError as e:
    print(f"Connection failed: {e}")
except ProviderRateLimitError as e:
    print(f"Rate limited: {e}")
except ProviderError as e:
    print(f"Provider error: {e}")
```

### Integrating with ByteFlow Agent

```python
from byteflow.agent import Agent
from byteflow.ai_providers import get_provider

# Create a provider
provider = get_provider('claude', api_key='your-key')

# Use with ByteFlow Agent
agent = Agent(
    provider=provider,
    personality="You are a helpful coding assistant"
)

# Chat using the provider
response = agent.chat("How do I write a Python decorator?")
print(response)
```

## Environment Variables

Set these environment variables for easier configuration:

```bash
# Claude
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI
export OPENAI_API_KEY="sk-..."

# Google
export GOOGLE_API_KEY="your-key"

# Grok/XAI
export XAI_API_KEY="your-key"
export GROK_API_KEY="your-key"  # Alternative

# Ollama
export OLLAMA_API_URL="http://localhost:11434"
```

## Provider Features Comparison

| Feature | Claude | ChatGPT | Gemini | Grok | Ollama |
|---------|--------|---------|--------|------|--------|
| API Access | ✅ | ✅ | ✅ | ✅ | ✅ |
| Web Access | ❌ | ❌ | ❌ | ❌ | N/A |
| Vision Support | ✅ | ✅ | ✅ | ✅ | ❌ |
| Audio Support | ❌ | ❌ | ✅ | ❌ | ❌ |
| Max Context | 200K | 128K | 1M | 128K | Varies |
| Local/Offline | ❌ | ❌ | ❌ | ❌ | ✅ |
| Cost | Medium | Low-High | Low | Medium | Free |
| Speed | Fast | Fast | Fast | Fast | Depends |

## Best Practices

### 1. **Provider Selection**
- Use **Claude** for complex reasoning and analysis
- Use **GPT-4** for general-purpose tasks
- Use **Gemini 1.5** for very long context
- Use **Grok** for real-time information
- Use **Ollama** for privacy-critical applications

### 2. **Error Handling**
```python
import asyncio

async def safe_generate(provider, prompt, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await provider.generate(prompt)
        except ProviderRateLimitError:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        except ProviderError as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(1)
```

### 3. **Resource Management**
```python
# Always close providers to clean up resources
try:
    response = await provider.generate("Your prompt")
finally:
    await provider.close()

# Or use context manager (when available)
async with provider:
    response = await provider.generate("Your prompt")
```

### 4. **Caching & Performance**
```python
# Enable caching for repeated requests
config = ProviderConfig(
    provider_name='claude',
    use_cache=True,
    cache_ttl=3600,  # 1 hour
)
```

### 5. **Logging**
```python
# Enable logging for debugging
config = ProviderConfig(
    provider_name='claude',
    enable_logging=True,
)
```

## Troubleshooting

### "Invalid API Key"
- Verify your API key is correct
- Check environment variables
- Ensure the key hasn't expired or been revoked

### "Connection Timeout"
- Check your internet connection
- Verify the API endpoint is accessible
- Increase `request_timeout` in configuration

### "Rate Limit Exceeded"
- Implement exponential backoff
- Reduce request frequency
- Use a cheaper/faster model
- Consider Ollama for unlimited requests

### "Model Not Found"
- Check available models: `await provider.list_models()`
- Verify model ID spelling
- Ensure you have access to the model

### Ollama Connection Issues
- Ensure Ollama is running: `ollama serve`
- Check OLLAMA_API_URL environment variable
- Verify localhost:11434 is accessible
- Try pulling a model: `ollama pull llama2`

## Advanced: Creating Custom Providers

```python
from byteflow.ai_providers.base import AIProvider, ProviderConfig
from byteflow.ai_providers.registry import register_provider

class CustomProvider(AIProvider):
    async def initialize(self) -> bool:
        # Your initialization logic
        return True
    
    async def generate(self, prompt, system_prompt=None, **kwargs):
        # Your generation logic
        pass
    
    async def stream_generate(self, prompt, system_prompt=None, **kwargs):
        # Your streaming logic
        pass
    
    async def list_models(self):
        # Return available models
        pass
    
    async def get_model_info(self, model_id):
        # Return model information
        pass

# Register your provider
register_provider('mycustom', CustomProvider)

# Use it
provider = get_provider('mycustom')
```

## Cost Estimation

### Monthly Costs Example (1 million tokens)

**Input (500K tokens) + Output (500K tokens):**

- **Claude Opus**: ~$45
- **Claude Sonnet**: ~$9
- **Claude Haiku**: ~$2.40
- **GPT-4 Turbo**: ~$40
- **GPT-3.5 Turbo**: ~$2.75
- **Gemini Pro**: ~$1.75
- **Gemini 1.5 Pro**: ~$8.75
- **Grok-1**: ~$10
- **Ollama (Local)**: ~$0 (one-time setup)

## Security Notes

- Never commit API keys to version control
- Use environment variables for credentials
- Consider using API key rotation
- For Ollama, only expose to trusted networks
- Monitor API usage for unusual activity

## Contributing

To add a new provider:

1. Create a new file in `byteflow/ai_providers/`
2. Inherit from `AIProvider` base class
3. Implement required methods
4. Register with `register_provider()`
5. Add tests and documentation
6. Submit a PR!

## FAQ

**Q: Can I use multiple providers in the same application?**
A: Yes! Create multiple provider instances and use them in sequence or in parallel.

**Q: Is there a cost for using Ollama?**
A: No, Ollama is free and runs locally. Only your hardware costs (electricity).

**Q: Can I cache API responses?**
A: Yes, enable `use_cache=True` in ProviderConfig.

**Q: What's the maximum token context?**
A: Depends on the provider. Gemini 1.5 Pro supports up to 1 million tokens.

**Q: Can I use streaming for all providers?**
A: Yes, all providers support streaming via `stream_generate()`.

**Q: How do I handle provider failures?**
A: Catch provider-specific exceptions and implement retry logic.

---

**Last Updated**: 2024
**Version**: 1.0
**Status**: Active & Maintained
