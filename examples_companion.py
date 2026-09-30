"""
ByteFlow Companion - Usage Examples
====================================
Shows how to use the Lead Generator and Intelligence Agent
"""

import asyncio
from byteflow.lead_generation_companion import LeadCompanion
from byteflow.intelligence_companion import IntelligenceCompanion

# ═══════════════════════════════════════════════════════════════════════
# LEAD GENERATOR EXAMPLES
# ═══════════════════════════════════════════════════════════════════════

async def example_lead_search():
    """Example 1: Basic lead search"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Lead Search")
    print("="*70)
    
    lead = LeadCompanion()
    
    # Search for restaurants in New York
    results = await lead.search_leads(
        query="restaurants in New York",
        limit=5
    )
    
    if results['success']:
        print(f"\n✅ Found {len(results['leads'])} leads\n")
        for idx, lead_item in enumerate(results['leads'], 1):
            print(f"{idx}. {lead_item.get('name', 'N/A')}")
            print(f"   Rating: {lead_item.get('rating', 'N/A')}⭐")
            print(f"   Type: {lead_item.get('category', 'N/A')}")
            print()

async def example_lead_filter():
    """Example 2: Search and filter leads"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Filter Leads by Service")
    print("="*70)
    
    lead = LeadCompanion()
    
    # Search for businesses
    results = await lead.search_leads("retail shops Los Angeles")
    
    if results['success']:
        print(f"\n🔍 Filtering {len(results['leads'])} leads for website_creation service...\n")
        
        # Filter
        filtered = await lead.filter_leads(
            leads=results['leads'],
            service="website_creation"
        )
        
        print(f"✅ Found {len(filtered)} leads needing website creation\n")
        for lead_item in filtered[:3]:
            print(f"  • {lead_item.get('name')}")

async def example_lead_export():
    """Example 3: Export leads to CSV"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Export Leads to CSV")
    print("="*70)
    
    lead = LeadCompanion()
    
    # Search
    results = await lead.search_leads("coffee shops Seattle", limit=10)
    
    if results['success']:
        # Export to CSV
        filepath = await lead.export_to_csv(results['leads'])
        print(f"\n✅ Exported {len(results['leads'])} leads to:")
        print(f"   📁 {filepath}\n")

async def example_lead_hot_leads():
    """Example 4: Find hot/priority leads"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Find High-Priority Leads")
    print("="*70)
    
    lead = LeadCompanion()
    
    # Search
    results = await lead.search_leads("auto repair shops Miami", limit=20)
    
    if results['success']:
        # Get hot leads
        hot_leads = await lead.get_hot_leads(results['leads'])
        
        print(f"\n🔥 Found {len(hot_leads)} high-priority leads:\n")
        for lead_item in hot_leads[:5]:
            print(f"  ⭐ {lead_item.get('name')}")
            print(f"     Confidence: {lead_item.get('confidence', 0):.0%}")
            print()

