# 🚀 Lead Generation Companion for ByteFlow

An intelligent **AI-powered lead generation system** that identifies and qualifies businesses needing your digital services.

## 🎯 What It Does

Automatically finds businesses that:
- ✅ Have high Google ratings but **no website**
- ✅ Are **not SEO optimized** for search
- ✅ **Need WhatsApp bot** for customer service
- ✅ Lack **mobile optimization**
- ✅ Have **weak social media presence**

Then generates leads with:
- 📊 Confidence scores (0-100%)
- 🏆 Priority levels (hot/medium/low)
- 📝 Specific service recommendations
- 📧 Ready-to-send outreach messages
- 📊 Exportable lists for campaigns

## 💰 Business Model

Sell these high-margin services to identified leads:

| Service | Setup Price | Monthly | Margin |
|---------|-------------|---------|--------|
| Website Creation | $500-2000 | - | 70-80% |
| SEO Optimization | - | $300-1000 | 80% |
| WhatsApp Bot | $200-500 | $50-200 | 75% |
| Mobile Optimization | $300-800 | - | 75% |
| Social Media Mgmt | - | $500-2000 | 70% |

**Example**: Generate 50 leads/month × 20% conversion × $500 avg = **$5,000 MRR**

## 🚀 Quick Start (5 minutes)

### 1. Install Dependencies
```bash
pip install -r requirements_lead_generation.txt
```

### 2. Start the Companion
```bash
# Windows
START_LEAD_GENERATION.bat

# macOS/Linux
python -m byteflow.lead_generation_companion
```

### 3. Search for Businesses
```
🤖 > search clothing shops New York
🤖 > filter website_creation
🤖 > export website_creation
🤖 > hot
```

That's it! You now have a list of ready-to-contact leads.

## 📊 How It Works

### Step 1: Search
Searches business directories for matches
```
Query: "clothing shops New York"
Results: 10 businesses found
```

### Step 2: Crawl
Analyzes each business website with crawl4ai
```
✓ Website assessment
✓ Mobile friendliness check
✓ SEO indicators
✓ Contact info detection
```

### Step 3: Qualify with AI
Uses Phi4-mini to identify service needs
```
Phi4-mini Analysis:
  Rating: 4.7⭐
  No Website: YES → website_creation
  Not SEO: YES → seo_optimization
  Local Business: YES → whatsapp_bot
  Confidence: 90%
```

### Step 4: Store & Export
Saves qualified leads for outreach
```
📊 Generated 7 qualified leads
📧 Ready-to-send messages created
📝 CSV export available
```

## 💻 Usage Examples

### CLI Usage

```bash
# Basic search
search restaurants Los Angeles

# Filter by service type
filter website_creation
filter seo_optimization
filter whatsapp_bot

# Export for outreach
export website_creation      # Creates: leads_export_YYYYMMDD.csv

# View high-priority leads
hot

# Get statistics
stats

# Mark business as contacted (removes from hot leads)
mark "Best Pizza Shop"
```

### Python Usage

```python
import asyncio
from byteflow.lead_generation_companion import LeadCompanion

async def find_leads():
    companion = LeadCompanion()
    
    # Search for businesses
    results = await companion.search_leads(
        query="coffee shops New York",
        limit=10
    )
    
    # Get filtered leads
    web_leads = companion.filter_leads('website_creation')
    
    # Get outreach list
    outreach = companion.get_outreach_list('whatsapp_bot')
    
    # Export to CSV
    csv_file = companion.export_to_csv('seo_optimization')
    
    # View stats
    stats = companion.get_stats()
    print(f"Total leads: {stats['total_leads']}")
    print(f"Hot leads: {stats['hot_leads']}")

asyncio.run(find_leads())
```

### Integration with ByteFlow Agent

```python
from byteflow.companion import Companion
from byteflow.lead_generation_companion import LeadCompanion

class LeadAgent(Companion):
    def __init__(self):
        super().__init__()
        self.lead_finder = LeadCompanion(agent=self)
    
    async def find_leads_cmd(self, query):
        """!find-leads "clothing shops NYC" """
        result = await self.lead_finder.search_leads(query, limit=10)
        return f"Found {len(result['leads'])} qualified leads"
```

## 🏆 Lead Scoring Algorithm

Confidence score combines multiple factors:

```
Score = 
  (high_rating: 0.3) +           # ≥4.0 stars
  (no_website: 0.3) +             # Missing online presence
  (active_business: 0.2) +        # 10+ reviews
  (local_business: 0.2)           # Retail/Restaurant/Service
```

**Priority Levels**:
- 🔥 **HIGH**: 4.5+ rating + no website + 20+ reviews + not contacted
- 📌 **MEDIUM**: Any lead with needs but doesn't meet all high criteria
- 📊 **LOW**: Leads with weak signals

## 📈 Services to Sell

### 1. Website Creation
**Target**: High-rated businesses with no website

Pitch:
```
"You're amazing at what you do (4.7⭐ from 150 customers!), 
but people can't find you online. Let's fix that 
with a professional website + your own phone line system."
```

**Delivery**: WordPress, Webflow, or custom HTML
**Timeline**: 2-4 weeks
**Upsell**: SEO, WhatsApp bot, mobile app

### 2. SEO Optimization
**Target**: Businesses not showing up in local search

Features to offer:
- Google My Business optimization
- Local keyword targeting
- Schema markup
- Mobile optimization
- Page speed improvements
- Backlink building

**Package**: $300-1000/month (recurring 💰)

