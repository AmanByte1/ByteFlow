"""
Lead Finder Companion Module
=============================
Intelligent lead generation using:
  - crawl4ai: Web scraping for business data
  - phi4-mini: LLM analysis for qualification
  
Identifies businesses that need:
  - Website creation
  - SEO optimization
  - WhatsApp bot integration
"""

import json
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

try:
    from crawl4ai import AsyncWebCrawler, CrawlResult
except ImportError:
    print("[LeadFinder] Install crawl4ai: pip install crawl4ai")
    AsyncWebCrawler = None


class LeadQualifier:
    """Analyze businesses using phi4-mini or other LLM"""
    
    def __init__(self, agent=None):
        self.agent = agent
        self.cache = {}
    
    async def analyze_business(self, business_data: Dict) -> Dict:
        """
        Analyze a business using LLM to identify needs.
        Returns: {needs: [service list], confidence: score, reasoning: str}
        """
        cache_key = business_data.get('name', 'unknown')
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        analysis = {
            'name': business_data.get('name'),
            'rating': business_data.get('rating'),
            'has_website': business_data.get('has_website', False),
            'needs': self._identify_needs(business_data),
            'confidence': self._calculate_confidence(business_data),
            'reasoning': self._build_reasoning(business_data),
            'priority': 'high' if self._is_high_priority(business_data) else 'medium'
        }
        
        self.cache[cache_key] = analysis
        return analysis
    
    def _identify_needs(self, data: Dict) -> List[str]:
        """Identify what services this business needs"""
        needs = []
        
        # High rating but no website = needs website + SEO
        if data.get('rating', 0) >= 4.0 and not data.get('has_website'):
            needs.extend(['website_creation', 'seo_optimization'])
        
        # Poor online presence = SEO services
        if not data.get('has_website') or not data.get('is_seo_optimized'):
            needs.append('seo_optimization')
        
        # Local business = WhatsApp bot
        if data.get('category') in ['retail', 'restaurant', 'service', 'local']:
            needs.append('whatsapp_bot')
        
        # No mobile presence = mobile optimization
        if not data.get('mobile_friendly'):
            needs.append('mobile_optimization')
        
        # Social media = social media management
        if data.get('social_followers', 0) < 1000:
            needs.append('social_media_marketing')
        
        return list(set(needs))  # Remove duplicates
    
    def _calculate_confidence(self, data: Dict) -> float:
        """Calculate confidence score (0-1) for lead quality"""
        score = 0.0
        
        # High rating = good target
        if data.get('rating', 0) >= 4.0:
            score += 0.3
        
        # No website = definite need
        if not data.get('has_website'):
            score += 0.3
        
        # Active business (has reviews/followers)
        if data.get('review_count', 0) > 10:
            score += 0.2
        
        # Local business = higher conversion
        if data.get('category') in ['retail', 'restaurant', 'service']:
            score += 0.2
        
        return min(score, 1.0)
    
    def _is_high_priority(self, data: Dict) -> bool:
        """Mark as high priority if it's a hot lead"""
        return (
            data.get('rating', 0) >= 4.5 and
            not data.get('has_website') and
            data.get('review_count', 0) > 20
        )
    
    def _build_reasoning(self, data: Dict) -> str:
        """Generate human-readable explanation"""
        reasons = []
        
        if data.get('rating', 0) >= 4.0 and not data.get('has_website'):
            reasons.append(f"Highly rated ({data.get('rating')}⭐) with no website")
        
        if not data.get('is_seo_optimized'):
            reasons.append("Not SEO optimized in search results")
        
        if data.get('category') in ['retail', 'restaurant', 'service']:
            reasons.append(f"Local {data.get('category')} business")
        
        if data.get('review_count', 0) > 0:
            reasons.append(f"Active: {data.get('review_count')} reviews")
        
        return " | ".join(reasons) if reasons else "Potential lead"


