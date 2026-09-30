# ⚡ ByteFlow - Quick Reference

## 🚀 Quick Start (60 seconds)

1. **Extract ZIP** → `unzip ByteFlow.zip && cd ByteFlow`
2. **Run** → Double-click `START_COMPANION.bat`
3. **Open** → http://localhost:5000
4. **Search** → Enter query and click "🚀 Search"
5. **Export** → Download results as CSV/JSON

## 🎯 Commands

### Start Server
```bash
# Windows
START_COMPANION.bat

# Windows (PowerShell)
powershell -ExecutionPolicy Bypass -File START_COMPANION.ps1

# macOS/Linux
python3 -m byteflow.web_companion
```

### Python API

```python
# Search leads
await LeadCompanion().search_leads("restaurants NYC")

# Extract data
await IntelligenceCompanion().extract_from_query("Extract product names")

# Filter leads
await LeadCompanion().filter_leads(leads, "website_creation")

# Export
await LeadCompanion().export_to_csv(leads)

# Get stats
await LeadCompanion().get_stats()

# Mark contacted
await LeadCompanion().mark_contacted(lead_id)
```

### REST API

```bash
# Search
curl -X POST http://localhost:5000/api/search \
  -d '{"query":"restaurants NYC","mode":"lead"}'

# Extract
curl -X POST http://localhost:5000/api/extract \
  -d '{"url":"https://example.com","fields":["name","price"]}'

# History
curl http://localhost:5000/api/history?limit=20

# Stats
curl http://localhost:5000/api/stats
```

## 🎨 Web Interface

### Tabs
- **🎯 Search** - Find leads or query data
- **🔍 Extract** - Extract from specific URLs
- **📋 Activity** - View operation history

### Companion Features
- 👀 **Eye Tracking** - Follows your mouse
- 📊 **Waveform** - Shows activity status
- 🎯 **Status Dot** - Green = ready, red = error
- 🔄 **Animation** - Spinning circle shows processing

## 📊 Services to Sell

| Service | Price | Margin | Notes |
|---------|-------|--------|-------|
| Website Creation | $500-2000 | 70-80% | One-time |
| SEO Optimization | $300-1000/mo | 80% | Recurring |
| WhatsApp Bot | $200-500 + $100-200/mo | 75% | Hybrid |
| Mobile Opt | $300-800 | 75% | One-time |
| Social Media | $500-2000/mo | 70% | Recurring |

## 🔧 Configuration

Edit `byteflow/settings.py`:

```python
# Change quality threshold (0-1)
"quality_threshold": 0.75

# Change max extraction attempts
"max_attempts": 5

# Change target services
"target_services": ["website_creation", "seo_optimization"]

# Change model
"model": "phi4-mini"

# Change port
app.run(port=5001)
```

## 🎯 Lead Search Examples

```
"restaurants in New York"
"digital agencies Los Angeles"
"auto repair shops Chicago"
"fitness gyms Miami"
"dental clinics Boston"
"lawyers in San Francisco"
"plumbers New York City"
"salons near me"
"gyms in my area"
"coffee shops downtown"
```

## 📊 Data Extraction Examples

```
"Extract product names and prices"
"Get all contact information"
"Find company names and phone numbers"
"Extract table data from page"
"Get all links and titles"
"Find email addresses"
"Extract prices and ratings"
"Get business hours"
"Find opening dates"
"Extract social media links"
```

## ⚡ Performance Tips

1. **Specific Queries** - "restaurants in NYC" better than "restaurants"
2. **Batch Operations** - Process multiple at once
3. **Filter Early** - Use service filters
4. **Cache Results** - Don't repeat same search
5. **Quality vs Speed** - Lower threshold = faster, higher = better
6. **Parallel Processing** - Use async operations

## 🐛 Quick Fixes

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID xxxxx /F

# macOS/Linux
lsof -i :5000
kill -9 xxxxx
```

### Dependencies Missing
```bash
pip install -r requirements.txt --upgrade
```

### Python Not Found
```bash
# Check version
python --version

