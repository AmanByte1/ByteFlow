# ByteFlow AI Providers Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ByteFlow Application                    │
│  (Agent, Chat, Tools, etc.)                                 │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│            AI Provider Interface (Unified)                  │
│         (AIProvider, ProviderConfig, ModelInfo)             │
└────────────────┬────────────────────────────────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
        ▼                 ▼
┌──────────────────────┐  ┌──────────────────────┐
│ API-Based Providers  │  │ Local Providers      │
├──────────────────────┤  ├──────────────────────┤
│ • Claude (Anthropic) │  │ • Ollama (Local)     │
│ • ChatGPT (OpenAI)   │  │   - Llama 2          │
│ • Gemini (Google)    │  │   - Mistral          │
│ • Grok (X)           │  │   - Neural Chat      │
└──────────────────────┘  │   - Custom Models    │
        │                 │                      │
        │                 └──────────────────────┘
        │
        ├─────────────────────────────────┐
        │                                 │
        ▼                                 ▼
    HTTP/HTTPS                      HTTP (localhost)
    (aiohttp Client)                 (aiohttp Client)
        │                                 │
        │                                 │
        ▼                                 ▼
   External APIs                    Ollama Server
   (auth headers,                   (local inference)
    streaming)                       (on localhost:11434)
```

## Directory Structure

```
byteflow/
├── ai_providers/
│   ├── __init__.py                 # Main exports
│   ├── base.py                     # Base classes & interfaces
│   ├── registry.py                 # Provider registry
│   │
│   ├── anthropic_provider.py        # Claude provider
│   ├── openai_provider.py           # ChatGPT provider
│   ├── google_provider.py           # Gemini provider
│   ├── grok_provider.py             # Grok provider
│   └── local_provider.py            # Ollama provider
│
├── agent.py                         # Main Agent class (uses providers)
├── ... (other existing modules)
```

## Core Components

### 1. Base Classes (`base.py`)

```python
AIProvider (ABC)
├── initialize()          # Connection setup & auth
├── generate()            # Single response
├── stream_generate()     # Streaming responses
├── list_models()         # Available models
├── get_model_info()      # Model details
└── close()              # Cleanup

ProviderConfig
├── provider_name        # e.g., 'claude'
├── access_type          # API, WEB, WEBSOCKET, HYBRID
├── api_key             # Authentication
├── model_id            # Model selection
├── temperature         # Generation params
├── max_tokens          # Output limit
├── system_prompt       # Instructions
└── ... (advanced config)

ModelInfo
├── id, name           # Identification
├── type               # CHAT, COMPLETION, MULTIMODAL
├── context_window     # Max context
├── max_output         # Max output tokens
├── supports_vision    # Image input
├── supports_audio     # Audio input
└── cost_per_1k_*      # Pricing info
```

### 2. Provider Registry (`registry.py`)

```python
AIProviderRegistry
├── register(name, class)           # Register provider
├── get_provider_class(name)        # Get provider class
├── list_providers()                # List all providers
├── create_instance(name, config)   # Create instance
└── clear_cache()                   # Clear instances

# Convenience functions
get_provider(name, **kwargs)        # Get/create provider
register_provider(name, class)      # Register provider
list_providers()                    # List available
```

### 3. Provider Implementations

Each provider inherits from `AIProvider` and implements:

- **Authentication**: Validates API keys
- **API Communication**: Makes HTTP requests
- **Error Handling**: Handles provider-specific errors
- **Model Management**: Lists available models
- **Streaming**: Implements token streaming
- **Resource Cleanup**: Closes connections

## Data Flow

### Simple Generation Request

```
User Code
    ↓
provider.generate(prompt)
    ↓
ProviderConfig validation
    ↓
prepare_request() [provider-specific]
    ↓
HTTP POST to API/localhost
    ↓
parse_response()
    ↓
return text to user
```

### Streaming Request

```
User Code
    ↓
provider.stream_generate(prompt)
    ↓
setup_stream_connection()
    ↓
HTTP POST with stream=True
    ↓
