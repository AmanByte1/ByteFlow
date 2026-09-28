"""
Lead Generation Companion
===========================
AI-powered lead finder for selling:
  - Website creation services
  - SEO optimization packages  
  - WhatsApp bot integration
  - Digital marketing services

Features:
  - Search for businesses by location/category
  - Auto-qualify leads with Phi4-mini
  - Crawl websites with crawl4ai
  - Generate outreach lists
  - Track contact history
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

# Import lead finder
try:
    from .lead_finder import LeadGenerationPipeline, LeadManager
except ImportError:
    from lead_finder import LeadGenerationPipeline, LeadManager


class LeadCompanion:
    """Lead generation companion - standalone or integrated with ByteFlow"""
    
    def __init__(self, agent=None, model="phi4-mini"):
        self.agent = agent
        self.model = model
        self.pipeline = LeadGenerationPipeline(agent)
        self.manager = LeadManager()
        self.current_results = []
        self.settings = self._load_settings()
    
    def _load_settings(self) -> dict:
        """Load lead companion settings"""
        return {
            'auto_crawl': True,
            'min_confidence': 0.6,
            'target_services': ['website_creation', 'seo_optimization', 'whatsapp_bot'],
            'outreach_template': self._default_outreach_template(),
        }
    
    def _default_outreach_template(self) -> str:
        """Default WhatsApp/Email outreach message"""
        return """
Hi {name}! 👋

I noticed {business} has excellent ratings ({rating}⭐) but could use:
- Professional website
- SEO optimization
- WhatsApp bot for customer service

Would love to discuss how we can help grow your online presence! 💼
"""
    
    async def search_leads(self, query: str, limit: int = 10) -> dict:
        """
        Main entry point: Search for businesses that need services
        
        Examples:
          - "clothing shops New York"
          - "restaurants Los Angeles"
          - "hair salons Miami"
        """
        print(f"\n{'='*60}")
        print(f"🚀 LEAD GENERATION SEARCH")
        print(f"{'='*60}")
        print(f"Query: {query}")
        print(f"Limit: {limit}")
        
        try:
            # Run the full pipeline
            leads = await self.pipeline.generate_leads(query, limit)
            self.current_results = leads
            
            return {
                'success': True,
                'query': query,
                'total_found': len(leads),
                'leads': leads,
                'stats': self.manager.get_stats(),
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
            }
    
    def filter_leads(self, service_needed: str) -> list:
        """Filter current results by service type"""
        return [
            l for l in self.current_results 
            if service_needed in l.get('needs', [])
        ]
    
    def get_outreach_list(self, service: str = None) -> list:
        """Get formatted list for outreach with templates"""
        leads = (
            self.filter_leads(service) 
            if service else 
            self.current_results
        )
        
        outreach = []
        for lead in leads:
            template = self.settings['outreach_template']
            message = template.format(
                name=lead.get('name', 'there'),
                business=lead.get('category', 'Your business'),
                rating=lead.get('rating', 'N/A'),
            )
            
            outreach.append({
                'business_name': lead.get('name'),
                'phone': lead.get('phone', 'N/A'),
                'rating': lead.get('rating'),
                'needs': lead.get('needs'),
                'message': message,
                'confidence': lead.get('confidence'),
            })
        
        return outreach
    
    def export_to_csv(self, service: str = None) -> str:
        """Export leads to CSV for bulk contact"""
        import csv
        from io import StringIO
        
        leads = self.get_outreach_list(service)
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'business_name', 'phone', 'rating', 'needs', 'confidence'
        ])
        writer.writeheader()
        
        for lead in leads:
            writer.writerow({
                'business_name': lead['business_name'],
                'phone': lead['phone'],
                'rating': lead['rating'],
                'needs': ','.join(lead['needs']),
                'confidence': f"{lead['confidence']:.2f}",
            })
        
        csv_str = output.getvalue()
        
        # Save to file
        filepath = Path(f"leads_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        filepath.write_text(csv_str)
        
        return str(filepath)
    
    def get_hot_leads(self, limit: int = 10) -> list:
        """Get highest priority leads from database"""
        return self.manager.get_hot_leads(limit)
    
    def get_stats(self) -> dict:
        """Get overall statistics"""
        stats = self.manager.get_stats()
        stats['current_results'] = len(self.current_results)
        return stats
    
    def mark_contacted(self, business_name: str) -> dict:
        """Mark a lead as contacted"""
        self.manager.mark_contacted(business_name)
        return {'success': True, 'message': f"Marked {business_name} as contacted"}
    
    def get_hot_leads_html(self) -> str:
        """Generate HTML view of hot leads"""
        hot_leads = self.get_hot_leads()
        
        html = """
