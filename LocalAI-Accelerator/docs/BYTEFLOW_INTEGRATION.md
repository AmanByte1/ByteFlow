# LocalAI Accelerator + ByteFlow Integration Guide

Use LocalAI Accelerator with ByteFlow for optimized lead generation and data extraction with local AI.

## Quick Start

### 1. Install Both Projects

```bash
# LocalAI Accelerator
pip install localai-accelerator

# ByteFlow (already installed from your repo)
cd ByteFlow
pip install -r requirements.txt
```

### 2. Basic Integration

```python
from local_ai_accelerator import LocalAIAccelerator
from byteflow import ByteFlow

# Initialize
accelerator = LocalAIAccelerator()
accelerator.load_model("phi-2")
byteflow = ByteFlow()

# Use accelerator in ByteFlow for intelligent extraction
def extract_with_ai(website_url, query):
    # Crawl website
    data = byteflow.crawl(website_url)
    
    # Use accelerator for intelligent extraction
    prompt = f"""
    Extract business information from this data:
    {data}
    
    Query: {query}
    Provide structured JSON response.
    """
    
    response = accelerator.inference(
        prompt=prompt,
        model_name="phi-2",
        max_tokens=512
    )
    
    return response

# Usage
result = extract_with_ai(
    "https://example-business.com",
    "Extract company contact info and services"
)
print(result)
```

## Advanced Integration: ByteFlow Plugin

Create a reusable ByteFlow plugin with LocalAI Accelerator:

```python
from local_ai_accelerator import LocalAIAccelerator
from byteflow.plugin import BasePlugin
import json


class LocalAIPlugin(BasePlugin):
    """ByteFlow plugin for local AI-powered extraction"""
    
    name = "local_ai"
    version = "1.0.0"
    
    def __init__(self, model_name: str = "phi-2"):
        super().__init__()
        self.accelerator = LocalAIAccelerator()
        self.model_name = model_name
        self.accelerator.load_model(model_name)
    
    def extract_entities(self, text: str, entity_types: list) -> dict:
        """Extract specific entities from text"""
        prompt = f"""
        Extract the following entities from this text:
        Entity types: {', '.join(entity_types)}
        
        Text: {text}
        
        Return JSON format: {{"entity_type": ["value1", "value2"]}}
        """
        
        response = self.accelerator.inference(
            prompt=prompt,
            model_name=self.model_name,
            max_tokens=512
        )
        
        try:
            return json.loads(response)
        except:
            return {"error": response}
    
    def classify_content(self, text: str, categories: list) -> str:
        """Classify text into categories"""
        prompt = f"""
        Classify this text into one of these categories:
        {', '.join(categories)}
        
        Text: {text}
        
        Return only the category name.
        """
        
        response = self.accelerator.inference(
            prompt=prompt,
            model_name=self.model_name,
            max_tokens=50
        )
        
        return response.strip()
    
    def summarize(self, text: str, max_length: int = 100) -> str:
        """Summarize text"""
        prompt = f"""
        Summarize this text in {max_length} characters:
        
        {text}
        """
        
        response = self.accelerator.inference(
            prompt=prompt,
            model_name=self.model_name,
            max_tokens=100
        )
        
        return response[:max_length]
    
    def shutdown(self):
        """Clean up resources"""
        self.accelerator.shutdown()


# Usage with ByteFlow
def main():
    # Initialize plugin
    ai_plugin = LocalAIPlugin(model_name="phi-2")
    
    # Example 1: Extract business info
    business_text = """
    ABC Corporation is a software development company founded in 2010.
    They specialize in cloud solutions and AI integration.
    Contact: info@abc-corp.com, Phone: +1-555-123-4567
    """
    
    entities = ai_plugin.extract_entities(
        business_text,
        ["company_name", "industry", "email", "phone"]
    )
    print(f"Extracted entities: {entities}")
    
    # Example 2: Classify lead quality
    lead_description = """
    Active company with strong online presence, 
    multiple locations, enterprise clients
    """
    
    quality = ai_plugin.classify_content(
        lead_description,
        ["high_quality", "medium_quality", "low_quality"]
    )
    print(f"Lead quality: {quality}")
    
    # Example 3: Summarize company info
    company_info = """
    TechFlow Solutions is a leading provider of digital transformation services.
    With 15 years in the industry, we've helped 500+ companies modernize their operations.
    Our services include cloud migration, AI implementation, and data analytics.
    We have offices in New York, London, Singapore, and Toronto.
    """
    
    summary = ai_plugin.summarize(company_info)
    print(f"Summary: {summary}")
    
    # Cleanup
    ai_plugin.shutdown()


if __name__ == "__main__":
    main()
```

## Performance with ByteFlow

### Lead Generation Optimization