for each chunk from stream:
    ├─ parse chunk
    ├─ yield token
    └─ continue
    ↓
connection closes
```

## Provider Specifications

### Anthropic Claude

```
┌─ Protocol: REST API
├─ Base URL: https://api.anthropic.com/v1
├─ Authentication: x-api-key header
├─ Models: opus-4.6, sonnet-4.6, haiku-4.5
├─ Context Window: up to 200K tokens
├─ Features:
│  ├─ Vision support
│  ├─ Tool use
│  ├─ Streaming
│  └─ Batch processing
└─ Pricing: Per million tokens

Example Request:
POST /messages
Headers:
  x-api-key: {key}
  anthropic-version: 2024-06-15
Body:
  {
    "model": "claude-opus-4-6",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "..."}]
  }
```

### OpenAI ChatGPT

```
┌─ Protocol: REST API
├─ Base URL: https://api.openai.com/v1
├─ Authentication: Bearer token
├─ Models: gpt-4-turbo, gpt-4, gpt-3.5-turbo
├─ Context Window: up to 128K tokens
├─ Features:
│  ├─ Vision (GPT-4V)
│  ├─ Function calling
│  ├─ Streaming
│  └─ Fine-tuning
└─ Pricing: Per 1K tokens

Example Request:
POST /chat/completions
Headers:
  Authorization: Bearer {key}
Body:
  {
    "model": "gpt-4-turbo-preview",
    "messages": [{"role": "user", "content": "..."}],
    "stream": false
  }
```

### Google Gemini

```
┌─ Protocol: REST API
├─ Base URL: https://generativelanguage.googleapis.com/v1beta
├─ Authentication: API key in URL
├─ Models: gemini-pro, gemini-1.5-pro
├─ Context Window: up to 1M tokens
├─ Features:
│  ├─ Vision & Audio (1.5)
│  ├─ Long context
│  ├─ Streaming
│  └─ Safety ratings
└─ Pricing: Competitive

Example Request:
POST /models/{model}:generateContent?key={key}
Body:
  {
    "contents": [{
      "parts": [{"text": "..."}]
    }],
    "generationConfig": {"temperature": 0.7}
  }
```

### X Grok

```
┌─ Protocol: REST API
├─ Base URL: https://api.x.ai/v1
├─ Authentication: Bearer token
├─ Models: grok-1, grok-vision-beta
├─ Context Window: 128K tokens
├─ Features:
│  ├─ Vision support
│  ├─ Fast inference
│  ├─ Streaming
│  └─ Real-time capabilities
└─ Pricing: Moderate

Example Request:
POST /chat/completions
Headers:
  Authorization: Bearer {key}
Body:
  {
    "model": "grok-1",
    "messages": [{"role": "user", "content": "..."}]
  }
```

### Ollama Local

```
┌─ Protocol: REST API
├─ Base URL: http://localhost:11434
├─ Authentication: None (local)
├─ Models: llama2, mistral, neural-chat, custom
├─ Context Window: Model-dependent
├─ Features:
│  ├─ Local inference
│  ├─ No API costs
│  ├─ Full privacy
│  ├─ Streaming
│  └─ Model customization
└─ Pricing: Free (hardware costs)

Example Request:
POST /api/generate
Body:
  {
    "model": "llama2",
    "prompt": "...",
    "stream": false
  }
```

## Configuration Hierarchy

```
Defaults (in base.py)
    ↓
Environment Variables
    ↓
ProviderConfig object
    ↓
Per-request overrides
    ↓
Actual request parameters
```

Example:
```python
# Default: temp = 0.7
config = ProviderConfig(temperature=0.8)  # Override to 0.8
provider.generate("prompt", temperature=0.9)  # Override to 0.9
# Final temperature = 0.9
```

## Error Handling Strategy

```
Provider Error
├─ ProviderAuthError (401, invalid key)
├─ ProviderConnectionError (network issues)
├─ ProviderRateLimitError (429)
├─ ProviderModelNotFound (404)
└─ ProviderError (generic)