### 3. WhatsApp Bot Integration
**Target**: Customer service heavy businesses (retail, restaurants, services)

Features:
- Order taking/reservations
- FAQ responses
- Appointment booking
- Payment collection
- Broadcast campaigns

**Package**: $200 setup + $100-200/month (recurring 💰)

### 4. Mobile Optimization
**Target**: Businesses with non-responsive websites

Services:
- Responsive design overhaul
- Mobile-first redesign
- App development
- Progressive Web App

**Package**: $300-800 one-time or $100-300/month

### 5. Social Media Management
**Target**: Businesses with <1000 followers

Channels:
- Instagram content creation
- Facebook ads management
- TikTok videos
- Engagement tracking

**Package**: $500-2000/month (recurring 💰)

## 📂 File Structure

```
ByteFlow/
├── byteflow/
│   ├── lead_finder.py                    # Core lead finding logic
│   ├── lead_generation_companion.py      # Main companion class
│   └── settings.py                       # (updated with lead settings)
├── SETUP_LEAD_GENERATION.md              # Setup guide
├── LEAD_GENERATION_README.md             # This file
├── requirements_lead_generation.txt      # Dependencies
├── START_LEAD_GENERATION.bat             # Windows startup
├── START_LEAD_GENERATION.ps1             # PowerShell startup
├── examples_lead_generation.py           # Usage examples
└── leads_database.json                   # Stored leads (created on first run)
```

## 🔧 Configuration

Edit `byteflow_settings.json`:

```json
{
  "lead_generation_enabled": true,
  "lead_model": "phi4-mini",              # LLM for analysis
  "lead_crawl_enabled": true,             # Enable web crawling
  "lead_min_confidence": 0.6,             # Only shows 60%+ confidence
  "lead_target_services": [
    "website_creation",
    "seo_optimization",
    "whatsapp_bot",
    "mobile_optimization"
  ]
}
```

## 📊 Data Storage

Leads stored in `leads_database.json`:

```json
{
  "name": "Best Clothing Store",
  "category": "retail",
  "rating": 4.7,
  "review_count": 125,
  "phone": "+1-555-0101",
  "address": "123 Main St, New York, NY",
  "has_website": false,
  "is_seo_optimized": false,
  "needs": ["website_creation", "seo_optimization", "whatsapp_bot"],
  "confidence": 0.92,
  "priority": "high",
  "reasoning": "Highly rated (4.7⭐) with no website...",
  "added_at": "2024-01-15T10:30:00",
  "contacted": false
}
```

## 🚀 Scaling Tips

### Local Optimization
1. **Start small**: Search 5-10 businesses at a time
2. **Geographic focus**: Master one city first
3. **Niche targeting**: Focus on one business type (e.g., all salons)
4. **Track conversion**: Log which services sell best

### Scaling Outreach
1. **CSV export**: Use for bulk WhatsApp messaging
2. **CRM integration**: Connect to HubSpot/Salesforce
3. **Email campaigns**: Combine with ConvertKit/ActiveCampaign
4. **Automation**: Schedule daily searches for your top niches

### Advanced Integration
```python
# Integrate with Zapier
lead_data → Zapier → WhatsApp/Email/Slack

# Sync to CRM
lead_data → HubSpot/Salesforce

# Custom webhook
await post_to_webhook(lead_data)
```

## 🤝 Integration Examples

### With Telegram Bot
```python
from telegram import Bot

async def send_hot_leads_telegram(bot_token, chat_id):
    companion = LeadCompanion()
    hot = companion.get_hot_leads(5)
    
    message = "🔥 Hot Leads:\n"
    for lead in hot:
        message += f"• {lead['name']} ({lead['confidence']:.0%})\n"
    
    bot = Bot(token=bot_token)
    await bot.send_message(chat_id=chat_id, text=message)
```

### With Discord Webhook
```python
import aiohttp

async def send_to_discord(webhook_url):
    companion = LeadCompanion()
    hot = companion.get_hot_leads(10)
    
    async with aiohttp.ClientSession() as session:
        await session.post(webhook_url, json={
            "content": f"Found {len(hot)} hot leads today! 🔥"
        })
```

### With Email (Gmail)
```python
import smtplib

async def email_daily_digest():
    companion = LeadCompanion()
    hot = companion.get_hot_leads()
    
    # Build HTML email with hot leads
    # Send via Gmail SMTP
```

## 🆘 Troubleshooting

### "crawl4ai not found"
```bash
pip install crawl4ai
```

### "No leads found"
- Try different search terms
- Check internet connection
- Reduce `limit` parameter
- Add city/state to search (e.g., "salons Miami Florida")

### "Slow performance"
- Use `limit=5` for testing
- Process in batches
- Run during off-peak hours
- Check phi4-mini model size

### "Low confidence scores"
- Check your min_confidence setting
- Adjust qualification rules in `lead_finder.py`
- Look for businesses with more reviews

## 📝 License

Same as ByteFlow

## 🎓 Learn More

- **crawl4ai**: https://github.com/unclecode/crawl4ai
- **Phi4-mini**: https://huggingface.co/microsoft/phi-4-mini
- **ByteFlow**: https://github.com/byteflowai/byteflow

## 💬 Support

Issues? Check:
1. Requirements installed: `pip list | grep crawl4ai`
2. Python version: `python --version` (needs 3.8+)
3. API keys/credentials configured
4. Examples: `python examples_lead_generation.py`

---

**Made with ❤️ for digital entrepreneurs**

Start finding qualified leads today! 🚀
