# 🚀 ByteFlow - Complete Setup Guide

## What is ByteFlow?

**ByteFlow** is an intelligent lead generation and web data extraction system with a beautiful circular companion interface. It combines:

- 🎯 **Lead Generator** - Find local businesses needing your services
- 🧠 **Intelligence Agent** - Extract structured data from any website
- 🎨 **Circular Companion UI** - Beautiful voice-assistant-like interface
- ⚡ **Fast & Scalable** - Built with Python, Flask, and crawl4ai

## 📋 System Requirements

### Minimum Requirements
- **Python 3.8+** - [Download here](https://www.python.org/downloads/)
- **4GB RAM** - For concurrent operations
- **Windows, macOS, or Linux** - Works on all platforms
- **Internet connection** - For web scraping and LLM calls

### Optional
- **Ollama** - For local LLM support
- **API Keys** - For Anthropic/OpenAI integration

## 🎯 Installation Steps

### Step 1: Download ByteFlow

```bash
# Extract ByteFlow.zip to a folder
unzip ByteFlow.zip
cd ByteFlow
```

### Step 2: Run Startup Script

#### Windows (Easiest)
**Double-click one of these:**
- `START_COMPANION.bat` - Standard batch script
- `START_COMPANION.ps1` - PowerShell script

The script will:
1. ✅ Check Python installation
2. ✅ Create virtual environment
3. ✅ Install all dependencies
4. ✅ Start the web server

#### macOS/Linux
```bash
# Make script executable
chmod +x start_companion.sh

# Run it
./start_companion.sh
```

#### Manual Setup
```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate.bat
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start server
python -m byteflow.web_companion
```

### Step 3: Open in Browser

```
http://localhost:5000
```

You should see the **ByteFlow Companion** with the circular orange AI interface.

## 🎨 Using the Companion

### Lead Generator

1. **Select Mode**: Click on "🎯 Lead Generator" tab
2. **Enter Search**: "restaurants in New York"
3. **Click Search**: System finds and qualifies leads
4. **View Results**: 
   - Number of leads found
   - Quality score (0-100%)
   - Time taken
5. **Export**: Download as CSV or JSON

### Intelligence Agent

1. **Select Tab**: "🔍 Extract"
2. **Enter URL**: `https://example.com`
3. **Specify Fields**: `name, price, rating`
4. **Click Extract**: Analyzes and extracts data
5. **View Quality**: Shows extraction quality score
6. **Export**: Save results in chosen format

### Activity Log

1. **Select Tab**: "📋 Activity"
2. **View History**: All operations and results
3. **See Success/Errors**: Color-coded feedback

## 📁 Project Structure

```
ByteFlow/
├── byteflow/                          # Main package
│   ├── __init__.py
│   ├── web_companion.py               # Flask server
│   ├── lead_generation_companion.py   # Lead generator
│   ├── intelligence_companion.py      # Data extraction
│   ├── lead_finder.py                 # Core lead engine
│   ├── smart_extractor.py             # Core extraction
│   ├── settings.py                    # Configuration
│   ├── templates/
│   │   └── companion.html             # Main UI
│   └── static/                        # CSS/JS assets
│
├── START_COMPANION.bat                # Windows startup
├── START_COMPANION.ps1                # PowerShell startup
├── requirements.txt                   # Python dependencies
│
├── examples_companion.py               # Usage examples
├── COMPANION_README.md                # Companion docs
├── SETUP_GUIDE.md                     # This file
├── QUICK_REFERENCE.md                 # Quick commands
└── LICENSE

```

## 🔧 Configuration

### Edit Settings

Open `byteflow/settings.py` to customize:

```python
# Lead Generation Config
LEAD_GENERATION_CONFIG = {
    "enabled": True,
    "model": "phi4-mini",
    "crawl_enabled": True,
    "min_confidence": 0.6,
    "target_services": [
        "website_creation",
        "seo_optimization",
        "whatsapp_bot"
    ]
}

# Intelligence Agent Config
INTELLIGENCE_CONFIG = {
    "quality_threshold": 0.75,    # 0-1, higher = stricter
    "max_attempts": 5,            # Max refinement attempts
    "strategies": [               # Extraction strategies
        "default",
        "table",
        "list",
        "nested",
        "specific"
    ]
}

# LLM Model
MODEL_CONFIG = {
    "provider": "ollama",         # ollama, anthropic, openai
    "model": "phi4-mini",
    "temperature": 0.3,
    "max_tokens": 1000
}
```

### Change Port

In `byteflow/web_companion.py`:

```python
if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5001,  # Change to your port
        debug=True
    )
```

## 📚 API Usage

### Python Script Example

```python
import asyncio
from byteflow.lead_generation_companion import LeadCompanion
from byteflow.intelligence_companion import IntelligenceCompanion

async def main():
    # Lead Generation
    lead = LeadCompanion()
    results = await lead.search_leads(
        query="restaurants in NYC",
        limit=10
    )
    print(f"Found {len(results['leads'])} leads")
    
    # Intelligence Agent
    intel = IntelligenceCompanion()
    data = await intel.extract_from_query(
        query="Extract product names and prices",
        urls=["https://example.com"]
    )
    print(f"Quality: {data['quality_score']:.0%}")

asyncio.run(main())
```

### REST API Example

```bash
# Search leads
curl -X POST http://localhost:5000/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "restaurants in NYC",
    "mode": "lead"
  }'

# Extract data
curl -X POST http://localhost:5000/api/extract \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "fields": ["name", "price"]
  }'

# Get history
curl http://localhost:5000/api/history?limit=20

# Get stats
curl http://localhost:5000/api/stats
```

## 🎯 Common Tasks

### Task 1: Find Leads for Website Creation Service

```python
from byteflow.lead_generation_companion import LeadCompanion
import asyncio

async def find_website_leads():
    lead = LeadCompanion()
    
    # Search
    results = await lead.search_leads(
        query="businesses without websites in Los Angeles",
        limit=50
    )
    
    # Filter for website creation needs
    filtered = await lead.filter_leads(
        leads=results['leads'],
        service="website_creation"
    )
    
    # Export
    filepath = await lead.export_to_csv(filtered)
    print(f"Exported to: {filepath}")

asyncio.run(find_website_leads())
```

### Task 2: Extract Product Data from E-commerce

```python
from byteflow.intelligence_companion import IntelligenceCompanion
import asyncio

async def extract_products():
    intel = IntelligenceCompanion()
    
    result = await intel.extract_from_query(
        query="Extract all products with names, prices, and ratings",
        urls=["https://example-store.com"]
    )
    
    print(f"Extracted {len(result['data'])} products")
    print(f"Quality: {result['quality_score']:.0%}")
    
    # Export
    await intel.export_results(result, format='csv')

asyncio.run(extract_products())
```

### Task 3: Monitor Lead Generation Progress

```python
from byteflow.lead_generation_companion import LeadCompanion
import asyncio

async def monitor_progress():
    lead = LeadCompanion()
    
    # Get current stats
    stats = await lead.get_stats()
    
    print(f"Total leads: {stats['total']}")
    print(f"Contacted: {stats['contacted']}")
    print(f"Remaining: {stats['total'] - stats['contacted']}")
    print(f"Conversion rate: {stats['contacted'] / stats['total']:.1%}")

asyncio.run(monitor_progress())
```

## 🐛 Troubleshooting

### Issue: "Python not found"

**Solution:**
1. Install Python from https://www.python.org
2. During install, check "Add Python to PATH"
3. Restart computer
4. Or use full path: `C:\Python39\python.exe -m byteflow.web_companion`

### Issue: "Port 5000 already in use"

**Solution:**
```bash
# Windows: Find and kill process
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Or change port in web_companion.py
app.run(port=5001)
```

### Issue: "crawl4ai not found"

**Solution:**
```bash
pip install crawl4ai --upgrade
```

### Issue: "No results found"

**Solution:**
- Check search query is specific enough
- Verify internet connection
- Try different search terms
- Check logs in Activity tab

### Issue: "Low quality scores"

**Solution:**
- Refine extraction query
- Specify exact fields needed
- Increase max_attempts in settings
- Try different data source

## 📈 Performance Tips

1. **Batch Processing** - Search multiple queries at once
2. **Filter Early** - Use service filters to narrow results
3. **Cache Results** - Avoid duplicate searches
4. **Optimize Fields** - Extract only needed fields
5. **Use Specific URLs** - Target exact pages vs homepages

## 🔐 Security Best Practices

- ✅ Data stored locally only
- ✅ No external transmission by default
- ✅ API is open (add auth if needed)
- ✅ Use HTTPS in production
- ✅ Validate all inputs

### Add Authentication

```python
from flask_httpauth import HTTPBasicAuth

auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    if username == 'admin' and password == 'secret':
        return username

@app.route('/api/search')
@auth.login_required
def search():
    # Protected route
    return jsonify(...)
```

## 🚀 Next Steps

1. ✅ **Run the Companion** - Execute START_COMPANION.bat
2. ✅ **Try Lead Search** - Search for businesses in your area
3. ✅ **Test Extraction** - Extract data from a website
4. ✅ **Export Results** - Download as CSV/JSON
5. ✅ **Customize Settings** - Adjust configuration
6. ✅ **Integrate with Your Tools** - Use the API
7. ✅ **Scale Up** - Bulk import leads into CRM

## 📞 Support & Help

### Check Documentation
- `COMPANION_README.md` - Feature overview
- `QUICK_REFERENCE.md` - Common commands
- `examples_companion.py` - Code examples

### View Activity Log
- Open web interface
- Click "Activity" tab
- See detailed operation history

### Debug Issues
- Check console output when running
- Review error messages in Activity tab
- Check Python version: `python --version`

## 🎉 You're All Set!

ByteFlow is now ready to use. Start finding leads and extracting data!

**Happy prospecting! 🚀**

---

**ByteFlow** - Making lead generation and data extraction intelligent, beautiful, and easy.