```python
from local_ai_accelerator import LocalAIAccelerator
from byteflow.lead_finder import LeadQualifier

accelerator = LocalAIAccelerator()
accelerator.load_model("phi-2")

# Custom lead qualifier using AI
class AILeadQualifier(LeadQualifier):
    def qualify(self, lead_data):
        prompt = f"""
        Evaluate this business lead:
        {lead_data}
        
        Score 1-10 based on:
        - Company size
        - Industry fit
        - Contact availability
        - Growth indicators
        
        Return JSON: {{"score": 0-10, "reason": "..."}}
        """
        
        result = accelerator.inference(
            prompt=prompt,
            model_name="phi-2",
            max_tokens=200
        )
        
        # Parse and return
        import json
        data = json.loads(result)
        return data["score"], data["reason"]

# Use with ByteFlow
qualifier = AILeadQualifier()
score, reason = qualifier.qualify(lead_data)
print(f"Lead Score: {score}/10 - {reason}")
```

## Batch Processing with Accelerator

Process multiple leads efficiently:

```python
from local_ai_accelerator import LocalAIAccelerator

accelerator = LocalAIAccelerator()
accelerator.load_model("phi-2")

# Batch process multiple leads
leads = [
    {"name": "ABC Corp", "industry": "Tech", "size": "100+"},
    {"name": "XYZ Inc", "industry": "Finance", "size": "50-100"},
    {"name": "123 LLC", "industry": "Retail", "size": "<50"},
]

prompts = [
    f"Is this a good lead? {lead}" 
    for lead in leads
]

# Process batch
results = accelerator.batch_inference(
    prompts=prompts,
    model_name="phi-2",
    max_tokens=100
)

for lead, result in zip(leads, results):
    print(f"{lead['name']}: {result[:100]}")
```

## Resource Management

LocalAI Accelerator automatically manages resources for ByteFlow:

```python
accelerator = LocalAIAccelerator()

# Check if enough resources for lead generation
stats = accelerator.get_resource_stats()
print(f"Available GPU: {stats['gpu_percent']}%")
print(f"Available RAM: {stats['ram_percent']}%")

# Get recommendations
specs = accelerator.get_system_specs()
print(f"Recommended batch size: {specs['recommended_batch_size']}")
print(f"Recommended model: {specs['recommended_model_size']}")

# Auto-select best model for your hardware
recommended_model = accelerator.recommend_model()
accelerator.load_model(recommended_model)
```

## Async Processing for Web Companion

Use async for faster response times:

```python
import asyncio
from local_ai_accelerator import LocalAIAccelerator, RequestPriority

async def process_user_query():
    accelerator = LocalAIAccelerator()
    accelerator.load_model("phi-2")
    
    # Submit request asynchronously
    response = await accelerator.inference_async(
        prompt="User question",
        model_name="phi-2",
        priority=RequestPriority.HIGH
    )
    
    return response

# In Flask route
@app.post("/api/chat")
async def chat():
    response = await process_user_query()
    return {"response": response}
```

## Monitoring & Logging

Track performance metrics:

```python
accelerator = LocalAIAccelerator()

# Get optimization report
report = accelerator.get_optimization_report()
print(f"Recommended model: {report['recommendations']['recommended_model']}")
print(f"Current GPU usage: {report['current_resources']['gpu_usage_percent']}%")

# Export metrics
metrics = {
    "system": accelerator.get_system_specs(),
    "resources": accelerator.get_resource_stats(),
    "queue": accelerator.request_optimizer.export_stats()
}

# Use for monitoring/logging
import json
print(json.dumps(metrics, indent=2))
```

## Troubleshooting

### Slow Responses
```python
# Check resource availability
stats = accelerator.get_resource_stats()
if stats['gpu_percent'] > 90:
    print("GPU at capacity, consider loading smaller model")

# Switch to smaller model
if current_model == "qwen-2.5-14b":
    accelerator.unload_model("qwen-2.5-14b")
    accelerator.load_model("phi-2")
```

### Memory Issues
```python
# Monitor memory
monitor = accelerator.resource_monitor
monitor.start()

# Unload unused models
loaded = accelerator.get_loaded_models()
for model in loaded:
    if model not in ["phi-2"]:  # Keep phi-2
        accelerator.unload_model(model)

# Clear cache
accelerator.request_optimizer.clear_old_results(max_age_seconds=300)
```

### High CPU Usage
```python
# Reduce concurrent requests
optimizer = accelerator.request_optimizer
optimizer.max_batch_size = 2  # Process 2 at a time instead of 4

# Or use priority queuing
await optimizer.submit_request(
    prompt="urgent query",
    priority=RequestPriority.HIGH
)
```

## Production Deployment

For production ByteFlow + LocalAI setup:

```yaml
# docker-compose.yml
version: '3.8'
services:
  byteflow:
    image: byteflow:latest
    environment:
      - LOCALAI_ENABLED=true
      - LOCALAI_MODEL=phi-2
      - LOCALAI_DEVICE=cuda
    ports:
      - "5000:5000"
    volumes:
      - ./models:/app/models
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## Summary

LocalAI Accelerator + ByteFlow gives you:
- ✅ **Fast inference** (1-2 seconds per response)
- ✅ **Intelligent resource management** (optimize CPU/GPU)
- ✅ **Smart request queuing** (handle multiple users)
- ✅ **Zero cloud dependency** (completely local)
- ✅ **Easy integration** (simple Python API)

**Start building with local AI today!** 🚀
