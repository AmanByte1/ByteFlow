"""
ByteFlow AI Providers - Usage Examples

This file demonstrates various ways to use the unified AI providers interface.
Run with: python examples_ai_providers.py
"""

import asyncio
from byteflow.ai_providers import get_provider, list_providers


# ============================================================================
# Example 1: Using Claude (Anthropic)
# ============================================================================

async def example_claude():
    """Example: Basic Claude usage"""
    print("\n" + "="*60)
    print("EXAMPLE 1: Using Claude")
    print("="*60)
    
    try:
        provider = get_provider('claude', api_key='your-anthropic-key')
        
        # Initialize (test connection)
        print("Initializing Claude provider...")
        if await provider.initialize():
            print("✓ Connected to Claude API")
            
            # Generate a response
            print("\nGenerating response...")
            response = await provider.generate(
                "What is the meaning of life?",
                temperature=0.7,
                max_tokens=200
            )
            print(f"Response: {response}")
            
            # Cleanup
            await provider.close()
    except Exception as e:
        print(f"Error: {e}")


# ============================================================================
# Example 2: Using ChatGPT (OpenAI)
# ============================================================================

async def example_chatgpt():
    """Example: ChatGPT with different models"""
    print("\n" + "="*60)
    print("EXAMPLE 2: Using ChatGPT")
    print("="*60)
    
    try:
        # Try different models
        models = ['gpt-4-turbo-preview', 'gpt-4', 'gpt-3.5-turbo']
        
        for model_id in models:
            provider = get_provider(
                'openai',
                api_key='your-openai-key',
                model_id=model_id
            )
            
            if await provider.initialize():
                print(f"\n✓ Using {model_id}")
                
                response = await provider.generate(
                    "Explain quantum computing in 50 words",
                    max_tokens=100
                )
                print(f"Response: {response[:100]}...")
                
                await provider.close()
    except Exception as e:
        print(f"Error: {e}")


# ============================================================================
# Example 3: Streaming Responses
# ============================================================================

async def example_streaming():
    """Example: Streaming text generation"""
    print("\n" + "="*60)
    print("EXAMPLE 3: Streaming Responses")
    print("="*60)
    
    try:
        provider = get_provider('claude', api_key='your-anthropic-key')
        
        if await provider.initialize():
            print("Streaming Claude response:\n")
            
            # Stream the response token by token
            async for token in provider.stream_generate(
                "Write a short haiku about AI"
            ):
                print(token, end='', flush=True)
            
            print("\n")
            await provider.close()
    except Exception as e:
        print(f"Error: {e}")


# ============================================================================
# Example 4: Model Information
# ============================================================================

async def example_model_info():
    """Example: Getting model information"""
    print("\n" + "="*60)
    print("EXAMPLE 4: Model Information")
    print("="*60)
    
    try:
        provider = get_provider('claude')
        
        # List all available models
        print("Available Claude models:")
        models = await provider.list_models()
        for model in models:
            print(f"\n  {model.name}")
            print(f"    ID: {model.id}")
            print(f"    Context: {model.context_window:,} tokens")
            print(f"    Max Output: {model.max_output} tokens")
            print(f"    Vision Support: {model.supports_vision}")
            print(f"    Cost: ${model.cost_per_1k_input}/1K input tokens")
            print(f"    Cost: ${model.cost_per_1k_output}/1K output tokens")
    except Exception as e:
        print(f"Error: {e}")


# ============================================================================
# Example 5: Using Google Gemini
# ============================================================================

async def example_gemini():
    """Example: Google Gemini provider"""
    print("\n" + "="*60)
    print("EXAMPLE 5: Using Google Gemini")
    print("="*60)
    
    try:
        provider = get_provider(
            'gemini',
            api_key='your-google-key',
            model_id='gemini-1.5-pro'
        )
        
        if await provider.initialize():
            print("✓ Connected to Gemini API")
            
            # Gemini supports large context
            response = await provider.generate(
                "Summarize the history of AI",
                max_tokens=500
            )
            print(f"Response: {response[:200]}...")
            
            await provider.close()
    except Exception as e:
        print(f"Error: {e}")


# ============================================================================
# Example 6: Using Local Ollama
# ============================================================================

async def example_ollama():
    """Example: Local Ollama provider (no API key needed)"""
    print("\n" + "="*60)
    print("EXAMPLE 6: Using Local Ollama")
    print("="*60)
    print("(Make sure Ollama is running: ollama serve)")
    
    try:
        provider = get_provider('ollama', model_id='llama2')
        
        if await provider.initialize():
            print("✓ Connected to local Ollama")
            
            # Generate using local model
            response = await provider.generate(
                "What is machine learning?",
                temperature=0.5,
                max_tokens=300
            )
            print(f"Response: {response}")
            
            await provider.close()
    except Exception as e:
        print(f"Error (make sure Ollama is running): {e}")


# ============================================================================
# Example 7: Switching Between Providers
# ============================================================================

async def example_provider_switching():
    """Example: Using multiple providers with the same prompt"""
    print("\n" + "="*60)
    print("EXAMPLE 7: Provider Switching")
    print("="*60)
    
    prompt = "What is artificial intelligence?"
    
    providers_config = [
        ('claude', {'api_key': 'your-anthropic-key'}),
        ('openai', {'api_key': 'your-openai-key'}),
        ('gemini', {'api_key': 'your-google-key'}),
    ]
    
    for provider_name, config in providers_config:
        try:
            provider = get_provider(provider_name, **config)
            
            if await provider.initialize():
                print(f"\n{provider_name.upper()}:")
                response = await provider.generate(prompt, max_tokens=100)
                print(f"  {response[:100]}...")
                await provider.close()
        except Exception as e:
            print(f"  Error: {str(e)[:50]}")