async def example_lead_mark_contacted():
    """Example 5: Track contacted leads"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Track Contacted Leads")
    print("="*70)
    
    lead = LeadCompanion()
    
    # Search
    results = await lead.search_leads("fitness gyms Chicago", limit=5)
    
    if results['success']:
        first_lead = results['leads'][0]
        
        # Mark as contacted
        await lead.mark_contacted(first_lead.get('id', first_lead.get('name')))
        
        print(f"\n✅ Marked '{first_lead.get('name')}' as contacted")
        
        # Get stats
        stats = await lead.get_stats()
        print(f"\n📊 Stats:")
        print(f"   Total leads: {stats.get('total', 0)}")
        print(f"   Contacted: {stats.get('contacted', 0)}")

# ═══════════════════════════════════════════════════════════════════════
# INTELLIGENCE AGENT EXAMPLES
# ═══════════════════════════════════════════════════════════════════════

async def example_intelligence_extract():
    """Example 6: Basic data extraction"""
    print("\n" + "="*70)
    print("EXAMPLE 6: Extract Data from Website")
    print("="*70)
    
    intel = IntelligenceCompanion()
    
    # Extract product names and prices
    result = await intel.extract_from_query(
        query="Extract product names and prices",
        urls=["https://example.com/products"]
    )
    
    if result['success']:
        print(f"\n✅ Extraction complete!")
        print(f"   Quality Score: {result['quality_score']:.0%}")
        print(f"   Attempts: {result.get('attempts', 1)}")
        print(f"   Items extracted: {len(result.get('data', []))}\n")

async def example_intelligence_search_extract():
    """Example 7: Search and extract"""
    print("\n" + "="*70)
    print("EXAMPLE 7: Search and Extract Data")
    print("="*70)
    
    intel = IntelligenceCompanion()
    
    # Search for product data
    result = await intel.extract_from_query(
        query="Find all laptop models with prices from Amazon"
    )
    
    if result['success']:
        print(f"\n✅ Found and extracted data!")
        print(f"   Quality: {result['quality_score']:.0%}")
        print(f"   Items: {len(result.get('data', []))}")
        
        # Show first 3 items
        if result.get('data'):
            print(f"\n   Sample data:")
            for item in result['data'][:3]:
                if isinstance(item, dict):
                    print(f"   • {item}")

async def example_intelligence_specific_fields():
    """Example 8: Extract specific fields"""
    print("\n" + "="*70)
    print("EXAMPLE 8: Extract Specific Fields")
    print("="*70)
    
    intel = IntelligenceCompanion()
    
    # Extract specific fields
    result = await intel.extract_from_query(
        query="Extract: name, phone, address, rating from business listings",
        data_type="businesses"
    )
    
    if result['success']:
        print(f"\n✅ Extracted specific fields!")
        print(f"   Quality: {result['quality_score']:.0%}")
        print(f"   Records: {len(result.get('data', []))}\n")

async def example_intelligence_quality_iterations():
    """Example 9: Watch quality improvement through iterations"""
    print("\n" + "="*70)
    print("EXAMPLE 9: Quality Improvement Through Iterations")
    print("="*70)
    
    intel = IntelligenceCompanion()
    
    result = await intel.extract_from_query(
        query="Extract restaurant ratings and reviews from multiple pages"
    )
    
    if result['success']:
        print(f"\n🔄 Extraction with quality refinement:")
        print(f"   Attempts made: {result.get('attempts', 1)}")
        print(f"   Final quality: {result['quality_score']:.0%}")
        print(f"   Status: {'✅ Success' if result['quality_score'] >= 0.75 else '⚠️ Acceptable'}\n")

async def example_intelligence_export():
    """Example 10: Export extracted data"""
    print("\n" + "="*70)
    print("EXAMPLE 10: Export Extracted Data")
    print("="*70)
    
    intel = IntelligenceCompanion()
    
    # Extract data
    result = await intel.extract_from_query(
        query="Extract all product information"
    )
    
    if result['success']:
        # Export in different formats
        print(f"\n✅ Extracted data can be exported as:\n")
        print(f"   1. JSON   - Structured data format")
        print(f"   2. CSV    - Spreadsheet format")
        print(f"   3. Markdown - Readable text format")
        print(f"   4. HTML   - Web format\n")

# ═══════════════════════════════════════════════════════════════════════
# COMBINED EXAMPLES
# ═══════════════════════════════════════════════════════════════════════

async def example_combined_workflow():
    """Example 11: Combined lead gen + data extraction workflow"""
    print("\n" + "="*70)
    print("EXAMPLE 11: Combined Workflow - Find Leads + Extract Data")
    print("="*70)
    
    lead = LeadCompanion()
    intel = IntelligenceCompanion()
    
    print("\n1️⃣  Finding local businesses...")
    lead_results = await lead.search_leads("digital agencies NYC", limit=5)
    
    if lead_results['success']:
        print(f"   ✅ Found {len(lead_results['leads'])} agencies\n")
        
        print("2️⃣  Extracting company details from web...\n")
        
        # For each lead, try to extract more data
        for idx, lead_item in enumerate(lead_results['leads'][:2], 1):
            print(f"   📊 Processing: {lead_item.get('name')}")
            
            # Extract details
            result = await intel.extract_from_query(
                query=f"Extract services offered by {lead_item.get('name')}"
            )
            
            if result['success']:
                print(f"       Quality: {result['quality_score']:.0%} ✅")
            print()

async def example_bulk_search():
    """Example 12: Bulk search and process"""
    print("\n" + "="*70)
    print("EXAMPLE 12: Bulk Search Multiple Queries")
    print("="*70)
    
    lead = LeadCompanion()
    
    queries = [
        "dental clinics Boston",
        "plumbers Chicago",
        "marketing agencies San Francisco"
    ]
    
    print(f"\n🔍 Searching for {len(queries)} categories...\n")
    
    total_leads = 0
    for query in queries:
        results = await lead.search_leads(query, limit=5)
        if results['success']:
            count = len(results['leads'])
            total_leads += count
            print(f"   ✅ {query}: {count} leads found")
    
    print(f"\n📊 Total: {total_leads} leads across all categories\n")

# ═══════════════════════════════════════════════════════════════════════
# MAIN - Run Examples
# ═══════════════════════════════════════════════════════════════════════

async def main():
    """Run all examples"""
    print("""
    ╔════════════════════════════════════════════════════════════════════╗
    ║        ByteFlow Companion - Usage Examples                        ║
    ║     Intelligent Lead Generation & Data Extraction                 ║
    ╚════════════════════════════════════════════════════════════════════╝
    """)
    
    examples = [
        ("Lead Search", example_lead_search),
        ("Lead Filter", example_lead_filter),
        ("Lead Export", example_lead_export),
        ("Hot Leads", example_lead_hot_leads),
        ("Track Contacted", example_lead_mark_contacted),
        ("Extract Data", example_intelligence_extract),
        ("Search & Extract", example_intelligence_search_extract),
        ("Specific Fields", example_intelligence_specific_fields),
        ("Quality Iterations", example_intelligence_quality_iterations),
        ("Export Data", example_intelligence_export),
        ("Combined Workflow", example_combined_workflow),
        ("Bulk Search", example_bulk_search),
    ]
    
    print("\nAvailable Examples:")
    for idx, (name, _) in enumerate(examples, 1):
        print(f"  {idx}. {name}")
    
    print("\nRun this file to execute all examples, or modify to run specific ones.")
    print("\nExample:")
    print("  await example_lead_search()")
    print("  await example_intelligence_extract()")
    print()

if __name__ == "__main__":
    asyncio.run(main())