<html>
<head>
    <style>
        body { font-family: Arial; margin: 20px; }
        .lead-card { 
            border: 1px solid #ddd; 
            padding: 15px; 
            margin: 10px 0;
            border-radius: 5px;
            background: #f9f9f9;
        }
        .rating { color: #ff9800; font-weight: bold; }
        .needs { color: #2196f3; }
        .confidence { color: #4caf50; }
        h2 { color: #333; }
    </style>
</head>
<body>
<h2>🔥 Hot Leads Ready to Contact</h2>
"""
        
        for lead in hot_leads:
            html += f"""
<div class="lead-card">
    <h3>{lead.get('name')}</h3>
    <p><strong>Rating:</strong> <span class="rating">{lead.get('rating')}⭐</span></p>
    <p><strong>Phone:</strong> {lead.get('phone', 'N/A')}</p>
    <p><strong>Needs:</strong> <span class="needs">{', '.join(lead.get('needs', []))}</span></p>
    <p><strong>Confidence:</strong> <span class="confidence">{lead.get('confidence', 0):.0%}</span></p>
    <p><em>{lead.get('reasoning', '')}</em></p>
</div>
"""
        
        html += "</body></html>"
        return html


class LeadCompanionCLI:
    """Command-line interface for lead companion"""
    
    def __init__(self):
        self.companion = LeadCompanion()
        self.commands = {
            'search': self._cmd_search,
            'filter': self._cmd_filter,
            'export': self._cmd_export,
            'hot': self._cmd_hot,
            'stats': self._cmd_stats,
            'mark': self._cmd_mark,
            'help': self._cmd_help,
        }
    
    async def run_interactive(self):
        """Run interactive CLI"""
        print("""
╔════════════════════════════════════════════════════════════╗
║       Lead Generation Companion v1.0                       ║
║  Find & qualify businesses that need your services         ║
╚════════════════════════════════════════════════════════════╝

Commands:
  search <query>      Search for businesses (e.g. "clothing shops NYC")
  filter <service>    Filter results by service type
  export <service>    Export leads to CSV
  hot                 Show top priority leads
  stats               Show statistics
  mark <name>         Mark business as contacted
  help                Show this help
  exit                Exit

Examples:
  > search clothing shops New York
  > filter website_creation
  > export seo_optimization
""")
        
        while True:
            try:
                cmd = input("\n🤖 > ").strip()
                
                if not cmd:
                    continue
                
                if cmd.lower() == 'exit':
                    print("👋 Goodbye!")
                    break
                
                parts = cmd.split(maxsplit=1)
                action = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else None
                
                if action in self.commands:
                    await self.commands[action](arg)
                else:
                    print(f"Unknown command: {action}")
                    await self._cmd_help(None)
                    
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted.")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    async def _cmd_search(self, query: str):
        if not query:
            print("❌ Usage: search <query>")
            return
        
        result = await self.companion.search_leads(query, limit=10)
        
        if result['success']:
            print(f"\n✅ Found {result['total_found']} qualified leads")
            for i, lead in enumerate(result['leads'][:5], 1):
                print(f"\n{i}. {lead['name']}")
                print(f"   Rating: {lead['rating']}⭐")
                print(f"   Needs: {', '.join(lead['needs'])}")
                print(f"   Confidence: {lead['confidence']:.0%}")
        else:
            print(f"❌ Error: {result['error']}")
    
    async def _cmd_filter(self, service: str):
        if not service:
            print("Services: website_creation, seo_optimization, whatsapp_bot, social_media_marketing")
            return
        
        filtered = self.companion.filter_leads(service)
        print(f"\n📋 {len(filtered)} leads need {service}")
        for lead in filtered[:10]:
            print(f"  • {lead['name']} ({lead['rating']}⭐)")
    
    async def _cmd_export(self, service: str):
        filepath = self.companion.export_to_csv(service)
        print(f"\n✅ Exported to {filepath}")
    
    async def _cmd_hot(self, _):
        hot = self.companion.get_hot_leads()
        print(f"\n🔥 {len(hot)} hot leads:\n")
        for i, lead in enumerate(hot, 1):
            print(f"{i}. {lead['name']}")
            print(f"   Rating: {lead['rating']}⭐ | Confidence: {lead['confidence']:.0%}")
            print()
    
    async def _cmd_stats(self, _):
        stats = self.companion.get_stats()
        print(f"""
📊 LEAD STATISTICS
─────────────────────
Total Leads:        {stats['total_leads']}
Hot Leads:          {stats['hot_leads']}
Already Contacted:  {stats['contacted']}
Avg Confidence:     {stats['avg_confidence']:.0%}
Current Results:    {stats['current_results']}
""")
    
    async def _cmd_mark(self, name: str):
        if not name:
            print("❌ Usage: mark <business_name>")
            return
        result = self.companion.mark_contacted(name)
        print(f"✅ {result['message']}")
    
    async def _cmd_help(self, _):
        print("\n" + self.run_interactive.__doc__)


# ═══════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════

async def main():
    cli = LeadCompanionCLI()
    await cli.run_interactive()


if __name__ == '__main__':
    print("\n🚀 Starting Lead Generation Companion...\n")
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