Retry Strategy:
1. ProviderAuthError → No retry (fix credentials)
2. ProviderRateLimitError → Exponential backoff
3. ProviderConnectionError → Retry with delay
4. Generic ProviderError → Retry, then fail
```

## Performance Considerations

### Connection Pooling
- Uses `aiohttp.ClientSession` for connection reuse
- Sessions kept alive across requests
- Manual cleanup with `provider.close()`

### Caching
- Optional response caching (configurable TTL)
- Cache key: provider + model + prompt hash
- Useful for repeated queries

### Streaming
- Token-by-token streaming for low latency
- Useful for real-time UX
- Reduces memory usage for large responses

### Async/Await
- All operations are async-first
- Non-blocking I/O for better concurrency
- Integration with asyncio event loop

## Security Considerations

### API Keys
- Never hardcode keys - use environment variables
- Support key rotation
- Validate keys during initialization

### Data Privacy
- Option to use local providers (Ollama) for sensitive data
- Support for proxy configuration
- Logging can be disabled

### HTTPS
- All API providers use HTTPS
- Certificate validation enabled by default
- Support for custom CA certificates (via proxy)

## Extension Points

### Adding New Providers

1. **Create Provider Class**
```python
class MyProvider(AIProvider):
    async def initialize(self): ...
    async def generate(self, prompt, ...): ...
    # ... implement other methods
```

2. **Register Provider**
```python
register_provider('myprovider', MyProvider)
```

3. **Use Provider**
```python
provider = get_provider('myprovider', api_key='...')
```

### Customizing Behavior

- Override methods in subclass
- Create wrapper providers
- Implement custom error handling
- Add provider-specific features

## Testing Strategy

```
test_ai_providers/
├── test_base.py              # Base class tests
├── test_registry.py          # Registry tests
├── test_anthropic.py         # Claude tests
├── test_openai.py            # ChatGPT tests
├── test_google.py            # Gemini tests
├── test_grok.py              # Grok tests
└── test_ollama.py            # Ollama tests

Mock Strategies:
- Mock HTTP responses
- Test error handling
- Verify config parsing
- Test streaming
- Test model listing
```

## Integration with ByteFlow Agent

The `Agent` class now accepts any `AIProvider`:

```python
from byteflow.agent import Agent
from byteflow.ai_providers import get_provider

provider = get_provider('claude', api_key='...')
agent = Agent(provider=provider)

# Use agent normally
response = agent.chat("Hello!")
```

## Future Enhancements

- [ ] Web-based provider access (browser automation)
- [ ] WebSocket streaming for lower latency
- [ ] Hybrid providers (API + web fallback)
- [ ] Built-in provider health monitoring
- [ ] Advanced caching strategies
- [ ] Load balancing across providers
- [ ] Provider fallback chains
- [ ] Cost tracking and optimization
- [ ] Custom fine-tuned models
- [ ] Multi-modal request handling

## Performance Metrics

### Typical Response Times (latency)

| Provider | P50 | P95 | P99 |
|----------|-----|-----|-----|
| Claude Opus | 1-2s | 2-3s | 3-5s |
| Claude Sonnet | 0.5-1s | 1-2s | 2-3s |
| GPT-4 Turbo | 1-2s | 2-4s | 4-6s |
| Gemini Pro | 0.5-1s | 1-2s | 2-4s |
| Grok | 0.3-0.8s | 0.8-1.5s | 1.5-2.5s |
| Ollama (local) | 0.1-1s | 0.5-2s | 1-5s |

*(Varies by model, region, and load)*

## Deployment Considerations

### Docker
```dockerfile
FROM python:3.11
RUN pip install aiohttp

# Copy ByteFlow
COPY byteflow /app/byteflow

# Set env vars
ENV ANTHROPIC_API_KEY=...
ENV OPENAI_API_KEY=...

# Run app
CMD ["python", "app.py"]
```

### Environment Setup
```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
XAI_API_KEY=...
OLLAMA_API_URL=http://localhost:11434
```

---

**Architecture Version**: 1.0
**Last Updated**: 2024
**Status**: Stable