class BusinessCrawler:
    """Crawl Google Maps, business directories, etc. using crawl4ai"""
    
    def __init__(self):
        self.crawler = None
        self.results = []
    
    async def init(self):
        """Initialize async crawler"""
        if AsyncWebCrawler is None:
            raise ImportError("crawl4ai not installed. Run: pip install crawl4ai")
        self.crawler = AsyncWebCrawler()
    
    async def crawl_google_maps(self, search_query: str, limit: int = 10) -> List[Dict]:
        """
        Crawl Google Maps for businesses matching search query.
        Example: "clothing shops in New York"
        """
        if not self.crawler:
            await self.init()
        
        # This would be integrated with Google Maps API or web scraping
        # For now, returning mock data structure
        return self._mock_gmaps_results(search_query, limit)
    
    async def crawl_business_website(self, url: str) -> Dict:
        """
        Crawl a business website to assess:
        - Has website (yes/no)
        - Is mobile friendly
        - SEO indicators
        - Contact info (has WhatsApp, email, etc)
        """
        if not self.crawler:
            await self.init()
        
        try:
            result = await self.crawler.arun(url=url)
            
            return {
                'url': url,
                'has_website': True,
                'mobile_friendly': self._check_mobile_friendly(result),
                'is_seo_optimized': self._check_seo(result),
                'has_contact': self._check_contact_info(result),
                'has_whatsapp': self._check_whatsapp(result),
                'page_speed': self._estimate_speed(result),
                'content': result.markdown[:500] if result.markdown else ""
            }
        except Exception as e:
            print(f"[LeadFinder] Error crawling {url}: {e}")
            return {'url': url, 'error': str(e)}
    
    def _check_mobile_friendly(self, result: 'CrawlResult') -> bool:
        """Check if page is mobile friendly"""
        html = result.html or ""
        indicators = [
            "viewport" in html,
            "mobile" in html.lower(),
            "responsive" in html.lower()
        ]
        return sum(indicators) >= 2
    
    def _check_seo(self, result: 'CrawlResult') -> bool:
        """Check basic SEO indicators"""
        html = result.html or ""
        indicators = [
            "<meta name=\"description\"" in html,
            "<h1>" in html,
            "robots" in html.lower()
        ]
        return sum(indicators) >= 2
    
    def _check_contact_info(self, result: 'CrawlResult') -> bool:
        """Check if contact info is available"""
        content = (result.markdown or "") + (result.html or "")
        return any(x in content for x in ["contact", "email", "phone"])
    
    def _check_whatsapp(self, result: 'CrawlResult') -> bool:
        """Check if WhatsApp is already integrated"""
        content = (result.markdown or "") + (result.html or "")
        return "whatsapp" in content.lower()
    
    def _estimate_speed(self, result: 'CrawlResult') -> str:
        """Estimate page load speed"""
        # In real scenario, use PageSpeed Insights API
        return "medium"
    
    def _mock_gmaps_results(self, query: str, limit: int) -> List[Dict]:
        """Mock Google Maps results for demo"""
        businesses = [
            {
                'name': f'{query.split()[0]} Store 1',
                'category': 'retail',
                'rating': 4.7,
                'review_count': 125,
                'phone': '+1-555-0101',
                'address': '123 Main St',
                'has_website': False,
                'is_seo_optimized': False,
                'mobile_friendly': False,
                'social_followers': 150,
            },
            {
                'name': f'{query.split()[0]} Store 2',
                'category': 'retail',
                'rating': 4.3,
                'review_count': 89,
                'phone': '+1-555-0102',
                'address': '456 Oak Ave',
                'has_website': True,
                'is_seo_optimized': False,
                'mobile_friendly': False,
                'social_followers': 500,
            },
        ]
        return businesses[:limit]


class LeadManager:
    """Manage and store identified leads"""
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path("./leads_database.json")
        self.leads = self._load_leads()
    
    def _load_leads(self) -> List[Dict]:
        """Load existing leads from storage"""
        if self.storage_path.exists():
            try:
                return json.loads(self.storage_path.read_text())
            except:
                return []
        return []
    
    def save_leads(self):
        """Persist leads to storage"""
        self.storage_path.write_text(json.dumps(self.leads, indent=2))
    
    def add_lead(self, lead: Dict):
        """Add a new lead"""
        lead['added_at'] = datetime.now().isoformat()
        lead['contacted'] = False
        self.leads.append(lead)
        self.save_leads()
    
    def get_hot_leads(self, limit: int = 10) -> List[Dict]:
        """Get top priority leads"""
        hot = [l for l in self.leads if l.get('priority') == 'high' and not l.get('contacted')]
        return sorted(hot, key=lambda x: x.get('confidence', 0), reverse=True)[:limit]
    
    def mark_contacted(self, lead_name: str):
        """Mark lead as contacted"""
        for lead in self.leads:
            if lead.get('name') == lead_name:
                lead['contacted'] = True
                lead['contacted_at'] = datetime.now().isoformat()
        self.save_leads()
    
    def get_stats(self) -> Dict:
        """Get lead generation stats"""
        return {
            'total_leads': len(self.leads),
            'hot_leads': len([l for l in self.leads if l.get('priority') == 'high']),
            'contacted': len([l for l in self.leads if l.get('contacted')]),
            'avg_confidence': sum(l.get('confidence', 0) for l in self.leads) / max(len(self.leads), 1),
        }


class LeadGenerationPipeline:
    """Main pipeline: Search → Crawl → Analyze → Store"""
    
    def __init__(self, agent=None):
        self.crawler = BusinessCrawler()
        self.qualifier = LeadQualifier(agent)
        self.manager = LeadManager()
    
    async def generate_leads(self, search_query: str, limit: int = 10) -> List[Dict]:
        """
        Full pipeline:
        1. Search for businesses
        2. Crawl their sites
        3. Analyze with LLM
        4. Store qualified leads
        """
        print(f"\n🔍 Searching for: {search_query}")
        
        # Step 1: Find businesses
        businesses = await self.crawler.crawl_google_maps(search_query, limit)
        print(f"✅ Found {len(businesses)} businesses")
        
        qualified_leads = []
        
        # Step 2-3: Crawl and analyze each
        for i, business in enumerate(businesses, 1):
            print(f"   [{i}/{len(businesses)}] Analyzing {business.get('name')}...")
            
            # Crawl website if it exists
            if business.get('has_website'):
                website_data = await self.crawler.crawl_business_website(
                    business.get('website', '')
                )
                business.update(website_data)
            
            # Qualify with LLM
            analysis = await self.qualifier.analyze_business(business)
            
            # Only add if has needs
            if analysis.get('needs'):
                lead = {**business, **analysis}
                qualified_leads.append(lead)
                self.manager.add_lead(lead)
                print(f"   ✓ Qualified: {', '.join(analysis.get('needs', []))}")
            else:
                print(f"   ✗ Not a qualified lead")
        
        print(f"\n📊 Generated {len(qualified_leads)} qualified leads")
        return qualified_leads


# ═══════════════════════════════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════════════════════════════

__all__ = [
    'LeadFinder',
    'LeadQualifier',
    'BusinessCrawler',
    'LeadManager',
    'LeadGenerationPipeline',
]


if __name__ == '__main__':
    # Demo usage
    print("Lead Finder Module v1.0")
    print("Install crawl4ai to enable web crawling:")
    print("  pip install crawl4ai")
