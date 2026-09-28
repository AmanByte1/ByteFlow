"""
Lead Generation Examples
========================
Practical examples of using the Lead Generation Companion

Run: python examples_lead_generation.py
"""

import asyncio
import sys
from pathlib import Path

# Add ByteFlow to path
sys.path.insert(0, str(Path(__file__).parent))

from byteflow.lead_generation_companion import (
    LeadCompanion,
    LeadCompanionCLI,
)


# ═════════════════════════════════════════════════════════════════════════
# EXAMPLE 1: Basic Lead Search
# ═════════════════════════════════════════════════════════════════════════

async def example_1_basic_search():
    """Search for businesses and get qualified leads"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Lead Search")
    print("="*70)
    
    companion = LeadCompanion()
    
    # Search for clothing shops in New York
    result = await companion.search_leads(
        query="clothing shops New York",
        limit=5
    )
    
    if result['success']:
        print(f"\n✅ Found {result['total_found']} qualified leads\n")
        
        for i, lead in enumerate(result['leads'], 1):
            print(f"{i}. {lead['name']}")
            print(f"   Rating: {lead['rating']}⭐")
            print(f"   Needs: {', '.join(lead['needs'])}")
            print(f"   Confidence: {lead['confidence']:.0%}")
            print()
    else:
        print(f"Error: {result['error']}")


# ═════════════════════════════════════════════════════════════════════════
# EXAMPLE 2: Filter by Service Type
# ═════════════════════════════════════════════════════════════════════════

async def example_2_filter_by_service():
    """Find leads that specifically need a certain service"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Filter Leads by Service Type")
    print("="*70)
    
    companion = LeadCompanion()
    
    # First do a search
    await companion.search_leads("restaurants Los Angeles", limit=8)
    
    # Now filter for different service types
    for service in ['website_creation', 'seo_optimization', 'whatsapp_bot']:
        filtered = companion.filter_leads(service)
        print(f"\n📌 {len(filtered)} leads need {service}:")
        
        for lead in filtered[:3]:
            print(f"  • {lead['name']} ({lead['confidence']:.0%} confidence)")


# ═════════════════════════════════════════════════════════════════════════
# EXAMPLE 3: Export for Outreach
# ═════════════════════════════════════════════════════════════════════════

async def example_3_export_leads():
    """Export leads to CSV for bulk outreach"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Export Leads for Outreach")
    print("="*70)
    
    companion = LeadCompanion()
    
    # Do a search
    await companion.search_leads("hair salons Miami", limit=10)
    
    # Get outreach list with templates
    outreach_list = companion.get_outreach_list('whatsapp_bot')
    
    print(f"\n📧 Generated {len(outreach_list)} outreach messages:\n")
    
    for i, item in enumerate(outreach_list[:2], 1):
        print(f"{i}. {item['business_name']}")
        print(f"   Phone: {item['phone']}")
        print(f"   Message:")
        print(f"   {item['message']}")
        print()
    
    # Export to CSV
    csv_file = companion.export_to_csv('whatsapp_bot')
    print(f"✅ Exported to: {csv_file}")


# ═════════════════════════════════════════════════════════════════════════
# EXAMPLE 4: Get Hot Leads
# ═════════════════════════════════════════════════════════════════════════

async def example_4_hot_leads():
    """Get the highest priority leads from the database"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Hot Leads (High Priority)")
    print("="*70)
    
    companion = LeadCompanion()
    
    # Get hot leads from database
    hot_leads = companion.get_hot_leads(limit=10)
    
    print(f"\n🔥 Top {len(hot_leads)} Hot Leads:\n")
    
    for i, lead in enumerate(hot_leads, 1):
        print(f"{i}. {lead['name']}")
        print(f"   Rating: {lead['rating']}⭐")
        print(f"   Contact: {lead.get('phone', 'N/A')}")
        print(f"   Confidence: {lead['confidence']:.0%}")
        print(f"   Needs: {', '.join(lead['needs'])}")
        print()


# ═════════════════════════════════════════════════════════════════════════
# EXAMPLE 5: Track Contact History
# ═════════════════════════════════════════════════════════════════════════

