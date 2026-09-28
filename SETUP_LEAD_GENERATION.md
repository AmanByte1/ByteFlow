# 🚀 Lead Generation Companion Setup Guide

## Overview
The **Lead Generation Companion** is an AI-powered tool to find and qualify businesses that need your digital services:
- 🌐 Website Creation
- 📊 SEO Optimization  
- 💬 WhatsApp Bot Integration
- 📱 Mobile Optimization
- 📈 Social Media Marketing

## Installation

### 1. Install Required Dependencies

```bash
# Install crawl4ai for web scraping
pip install crawl4ai

# Install phi4-mini (if using locally)
pip install ollama

# Other dependencies
pip install asyncio aiohttp
```

### 2. Enable Lead Generation in ByteFlow

The lead generation module is already integrated! Just enable it in settings:

**Via CLI:**
```bash
# Start the lead generation companion
python -m byteflow.lead_generation_companion
```

**Via ByteFlow Settings JSON:**
```json
{
  "lead_generation_enabled": true,
  "lead_model": "phi4-mini",
  "lead_crawl_enabled": true,
  "lead_min_confidence": 0.6,
  "lead_target_services": [
    "website_creation",
    "seo_optimization", 
    "whatsapp_bot"
  ]
}
```

## Quick Start

### Run the Interactive CLI

```bash
python byteflow/lead_generation_companion.py
```

You'll see:
```
╔════════════════════════════════════════════════════════════╗
║       Lead Generation Companion v1.0                       ║
║  Find & qualify businesses that need your services         ║
╚════════════════════════════════════════════════════════════╝

Commands:
  search <query>      Search for businesses
  filter <service>    Filter by service type
  export <service>    Export to CSV
  hot                 Show hot leads
  stats               Statistics
  mark <name>         Mark as contacted
  help                Show help
  exit                Exit
```

### Example Commands

```bash
# Search for high-value targets
search clothing shops New York
search restaurants Los Angeles  
search hair salons Miami
search plumbing contractors Chicago

# Filter for specific service
filter website_creation
filter seo_optimization
filter whatsapp_bot

# Export leads for outreach
export website_creation

# View top priority leads
hot

# Mark business as contacted
mark "Best Clothing Store"

# See statistics
stats
```

## How It Works

### 1️⃣ Search & Crawl
- Searches Google Maps / business directories
- Finds businesses matching your search
- Crawls their websites (if they have one)

### 2️⃣ Analyze with Phi4-mini
The LLM analyzes each business to identify needs:

**Website Creation**: High rating + No website = Lead
```
Rating: 4.7⭐ | No Website | → NEEDS: Website Creation
```

**SEO Optimization**: Not optimized for search
```
No Meta Tags | No Mobile Friendly | → NEEDS: SEO
```

**WhatsApp Bot**: Local business without bot
```
Restaurant/Retail | Manual Orders | → NEEDS: WhatsApp Bot
```

### 3️⃣ Qualify & Score
Each lead gets:
- **Confidence Score**: 0-100% likelihood they'll convert
- **Priority Level**: High/Medium/Low
- **Specific Needs**: List of services they need
- **Reasoning**: Why they're a good fit

### 4️⃣ Store & Track
- All leads stored in `leads_database.json`
- Track contact history
- Export for bulk outreach

## Lead Qualification Logic

### High Priority Leads
Automatically marked as "hot" if:
- ✅ Rating ≥ 4.5 stars
- ✅ No website OR not SEO optimized
- ✅ 20+ customer reviews (active business)
- ✅ Not yet contacted

### Scoring Formula
```
Confidence = (has_high_rating × 0.3) +
             (no_website × 0.3) +
             (active_business × 0.2) +
             (local_business × 0.2)
```

## Integration with ByteFlow

### Use in Custom Companions
```python
from byteflow.lead_generation_companion import LeadCompanion

# Create companion
lead_finder = LeadCompanion(agent=your_agent, model="phi4-mini")

# Search for businesses
results = await lead_finder.search_leads("clothing shops New York", limit=10)

# Get hot leads
hot_leads = lead_finder.get_hot_leads()

# Export for outreach
csv_file = lead_finder.export_to_csv("website_creation")
```

### Add as ByteFlow Plugin
Edit `byteflow/companion.py` to add lead generation commands:

```python
@self.register_command('generate_leads', 'Find businesses needing services')
async def cmd_generate_leads(self, args):
    from .lead_generation_companion import LeadCompanion
    companion = LeadCompanion()
    results = await companion.search_leads(' '.join(args), limit=10)
    return f"Found {len(results['leads'])} qualified leads"
```

## Services You Can Sell

### 1. Website Creation
**Target**: Highly-rated businesses with no website
- Charge: $500-$2000 per site
- Tools: WordPress, Webflow, custom HTML

### 2. SEO Optimization  
**Target**: Businesses not optimized in search
- Charge: $300-$1000/month
- Focus: GMaps optimization, local SEO

### 3. WhatsApp Bot Integration
**Target**: Retail, restaurants, services
- Charge: $200-$500 setup + $50-$200/month
- Features: Order taking, customer support, appointments

### 4. Mobile Optimization
**Target**: Businesses with non-responsive sites
- Charge: $300-$800
- Tools: CSS frameworks, responsive design

### 5. Social Media Marketing
**Target**: Businesses with <1000 followers
- Charge: $500-$2000/month
- Platforms: Instagram, Facebook, TikTok

## Outreach Templates

The companion includes templates for WhatsApp, Email, and LinkedIn:

```python
# Customize in your settings:
lead_companion.settings['outreach_template'] = """
Hi {name}! 👋

I noticed {business} has excellent ratings ({rating}⭐) 
but could use a professional website + SEO optimization.

Would love to discuss! 💼

[Your contact info]
"""
```

## Database Structure

Leads are stored in `leads_database.json`:

```json
{
  "name": "Best Clothing Store",
  "rating": 4.7,
  "category": "retail",
  "phone": "+1-555-0101",
  "address": "123 Main St",
  "has_website": false,
  "is_seo_optimized": false,
  "needs": ["website_creation", "seo_optimization", "whatsapp_bot"],
  "confidence": 0.9,
  "priority": "high",
  "reasoning": "Highly rated (4.7⭐) with no website | Not SEO optimized | Local retail business",
  "added_at": "2024-01-15T10:30:00",
  "contacted": false
}
```

## API Reference

### LeadCompanion Class

```python
class LeadCompanion:
    async def search_leads(query: str, limit: int) -> dict
    def filter_leads(service: str) -> list
    def get_outreach_list(service: str) -> list
    def export_to_csv(service: str) -> str
    def get_hot_leads(limit: int) -> list
    def get_stats() -> dict
    def mark_contacted(business_name: str) -> dict
```

### LeadGenerationPipeline

```python
class LeadGenerationPipeline:
    async def generate_leads(query: str, limit: int) -> list
```

## Advanced Configuration

### Custom Qualification Rules

Edit `lead_finder.py` to change what qualifies as a lead:

```python
def _identify_needs(self, data: Dict) -> List[str]:
    needs = []
    
    # Add your custom rules:
    if data.get('phone_only'):
        needs.append('digital_presence')
    
    if data.get('no_email'):
        needs.append('email_marketing')
    
    return needs
```

### Using Different LLMs

```python
# With Anthropic Claude
companion = LeadCompanion(model="claude-3-sonnet")

# With OpenAI
companion = LeadCompanion(model="gpt-4")

# With local Ollama
companion = LeadCompanion(model="llama2-local")
```

## Troubleshooting

### crawl4ai not found
```bash
pip install crawl4ai
```

### API rate limits
Crawl4ai may be limited. Use `limit=5` for testing:
```python
results = await companion.search_leads("coffee shops NYC", limit=5)
```

### No leads found
Try different search queries:
- ✅ "clothing shops New York" 
- ✅ "restaurants Los Angeles"
- ✅ "salons Miami Florida"

### Slow analysis
- Reduce `limit` parameter
- Check if phi4-mini is installed
- Use smaller batches

## Next Steps

1. **Customize Services**: Edit target services in settings
2. **Create Outreach**: Use export functions to get CSV
3. **Track Results**: Mark contacted leads
4. **Scale Up**: Integrate with CRM (Salesforce, HubSpot)
5. **Automate**: Schedule daily lead searches

## Support

For issues with:
- **crawl4ai**: https://github.com/unclecode/crawl4ai
- **ByteFlow**: Check ByteFlow documentation
- **Phi4-mini**: https://huggingface.co/microsoft/phi-4-mini

---

Made with ❤️ for digital entrepreneurs
