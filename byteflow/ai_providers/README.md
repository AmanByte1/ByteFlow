# ByteFlow AI Providers Module

Unified, provider-agnostic interface for multiple AI models including Claude, ChatGPT, Gemini, Grok, and Ollama.

## Quick Start

```python
from byteflow.ai_providers import get_provider

# Use Claude
provider = get_provider('claude', api_key='sk-ant-...')
await provider.initialize()
response = await provider.generate("What is AI?")

# Or use ChatGPT
provider = get_provider('openai', api_key='sk-...')
response = await provider.generate("What is AI?")

# Or use local Ollama (no API key!)
provider = get_provider('ollama', model_id='llama2')
response = await provider.generate("What is AI?")
```

## Supported Providers

| Provider | API | Web | Local | Status |
|----------|-----|-----|-------|--------|
| Claude (Anthropic) | ✅ | ❌ | ❌ | ✅ Ready |
| ChatGPT (OpenAI) | ✅ | ❌ | ❌ | ✅ Ready |
| Gemini (Google) | ✅ | ❌ | ❌ | ✅ Ready |
| Grok (X) | ✅ | ❌ | ❌ | ✅ Ready |
| Ollama (Local) | ✅ | ❌ | ✅ | ✅ Ready |

## Features

- 🎯 **Unified Interface** - One way to use all providers
- ⚡ **Async Native** - Full async/await support
- 🔄 **Streaming** - Token-by-token streaming responses
- 🛡️ **Error Handling** - Provider-specific exceptions
- 📦 **Zero Dependencies** - Only requires `aiohttp`
- 🔌 **Extensible** - Easy to add new providers
- 🔐 **Secure** - Environment variable support for API keys
- 📊 **Model Info** - List and inspect available models

## Installation

```bash
# ByteFlow includes this by default
# Just ensure aiohttp is installed
pip install aiohttp
```

## Basic Usage

### 1. Generate Text
```python
provider = get_provider('claude', api_key='your-key')
await provider.initialize()
response = await provider.generate("Explain quantum computing")
print(response)
await provider.close()
```

### 2. Stream Response
```python
async for token in provider.stream_generate("Tell a story"):
    print(token, end='', flush=True)
```

### 3. List Models
```python
models = await provider.list_models()
for model in models:
    print(f"{model.name} - {model.id}")
```

### 4. Get Model Info
```python
info = await provider.get_model_info('claude-opus-4-6')
print(f"Context: {info.context_window} tokens")
print(f"Cost: ${info.cost_per_1k_output}/1K tokens")
```

## Environment Variables

```bash
# Claude
export ANTHROPIC_API_KEY="sk-ant-..."

# OpenAI
export OPENAI_API_KEY="sk-..."

# Google
export GOOGLE_API_KEY="your-key"

# Grok
export XAI_API_KEY="your-key"

# Ollama
export OLLAMA_API_URL="http://localhost:11434"
```

## Advanced Usage

### Custom Configuration
```python
from byteflow.ai_providers import ProviderConfig

config = ProviderConfig(
    provider_name='claude',
    temperature=0.7,
    max_tokens=2048,
    system_prompt="You are a helpful assistant",
)
```

### Error Handling
```python
from byteflow.ai_providers.base import ProviderAuthError, ProviderError

try:
    response = await provider.generate(prompt)
except ProviderAuthError:
    print("Authentication failed - check your API key")
except ProviderError as e:
    print(f"Provider error: {e}")
```

### Batch Processing
```python
for prompt in prompts:
    response = await provider.generate(prompt)
    process(response)
```

### Provider Switching
```python
for provider_name in ['claude', 'openai', 'gemini']:
    provider = get_provider(provider_name, api_key='...')
    response = await provider.generate(prompt)
```

## Architecture

```
AIProvider (Abstract Base)
├── AnthropicProvider (Claude)
├── OpenAIProvider (ChatGPT)
├── GoogleProvider (Gemini)
├── GrokProvider (Grok)
└── OllamaProvider (Local)

ProviderRegistry
├── register(name, class)
├── get_provider_class(name)
└── create_instance(name, config)
```

## File Structure

```
ai_providers/
├── __init__.py              # Main exports
├── base.py                  # Base classes
├── registry.py              # Provider registry
├── anthropic_provider.py    # Claude
├── openai_provider.py       # ChatGPT
├── google_provider.py       # Gemini
├── grok_provider.py         # Grok
└── local_provider.py        # Ollama
```

## Documentation

- **[User Guide](../../AI_PROVIDERS_GUIDE.md)** - Complete guide with examples
- **[Architecture](../../AI_PROVIDERS_ARCHITECTURE.md)** - System design details
- **[Examples](../../examples_ai_providers.py)** - 12 runnable examples
- **[Summary](../../AI_PROVIDERS_SUMMARY.md)** - Implementation overview

