"""
Intelligence Agent Companion
=============================
ByteFlow integration for smart web data extraction with iterative refinement

Commands:
  !extract <query>                 - Extract data (interactive)
  !crawl <url> <fields>            - Crawl specific URL
  !search-and-extract <query>      - Search then extract
  !validate <data>                 - Validate extracted data
  !history                         - View extraction history
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

try:
    from .smart_extractor import IntelligenceAgent, ExtractionContext
except ImportError:
    from smart_extractor import IntelligenceAgent, ExtractionContext


class IntelligenceCompanion:
    """ByteFlow companion for intelligent data extraction"""
    
    def __init__(self, agent=None, model="phi4-mini"):
        self.agent = agent
        self.model = model
        self.intelligence = IntelligenceAgent(agent, model)
        self.extraction_history = []
        self.current_project = None
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict:
        """Load companion settings"""
        return {
            'max_attempts': 5,
            'quality_threshold': 0.75,
            'auto_refine': True,
            'cache_results': True,
            'parallel_urls': False,
        }
    
    async def extract_from_query(
        self,
        query: str,
        data_type: str = "general",
        urls: Optional[List[str]] = None
    ) -> Dict:
        """
        Main extraction entry point.
        
        Natural language interface:
          extract_from_query("Get all product listings with prices from Amazon")
          → Determines: data_type="product_listing", criteria=["name", "price", "rating"]
        """
        
        print(f"\n{'='*70}")
        print(f"🧠 INTELLIGENCE EXTRACTION")
        print(f"{'='*70}")
        
        # Step 1: Parse query to extract criteria
        criteria = await self._parse_query_criteria(query, data_type)
        
        print(f"✓ Identified criteria: {criteria}")
        
        # Step 2: Determine URLs if not provided
        if not urls:
            urls = await self._find_relevant_urls(query, data_type)
            print(f"✓ Found {len(urls)} relevant URLs")
        
        # Step 3: Run extraction pipeline
        result = await self.intelligence.extract(
            query=query,
            data_type=data_type,
            criteria=criteria,
            urls=urls,
            max_attempts=self.settings['max_attempts']
        )
        
        # Step 4: Store in history
        self.extraction_history.append({
            'query': query,
            'data_type': data_type,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
        # Step 5: Display results
        self._display_results(result)
        
        return result
    
    async def _parse_query_criteria(self, query: str, data_type: str) -> List[str]:
        """
        Use LLM to determine what fields to extract from natural language query.
        
        Example:
          "Get restaurant names, ratings, and addresses"
          → ["name", "rating", "address"]
        """
        
        # For now, simple keyword extraction
        # In production, use LLM to parse sophisticated queries
        
        query_lower = query.lower()
        
        # Common extraction patterns
        patterns = {
            'name': ['name', 'title', 'product', 'restaurant', 'company'],
            'price': ['price', 'cost', 'amount', 'rate', 'fee'],
            'rating': ['rating', 'score', 'stars', 'review'],
            'address': ['address', 'location', 'place', 'city', 'street'],
            'phone': ['phone', 'contact', 'call', 'number'],
            'email': ['email', 'mail', 'contact'],
            'url': ['url', 'link', 'website'],
            'description': ['description', 'details', 'info', 'about'],
            'image': ['image', 'photo', 'picture'],
            'date': ['date', 'time', 'posted', 'created'],
            'availability': ['available', 'stock', 'inventory'],
        }
        
        criteria = []
        for field, keywords in patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                criteria.append(field)
        
        # Default if nothing found
        if not criteria:
            criteria = ['name', 'description', 'url']
        
        return criteria
    
    async def _find_relevant_urls(self, query: str, data_type: str) -> List[str]:
        """
        Determine URLs to crawl based on query and data type.
        
        In production, would:
          - Search Google
          - Identify relevant sites
          - Return top URLs
        """
        
        query_lower = query.lower()
        
        # URL mapping for common queries
        url_mappings = {
            'restaurant': ['yelp.com', 'google.com/maps', 'opentable.com'],
            'product': ['amazon.com', 'ebay.com', 'targetcom'],
            'job': ['linkedin.com/jobs', 'indeed.com', 'glassdoor.com'],
            'real estate': ['zillow.com', 'redfin.com', 'realtor.com'],
            'news': ['news.google.com', 'bbc.com', 'cnn.com'],
            'review': ['trustpilot.com', 'capterra.com', 'g2.com'],
        }
        
        for key, urls in url_mappings.items():
            if key in query_lower:
                return urls
        
        # Default: Google search
        return [f"https://www.google.com/search?q={query.replace(' ', '+')}"]
    
    def _display_results(self, result: Dict):
        """Display extraction results in readable format"""
        
        print(f"\n{'─'*70}")
        print(f"📊 EXTRACTION RESULTS")
        print(f"{'─'*70}")
        
        print(f"\n✓ Success: {result['success']}")
        print(f"✓ Quality Score: {result['quality_score']:.0%}")
        print(f"✓ Attempts: {result['attempts']}/{self.settings['max_attempts']}")
        
        print(f"\n📋 Extracted Data:")
        
        if isinstance(result['data'], dict):
            for key, value in result['data'].items():
                if value:
                    value_preview = str(value)[:100]
                    print(f"  • {key}: {value_preview}")
        elif isinstance(result['data'], list):
            print(f"  {len(result['data'])} items found")
            for i, item in enumerate(result['data'][:5], 1):
                print(f"    {i}. {item}")
            if len(result['data']) > 5:
                print(f"    ... and {len(result['data']) - 5} more")
        
        print(f"\n🔄 Refinement History:")
        for i, feedback in enumerate(result.get('feedback', []), 1):
            print(f"\n  Attempt {i}:")
            print(f"    Feedback: {feedback.get('feedback', 'N/A')[:200]}")
            print(f"    Suggestion: {feedback.get('suggestion', 'N/A')}")
        
        print(f"\n{'─'*70}")
    
    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get recent extraction history"""
        return self.extraction_history[-limit:]
    
    def export_results(self, result: Dict, format: str = "json") -> str:
        """Export results in various formats"""
        
        if format == "json":
            return json.dumps(result, indent=2)
        
        elif format == "csv":
            # Convert to CSV
            if isinstance(result['data'], list):
                import csv
                from io import StringIO
                
                output = StringIO()
                if result['data']:
                    writer = csv.DictWriter(output, fieldnames=result['data'][0].keys())
                    writer.writeheader()
                    writer.writerows(result['data'])
                return output.getvalue()
        
        elif format == "markdown":
            md = f"# {result['query']}\n\n"
            md += f"**Type:** {result['data_type']}\n"
            md += f"**Quality:** {result['quality_score']:.0%}\n\n"
            
            if isinstance(result['data'], dict):
                for key, value in result['data'].items():
                    md += f"- **{key}:** {value}\n"
            
            return md
        
        return str(result)
    
    async def setup_project(
        self,
        name: str,
        description: str,
        extraction_rules: Dict
    ):
        """Setup a reusable extraction project"""
        
        project = {
            'name': name,
            'description': description,
            'rules': extraction_rules,
            'created_at': datetime.now().isoformat(),
            'extractions': []
        }
        
        self.current_project = project
        
        print(f"✅ Project '{name}' created")
        print(f"   Description: {description}")
        print(f"   Rules: {json.dumps(extraction_rules, indent=2)}")
        
        return project
    
    async def run_project_extraction(
        self,
        query: str,
        urls: List[str]
    ) -> Dict:
        """Run extraction using current project rules"""
        
        if not self.current_project:
            print("❌ No project selected")
            return {}
        
        print(f"\n🚀 Running project: {self.current_project['name']}")
        
        result = await self.extract_from_query(
            query=query,
            data_type=self.current_project.get('type', 'custom'),
            urls=urls
        )
        
        # Store in project
        self.current_project['extractions'].append({
            'query': query,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })
        
        return result