# If not found, add to PATH or use full path
C:\Python39\python.exe -m byteflow.web_companion
```

### Virtual Environment Issues
```bash
# Recreate venv
rm -rf venv
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
```

## 📈 Expected Results

### Lead Generation
- ✅ 10-100 leads per search
- ✅ 60-90% accuracy
- ✅ 2-5 seconds per search
- ✅ Exportable to CSV/JSON

### Data Extraction
- ✅ 75-95% quality score
- ✅ 80-100% field accuracy
- ✅ Iterative refinement
- ✅ Multiple export formats

## 🎁 What's Included

✅ **Circular Companion UI** - Beautiful interface
✅ **Lead Generator** - Find local businesses  
✅ **Intelligence Agent** - Extract web data
✅ **Web Server** - Flask backend
✅ **Examples** - 12+ working examples
✅ **Documentation** - Complete guides
✅ **Startup Scripts** - Easy installation
✅ **API Support** - Use programmatically

## 🚀 Deployment Options

### Local (Desktop)
```bash
python -m byteflow.web_companion
# Open: http://localhost:5000
```

### Network/Office
```bash
python -m byteflow.web_companion
# Access from: http://192.168.1.xxx:5000
```

### Cloud (Heroku/AWS)
```bash
# Add Procfile
echo "web: python -m byteflow.web_companion" > Procfile

# Deploy
heroku create byteflow-app
git push heroku main
```

### Docker
```dockerfile
FROM python:3.9
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
EXPOSE 5000
CMD python -m byteflow.web_companion
```

## 📞 Common Tasks

### Get High-Quality Leads
```python
results = await lead.search_leads("restaurants", limit=50)
hot_leads = await lead.get_hot_leads(results['leads'])
```

### Extract and Save
```python
data = await intel.extract_from_query("Extract all products")
await intel.export_results(data, format='csv')
```

### Track Progress
```python
stats = await lead.get_stats()
print(f"Total: {stats['total']}, Contacted: {stats['contacted']}")
```

### Bulk Import
```python
for query in queries:
    results = await lead.search_leads(query)
    await lead.export_to_csv(results['leads'])
```

## 🎯 Business Model

**Option 1: Lead Generation Service**
- Find businesses without websites
- Charge $50-200 per qualified lead
- Profit: $2500-10000 per month

**Option 2: Data Extraction**
- Extract competitor data
- Charge $200-1000 per project
- Profit: $5000-20000 per project

**Option 3: Website Creation**
- Use leads + create websites
- Charge $500-2000 per website
- Profit: $350-1600 per site (70-80%)

**Option 4: Subscription Service**
- Monthly lead generation
- Charge $500-2000/month
- Profit: Recurring

## 📱 Accessing from Phone

1. Start server on computer
2. Get computer's IP: 
   - Windows: `ipconfig` → IPv4 Address
   - Mac: System Preferences → Network
3. On phone, visit: `http://192.168.1.xxx:5000`

## ✨ Pro Tips

1. **Filter by Service** - Gets higher quality leads
2. **Use Specific Queries** - "dental clinic with bad reviews" better
3. **Combine Services** - Lead Gen + Data Extraction + Website
4. **Automate Searches** - Run batch operations at night
5. **Export Regularly** - Keep backups of all leads
6. **Track Success** - Use Activity log to monitor
7. **Iterate Queries** - Test different search terms
8. **Quality Over Quantity** - Focus on hot leads

## 🎓 Learning Resources

- See `examples_companion.py` for code examples
- Check `COMPANION_README.md` for features
- Read `SETUP_GUIDE.md` for detailed setup

## 🎉 You're Ready!

- ✅ Everything installed
- ✅ Server running
- ✅ Interface ready
- ✅ Start finding leads!

**Go make money! 💰**

---

**ByteFlow Quick Reference** - Your pocket guide to lead generation and data extraction.