# ============================================================================
# Example 8: Error Handling
# ============================================================================

async def example_error_handling():
    """Example: Proper error handling"""
    print("\n" + "="*60)
    print("EXAMPLE 8: Error Handling")
    print("="*60)
    
    from byteflow.ai_providers.base import (
        ProviderAuthError, ProviderConnectionError,
        ProviderError
    )
    
    try:
        # Try with invalid key
        provider = get_provider('claude', api_key='invalid-key')
        await provider.initialize()
    except ProviderAuthError as e:
        print(f"✓ Caught auth error: {e}")
    except ProviderConnectionError as e:
        print(f"✓ Caught connection error: {e}")
    except ProviderError as e:
        print(f"✓ Caught provider error: {e}")


# ============================================================================
# Example 9: Custom Configuration
# ============================================================================

async def example_custom_config():
    """Example: Custom provider configuration"""
    print("\n" + "="*60)
    print("EXAMPLE 9: Custom Configuration")
    print("="*60)
    
    from byteflow.ai_providers import ProviderConfig
    from byteflow.ai_providers.base import AccessType
    
    config = ProviderConfig(
        provider_name='claude',
        access_type=AccessType.API,
        api_key='your-key',
        model_id='claude-opus-4-6',
        temperature=0.3,  # More deterministic
        max_tokens=2048,
        top_p=0.9,
        system_prompt="You are an expert Python programmer",
        use_cache=True,
        cache_ttl=3600,
        max_retries=3,
        retry_delay=1.0,
        request_timeout=60,
    )
    
    print("Custom configuration created:")
    print(f"  Provider: {config.provider_name}")
    print(f"  Access Type: {config.access_type.value}")
    print(f"  Temperature: {config.temperature}")
    print(f"  Max Tokens: {config.max_tokens}")
    print(f"  System Prompt: {config.system_prompt[:50]}...")


# ============================================================================
# Example 10: Integration with ByteFlow Agent
# ============================================================================

async def example_byteflow_integration():
    """Example: Using providers with ByteFlow Agent"""
    print("\n" + "="*60)
    print("EXAMPLE 10: ByteFlow Agent Integration")
    print("="*60)
    
    try:
        from byteflow.agent import Agent
        
        # Create a provider
        provider = get_provider('claude', api_key='your-key')
        
        # Use with ByteFlow Agent
        agent = Agent(
            provider=provider,
            personality="You are a helpful Python coding assistant"
        )
        
        print("✓ Created Agent with Claude provider")
        print("  Agent can now use any AI provider!")
        
    except ImportError:
        print("ByteFlow Agent not available in this context")
    except Exception as e:
        print(f"Error: {e}")


# ============================================================================
# Example 11: List Available Providers
# ============================================================================

async def example_list_providers():
    """Example: List all available providers"""
    print("\n" + "="*60)
    print("EXAMPLE 11: Available Providers")
    print("="*60)
    
    providers = list_providers()
    print(f"Available providers: {', '.join(providers)}\n")
    
    # Show info for each
    provider_aliases = {
        'claude': 'Anthropic Claude',
        'openai': 'OpenAI ChatGPT',
        'google': 'Google Gemini',
        'grok': 'X Grok',
        'ollama': 'Local Ollama',
    }
    
    for provider_name in providers:
        alias = provider_aliases.get(provider_name, provider_name)
        print(f"  • {provider_name:12} → {alias}")


# ============================================================================
# Example 12: Batch Processing
# ============================================================================

async def example_batch_processing():
    """Example: Process multiple prompts"""
    print("\n" + "="*60)
    print("EXAMPLE 12: Batch Processing")
    print("="*60)
    
    prompts = [
        "What is AI?",
        "Explain machine learning",
        "What is deep learning?",
    ]
    
    try:
        provider = get_provider('claude', api_key='your-key')
        
        if await provider.initialize():
            print("Processing batch of prompts...\n")
            
            for i, prompt in enumerate(prompts, 1):
                try:
                    response = await provider.generate(
                        prompt,
                        max_tokens=100
                    )
                    print(f"{i}. {prompt}")
                    print(f"   Response: {response[:80]}...\n")
                except Exception as e:
                    print(f"{i}. Error: {e}\n")
            
            await provider.close()
    except Exception as e:
        print(f"Error: {e}")


# ============================================================================
# Main Entry Point
# ============================================================================

async def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("ByteFlow AI Providers - Usage Examples")
    print("="*60)
    
    # Note: Most examples require API keys
    print("\nNOTE: Most examples require valid API keys set:")
    print("  - ANTHROPIC_API_KEY (for Claude)")
    print("  - OPENAI_API_KEY (for ChatGPT)")
    print("  - GOOGLE_API_KEY (for Gemini)")
    print("  - XAI_API_KEY (for Grok)")
    print("  - Ollama running locally (for Ollama)")
    
    print("\nRunning available examples...\n")
    
    # Run examples that don't require API keys or gracefully handle missing keys
    await example_list_providers()
    await example_model_info()
    await example_custom_config()
    await example_error_handling()
    
    print("\n" + "="*60)
    print("To run the full examples, set your API keys:")
    print("  export ANTHROPIC_API_KEY=sk-ant-...")
    print("  export OPENAI_API_KEY=sk-...")
    print("  export GOOGLE_API_KEY=...")
    print("  export XAI_API_KEY=...")
    print("="*60)


if __name__ == '__main__':
    asyncio.run(main())