class IntelligenceCompanionCLI:
    """Command-line interface for Intelligence Companion"""
    
    def __init__(self):
        self.companion = IntelligenceCompanion()
        self.commands = {
            'extract': self._cmd_extract,
            'crawl': self._cmd_crawl,
            'search': self._cmd_search,
            'history': self._cmd_history,
            'export': self._cmd_export,
            'project': self._cmd_project,
            'help': self._cmd_help,
        }
    
    async def run_interactive(self):
        """Run interactive CLI"""
        print("""
╔════════════════════════════════════════════════════════════╗
║         Intelligence Agent v1.0                           ║
║     Smart Web Data Extraction with LLM Refinement         ║
╚════════════════════════════════════════════════════════════╝

Commands:
  extract <query>          Extract data from web
  crawl <url> <fields>     Crawl specific URL
  search <query>           Search and extract
  history                  View extraction history
  export <format>          Export last results (json/csv/md)
  project <create/run>     Manage extraction projects
  help                     Show this help
  exit                     Exit

Examples:
  > extract Get restaurant names, ratings, and addresses from NYC
  > search restaurant listings in Los Angeles with prices
  > history
  > export json
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
                import traceback
                traceback.print_exc()
    
    async def _cmd_extract(self, query: str):
        """Extract data from natural language query"""
        if not query:
            print("❌ Usage: extract <query>")
            return
        
        # Detect data type from query
        data_type = "general"
        if "restaurant" in query.lower():
            data_type = "restaurant"
        elif "product" in query.lower():
            data_type = "product"
        elif "job" in query.lower():
            data_type = "job"
        
        result = await self.companion.extract_from_query(query, data_type)
        
        if result['success']:
            print("\n✅ Extraction successful!")
        else:
            print(f"\n⚠️ Partial success (Quality: {result['quality_score']:.0%})")
    
    async def _cmd_crawl(self, args: str):
        """Crawl specific URL"""
        if not args:
            print("❌ Usage: crawl <url> <field1,field2,field3>")
            return
        
        parts = args.split()
        url = parts[0]
        fields = parts[1].split(',') if len(parts) > 1 else ["content"]
        
        print(f"\n🔍 Crawling: {url}")
        print(f"   Fields: {fields}")
        
        result = await self.companion.extract_from_query(
            query=f"Extract {', '.join(fields)}",
            data_type="custom",
            urls=[url]
        )
    
    async def _cmd_search(self, query: str):
        """Search and extract"""
        if not query:
            print("❌ Usage: search <query>")
            return
        
        await self.companion.extract_from_query(query)
    
    async def _cmd_history(self, _):
        """View extraction history"""
        history = self.companion.get_history()
        
        if not history:
            print("\n📋 No history yet")
            return
        
        print(f"\n📋 Recent Extractions ({len(history)} total):\n")
        
        for i, entry in enumerate(history[-10:], 1):
            result = entry['result']
            print(f"{i}. {entry['query'][:60]}")
            print(f"   Quality: {result['quality_score']:.0%} | Attempts: {result['attempts']}")
            print()
    
    async def _cmd_export(self, format: str):
        """Export last results"""
        if not self.companion.extraction_history:
            print("❌ No extraction results to export")
            return
        
        format = format or "json"
        if format not in ["json", "csv", "markdown"]:
            format = "json"
        
        last_result = self.companion.extraction_history[-1]['result']
        output = self.companion.export_results(last_result, format)
        
        # Save to file
        filename = f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        Path(filename).write_text(output)
        
        print(f"\n✅ Exported to: {filename}")
    
    async def _cmd_project(self, args: str):
        """Manage extraction projects"""
        if not args:
            print("❌ Usage: project <create|run> [name]")
            return
        
        subcommand = args.split()[0].lower()
        
        if subcommand == "create":
            name = " ".join(args.split()[1:]) or "My Project"
            await self.companion.setup_project(
                name=name,
                description="Custom extraction project",
                extraction_rules={}
            )
        
        elif subcommand == "run":
            query = input("Query: ").strip()
            urls = input("URLs (comma-separated): ").strip().split(',')
            
            result = await self.companion.run_project_extraction(query, urls)
            print(f"\n✅ Project extraction complete")
    
    async def _cmd_help(self, _):
        """Show help"""
        print("\n" + self.run_interactive.__doc__)


# ═══════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ═══════════════════════════════════════════════════════════════════════

async def main():
    cli = IntelligenceCompanionCLI()
    await cli.run_interactive()


if __name__ == '__main__':
    print("\n🚀 Starting Intelligence Agent...\n")
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
