# 🧠 ByteFlow Companion - Web Interface

Beautiful circular AI companion for intelligent data extraction and lead generation.

## 🎯 Features

### Lead Generator
- **Find Local Businesses** - Search for businesses needing your services
- **Smart Qualification** - AI-powered lead scoring and qualification
- **Contact Management** - Track interactions and mark contacted leads
- **Export Data** - Export to CSV, JSON, or other formats

### Intelligence Agent
- **Web Data Extraction** - Extract structured data from any website
- **Adaptive Strategies** - Automatically chooses best extraction method
- **Quality Scoring** - Validates data completeness and accuracy
- **Iterative Refinement** - Keeps improving until quality threshold met

## 🚀 Quick Start

### Windows

#### Option 1: Batch Script (Easiest)
```bash
START_COMPANION.bat
```

#### Option 2: PowerShell
```powershell
powershell -ExecutionPolicy Bypass -File START_COMPANION.ps1
```

#### Option 3: Manual
```bash
# Create virtual environment
python -m venv venv

# Activate
venv\Scripts\activate.bat

# Install dependencies
pip install -r requirements.txt

# Run server
python -m byteflow.web_companion
```

### macOS/Linux

```bash
# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
python -m byteflow.web_companion
```

### Then Open Browser
```
http://localhost:5000
```

## 🎨 User Interface

### Circular Companion Design
- **Animated Orange Circle** - Central focal point
- **Tracking Eyes** - Follow your mouse movements
- **Waveform Visualization** - Shows activity/listening state
- **Status Indicator** - Green dot shows system status

### Control Panel
- **Search Tab** - Lead generation search
- **Extract Tab** - Data extraction from URLs
- **Activity Tab** - History of all operations

## 📖 Usage Examples

### Lead Generation

1. **Select Mode**: "🎯 Lead Generator"
2. **Enter Query**: "restaurants in New York"
3. **Click Search**: System finds and qualifies leads
4. **View Results**: Shows number found, quality score, time taken
5. **Export**: Download as CSV or JSON

### Data Extraction

1. **Select Tab**: "Extract"
2. **Enter URL**: `https://example.com`
3. **Specify Fields**: "name, price, rating"
4. **Click Extract**: Analyzes page and extracts data
5. **View Quality**: Shows completeness and accuracy scores
6. **Export**: Save results

## 🔧 API Endpoints

### Search
```
POST /api/search
Content-Type: application/json

{
  "query": "restaurants in NYC",
  "mode": "lead"  // or "intelligence"
}

Response:
{
  "success": true,
  "found": 12,
  "quality": 0.92,
  "time": 2.3,
  "leads": [...]
}
```

### Extract
```
POST /api/extract
Content-Type: application/json

{
  "url": "https://example.com",
  "fields": ["name", "price"],
  "data_type": "products"
}

Response:
{
  "success": true,
  "quality": 0.88,
  "items": 45,
  "data": [...]
}
```

### History
```
GET /api/history?limit=20

Response:
{
  "history": [
    {
      "type": "success",
      "message": "Found 12 leads",
      "timestamp": "2024-01-28T10:30:00"
    }
  ]
}
```

### Stats
```
GET /api/stats

Response:
{
  "total_operations": 42,
  "successful": 39,
  "failures": 3,
  "accuracy": "92.9%"
}
```

## 📊 Configuration

Edit `byteflow/settings.py` to customize:

```python
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

INTELLIGENCE_CONFIG = {
    "quality_threshold": 0.75,
    "max_attempts": 5,
    "strategies": ["default", "table", "list", "nested", "specific"]
}
```

## 🎯 Services

### Sellable Services
- **Website Creation** - $500-2000 setup, 70-80% margin
- **SEO Optimization** - $300-1000/month, 80% margin
- **WhatsApp Bot** - $200-500 setup + $100-200/month
- **Mobile Optimization** - $300-800 setup, 75% margin
- **Social Media Management** - $500-2000/month, 70% margin

## 📚 File Structure

```
ByteFlow/
├── byteflow/
│   ├── web_companion.py          # Flask server
│   ├── lead_generation_companion.py
│   ├── intelligence_companion.py
│   ├── templates/
│   │   └── companion.html        # Main UI
│   └── static/                   # CSS/JS assets
├── START_COMPANION.bat           # Windows batch
├── START_COMPANION.ps1           # Windows PowerShell
├── requirements.txt              # Dependencies
└── COMPANION_README.md           # This file
```

## 🔌 Integration

### Flask Integration
```python
from byteflow.web_companion import app

# Add custom routes
@app.route('/custom')
def custom():
    return 'Custom route'

# Run
if __name__ == '__main__':
    app.run(port=5000)
```

### Python API Usage
```python
from byteflow.lead_generation_companion import LeadCompanion
from byteflow.intelligence_companion import IntelligenceCompanion

# Lead Generator
lead = LeadCompanion()
results = await lead.search_leads("restaurants NYC")

# Intelligence Agent
intel = IntelligenceCompanion()
data = await intel.extract_from_query("Find product names and prices")
```

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Windows: Find process on port 5000
netstat -ano | findstr :5000

# Kill process
taskkill /PID <PID> /F

# Or change port in code:
app.run(port=5001)
```

### Python Not Found
- Install Python 3.8+
- Add Python to PATH
- Use full path: `C:\Python39\python.exe -m byteflow.web_companion`

### Dependencies Error
```bash
# Upgrade pip
pip install --upgrade pip

# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

### No Results Found
- Check search query is specific enough
- Verify internet connection
- Check if crawl4ai is installed: `pip install crawl4ai`

## 📈 Performance Tips

1. **Increase Max Results** - Fetch more leads at once
2. **Use Filters** - Narrow down by service type
3. **Parallel Processing** - Handle multiple queries
4. **Cache Results** - Avoid duplicate searches
5. **Optimize Extraction** - Use specific fields

## 🔐 Security

- ✅ Local data storage only
- ✅ CORS enabled for API
- ✅ No external data transmission
- ✅ No authentication required (add if needed)

```python
# To add authentication:
from flask_httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()

@app.route('/api/search')
@auth.login_required
def search():
    ...
```

## 📞 Support

### Common Issues
1. **Slow extraction** - May be site-dependent
2. **Low quality scores** - Refine search terms
3. **Connection errors** - Check internet and URLs

### Improvements Coming
- [ ] Voice input support
- [ ] Real-time notifications
- [ ] Advanced filtering UI
- [ ] Database integration
- [ ] Mobile app companion

## 📄 License

ByteFlow is your project - use freely and modify as needed.

## 🎉 Next Steps

1. ✅ Run START_COMPANION.bat
2. ✅ Open http://localhost:5000
3. ✅ Try Lead Generator search
4. ✅ Try data extraction
5. ✅ Export results
6. ✅ Customize configuration

---

**ByteFlow Companion** - Making data extraction and lead generation beautiful and easy.