async def example_5_track_contacts():
    """Mark leads as contacted and view statistics"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Track Contact History")
    print("="*70)
    
    companion = LeadCompanion()
    
    # Get stats before marking
    stats_before = companion.get_stats()
    print(f"\n📊 Stats Before Contact:")
    print(f"   Total Leads: {stats_before['total_leads']}")
    print(f"   Contacted: {stats_before['contacted']}")
    
    # In a real scenario, you would mark leads as contacted
    # after actually reaching out to them
    # companion.mark_contacted("Best Clothing Store")
    
    # Get updated stats
    stats_after = companion.get_stats()
    print(f"\n📊 Stats After Contact:")
    print(f"   Total Leads: {stats_after['total_leads']}")
    print(f"   Contacted: {stats_after['contacted']}")
    print(f"   Hot Leads: {stats_after['hot_leads']}")
    print(f"   Avg Confidence: {stats_after['avg_confidence']:.0%}")


# ═════════════════════════════════════════════════════════════════════════
# EXAMPLE 6: Multi-Location Campaign
# ═════════════════════════════════════════════════════════════════════════

async def example_6_multi_location():
    """Search multiple locations for the same business type"""
    print("\n" + "="*70)
    print("EXAMPLE 6: Multi-Location Campaign")
    print("="*70)
    
    companion = LeadCompanion()
    
    locations = [
        "coffee shops New York",
        "coffee shops Los Angeles",
        "coffee shops Chicago",
    ]
    
    all_leads = []
    
    for location in locations:
        print(f"\n🔍 Searching: {location}")
        result = await companion.search_leads(location, limit=5)
        
        if result['success']:
            all_leads.extend(result['leads'])
            print(f"   ✅ Found {result['total_found']} leads")
    
    print(f"\n📊 Campaign Summary:")
    print(f"   Total Leads Across All Locations: {len(all_leads)}")
    print(f"   Avg Confidence: {sum(l['confidence'] for l in all_leads) / len(all_leads):.0%}")
    
    # Show top lead
    if all_leads:
        top = max(all_leads, key=lambda x: x['confidence'])
        print(f"\n🏆 Top Lead: {top['name']} ({top['confidence']:.0%})")


# ═════════════════════════════════════════════════════════════════════════
# EXAMPLE 7: Generate Custom Outreach Messages
# ═════════════════════════════════════════════════════════════════════════

async def example_7_custom_outreach():
    """Generate personalized outreach messages"""
    print("\n" + "="*70)
    print("EXAMPLE 7: Custom Outreach Messages")
    print("="*70)
    
    companion = LeadCompanion()
    
    # Customize the outreach template
    companion.settings['outreach_template'] = """
Hey {name}! 👋

We just analyzed {business} and noticed:
✅ {rating}⭐ rating - you're doing GREAT!
⚠️ But missing online opportunities

Let's fix that! We offer:
🌐 Professional Website - $599
📊 SEO Optimization - $299/month
💬 WhatsApp Bot - $199/month

Free consultation? 📅

[Your Contact Info]
"""
    
    # Do a search
    await companion.search_leads("plumbing contractors Chicago", limit=5)
    
    # Get outreach list with custom template
    outreach = companion.get_outreach_list()
    
    print(f"\n📧 Sample Messages:\n")
    for item in outreach[:2]:
        print(f"To: {item['business_name']}")
        print(item['message'])
        print("\n" + "-"*50 + "\n")


# ═════════════════════════════════════════════════════════════════════════
# MAIN: Run Selected Examples
# ═════════════════════════════════════════════════════════════════════════

async def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║     Lead Generation Companion - Usage Examples            ║
╚════════════════════════════════════════════════════════════╝

Choose an example to run:
  1. Basic Lead Search
  2. Filter by Service Type
  3. Export Leads for Outreach
  4. Hot Leads (High Priority)
  5. Track Contact History
  6. Multi-Location Campaign
  7. Custom Outreach Messages
  0. Run All Examples
  q. Quit
""")
    
    choice = input("Enter your choice (0-7, q): ").strip().lower()
    
    examples = {
        '1': example_1_basic_search,
        '2': example_2_filter_by_service,
        '3': example_3_export_leads,
        '4': example_4_hot_leads,
        '5': example_5_track_contacts,
        '6': example_6_multi_location,
        '7': example_7_custom_outreach,
    }
    
    if choice == 'q':
        print("Goodbye! 👋")
        return
    
    if choice == '0':
        # Run all examples
        for func in examples.values():
            try:
                await func()
            except Exception as e:
                print(f"Error in {func.__name__}: {e}")
    elif choice in examples:
        try:
            await examples[choice]()
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Invalid choice")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