## Common Tasks

### Use Claude for Complex Tasks
```python
provider = get_provider('claude', api_key='sk-ant-...')
```

### Use GPT-4 for General Tasks
```python
provider = get_provider('openai', api_key='sk-...', model_id='gpt-4-turbo')
```

### Use Gemini for Long Context
```python
provider = get_provider('gemini', api_key='...', model_id='gemini-1.5-pro')
```

### Use Local Ollama (No API Key!)
```python
provider = get_provider('ollama', model_id='llama2')
# Make sure Ollama is running: ollama serve
```

## Error Handling

```python
from byteflow.ai_providers.base import (
    ProviderAuthError,
    ProviderConnectionError,
    ProviderRateLimitError,
    ProviderError
)

try:
    response = await provider.generate(prompt)
except ProviderAuthError:
    # Invalid API key
    pass
except ProviderConnectionError:
    # Network issues
    pass
except ProviderRateLimitError:
    # Rate limited - implement backoff
    pass
except ProviderError:
    # Generic provider error
    pass
```

## Performance Tips

1. **Reuse Providers** - Create once, use multiple times
2. **Use Streaming** - For better UX with long responses
3. **Enable Caching** - For repeated identical requests
4. **Batch Requests** - Process multiple prompts together
5. **Use Appropriate Models** - Match model to task complexity

## Integration with ByteFlow Agent

```python
from byteflow.agent import Agent
from byteflow.ai_providers import get_provider

provider = get_provider('claude', api_key='sk-ant-...')
agent = Agent(provider=provider)

response = agent.chat("Tell me about AI")
```

## Troubleshooting

### "Invalid API Key"
- Verify key is correct
- Check environment variables
- Ensure key hasn't expired

### "Connection Timeout"
- Check internet connection
- Verify API endpoint is accessible
- Increase `request_timeout` in config

### "Rate Limit Exceeded"
- Implement exponential backoff
- Use cheaper/faster models
- Consider local Ollama

### Ollama Connection Issues
- Ensure Ollama is running: `ollama serve`
- Check OLLAMA_API_URL environment variable
- Verify localhost:11434 is accessible

## Creating Custom Providers

```python
from byteflow.ai_providers.base import AIProvider
from byteflow.ai_providers.registry import register_provider

class MyProvider(AIProvider):
    async def initialize(self):
        # Your auth logic
        return True
    
    async def generate(self, prompt, **kwargs):
        # Your generation logic
        return response
    
    async def stream_generate(self, prompt, **kwargs):
        # Your streaming logic
        yield token
    
    async def list_models(self):
        # Return available models
        return models
    
    async def get_model_info(self, model_id):
        # Return model info
        return info

# Register it
register_provider('myprovider', MyProvider)

# Use it
provider = get_provider('myprovider')
```

## API Reference

### AIProvider Methods

```python
async initialize() -> bool
    Connect and authenticate with the provider

async generate(prompt, system_prompt=None, temperature=None, max_tokens=None) -> str
    Generate a single response

async stream_generate(prompt, system_prompt=None) -> AsyncIterator[str]
    Stream response tokens

async list_models() -> List[ModelInfo]
    Get available models

async get_model_info(model_id: str) -> Optional[ModelInfo]
    Get specific model details

async close()
    Cleanup resources
```

### Utility Functions

```python
get_provider(name: str, **kwargs) -> AIProvider
    Get or create a provider instance

register_provider(name: str, provider_class: Type[AIProvider])
    Register a new provider

list_providers() -> List[str]
    List all available providers
```

## Contributing

To add a new provider:

1. Create a new file: `new_provider.py`
2. Inherit from `AIProvider`
3. Implement all abstract methods
4. Register: `register_provider('name', NewProvider)`
5. Add tests and documentation
6. Submit a PR!

## FAQ

**Q: Can I use multiple providers simultaneously?**
A: Yes! Create multiple instances and use them together.

**Q: Is there a cost for Ollama?**
A: No, Ollama is free and runs locally.

**Q: Can I cache responses?**
A: Yes, set `use_cache=True` in ProviderConfig.

**Q: What's the cheapest option?**
A: Ollama (free) or Claude Haiku (~$2.40/M tokens).

**Q: Which provider is fastest?**
A: Grok is typically fastest (~0.3-0.8s).

**Q: Which has the largest context?**
A: Gemini 1.5 Pro (1 million tokens).

## License

Same as ByteFlow

## Support

- 📖 See documentation files
- 💬 Check examples
- 🐛 Report issues
- 🤝 Contribute improvements

---

**Ready to use?** Start with the [User Guide](../../AI_PROVIDERS_GUIDE.md)!
