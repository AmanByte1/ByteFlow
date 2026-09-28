"""
Intelligence Agent Examples
=============================
Real-world usage examples for smart web data extraction

Run: python examples_intelligence_agent.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from byteflow.intelligence_companion import IntelligenceCompanion


# ═════════════════════════════════════════════════════════════════════════
# EXAMPLE 1: Extract Restaurant Data with Auto-Refinement
# ═════════════════════════════════════════════════════════════════════════

async def example_1_restaurant_extraction():
    """Extract restaurant data with iterative refinement"""
    print("\n" + "="*70)
    print("EXAMPLE 1: Restaurant Data Extraction")
    print("="*70)
    
    companion = IntelligenceCompanion()
    
    result = await companion.extract_from_query(
        query="Get restaurant names, ratings, addresses, and phone numbers in New York",
        data_type="restaurant",
        urls=["https://www.yelp.com/search?find_desc=restaurants&find_loc=New+York"]
    )
    
    print(f"\n✅ Completed in {result['attempts']} refinement cycles")
    print(f"   Quality Score: {result['quality_score']:.0%}")


# ═════════════════════════════════════════════════════════════════════════
# EXAMPLE 2: Product Listing with Price & Reviews
# ═════════════════════════════════════════════════════════════════════════

async def example_2_product_extraction():
    """Extract product listings with prices and reviews"""
    print("\n" + "="*70)
    print("EXAMPLE 2: Product Listing Extraction")
    print("="*70)
    
    companion = IntelligenceCompanion()
    
    result = await companion.extract_from_query(
        query="Extract laptop product names, prices, star ratings, and reviews from Amazon",
        data_type="product",
        urls=["https://www.amazon.com/s?k=laptop"]
    )
    
    # Export results
    csv_output = companion.export_results(result, "csv")
    print(f"\n📊 CSV Export Preview:\n{csv_output[:500]}")


# ═════════════════════════════════════════════════════════════════════════
# EXAMPLE 3: Job Postings with Requirements
# ═════════════════════════════════════════════════════════════════════════

async def example_3_job_extraction():
    """Extract job postings with salary and requirements"""
    print("\n" + "="*70)
    print("EXAMPLE 3: Job Postings Extraction")
    print("="*70)
    
    companion = IntelligenceCompanion()
    
    result = await companion.extract_from_query(
        query="Find remote Python developer jobs with salary ranges, required skills, and company names",
        data_type="job",
        urls=[
            "https://www.indeed.com/jobs?q=python+developer&jt=remotefulltime",
            "https://www.linkedin.com/jobs/search/?keywords=python"
        ]
    )
    
    # Show refinement history
    print("\n🔄 Refinement Process:")
    for i, feedback in enumerate(result.get('feedback', []), 1):
        print(f"\n   Cycle {i}:")
        print(f"   Issue: {feedback.get('feedback', 'N/A')[:100]}")
        print(f"   Action: {feedback.get('suggestion', 'N/A')[:100]}")


# ═════════════════════════════════════════════════════════════════════════
# EXAMPLE 4: Real Estate Listings
# ═════════════════════════════════════════════════════════════════════════

async def example_4_realestate_extraction():
    """Extract real estate listings"""
    print("\n" + "="*70)
    print("EXAMPLE 4: Real Estate Listings")
    print("="*70)
    
    companion = IntelligenceCompanion()
    
    result = await companion.extract_from_query(
        query="Get property listings with price, beds, baths, square feet, and location",
        data_type="real_estate",
        urls=["https://www.zillow.com/homes/for_sale/"]
    )
    
    print(f"\n📍 Found {len(result.get('data', []))} properties")
    print(f"   Average Quality Score: {result['quality_score']:.0%}")


# ═════════════════════════════════════════════════════════════════════════
# EXAMPLE 5: Multi-Source Data Aggregation
# ═════════════════════════════════════════════════════════════════════════

async def example_5_multi_source():
    """Extract from multiple sources and combine"""
    print("\n" + "="*70)
    print("EXAMPLE 5: Multi-Source Data Aggregation")
    print("="*70)
    
    companion = IntelligenceCompanion()
    
    # Setup a project for consistent extraction
    await companion.setup_project(
        name="Competitor Analysis",
        description="Track competitor pricing and features",
        extraction_rules={
            'product': ['name', 'price', 'features', 'rating'],
            'company': ['name', 'price', 'market_position', 'reviews']
        }
    )
    
    # Extract from multiple competitors
    competitors = [
        ("https://www.competitor1.com", "Extract product names and prices"),
        ("https://www.competitor2.com", "Extract product names and prices"),
        ("https://www.competitor3.com", "Extract product names and prices"),
    ]
    
    results = []
    for url, query in competitors:
        result = await companion.extract_from_query(
            query=query,
            data_type="competitor_product",
            urls=[url]
        )
        results.append({
            'source': url,
            'quality': result['quality_score'],
            'data': result['data']
        })
    
    # Compare results
    print("\n📊 Competitor Comparison:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. {result['source']}")
        print(f"   Data Quality: {result['quality']:.0%}")
        print(f"   Products Found: {len(result.get('data', []))}")


# ═════════════════════════════════════════════════════════════════════════
# EXAMPLE 6: News Aggregation with Sentiment
# ═════════════════════════════════════════════════════════════════════════

async def example_6_news_aggregation():
    """Extract news articles with headlines and summaries"""
    print("\n" + "="*70)
    print("EXAMPLE 6: News Aggregation")
    print("="*70)
    
    companion = IntelligenceCompanion()
    
    result = await companion.extract_from_query(
        query="Get latest AI news with headlines, summaries, and publish dates from major tech news sites",
        data_type="news",
        urls=[
            "https://techcrunch.com/tag/artificial-intelligence/",
            "https://www.theverge.com/ai-artificial-intelligence",
            "https://news.ycombinator.com/"
        ]
    )
    
    print(f"\n📰 Found {len(result.get('data', []))} articles")
    print(f"   Average Quality: {result['quality_score']:.0%}")
    
    # Export as markdown
    md_output = companion.export_results(result, "markdown")
    print(f"\n📝 Markdown Export:\n{md_output[:500]}")


# ═════════════════════════════════════════════════════════════════════════
# EXAMPLE 7: Custom Data Type with Complex Criteria
# ═════════════════════════════════════════════════════════════════════════

async def example_7_custom_extraction():
    """Extract custom data with complex criteria"""
    print("\n" + "="*70)
    print("EXAMPLE 7: Custom Data Extraction")
    print("="*70)
    
    companion = IntelligenceCompanion()
    
    result = await companion.extract_from_query(
        query="""
        Extract software review sites with:
        - Product name
        - Overall rating (1-5 stars)
        - Number of reviews
        - Top 3 features mentioned
        - Top 3 complaints
        - Pricing model
        - Free trial availability
        """,
        data_type="software_reviews",
        urls=[
            "https://www.capterra.com/",
            "https://www.g2.com/",
            "https://www.trustpilot.com/"
        ]
    )
    
    print(f"\n✅ Extraction Complete")
    print(f"   Attempts Used: {result['attempts']}/5")
    print(f"   Quality Achieved: {result['quality_score']:.0%}")
    
    # Show what was learned
    print("\n📚 Refinement Learning:")
    for i, feedback in enumerate(result.get('feedback', []), 1):
        print(f"\n   Refinement {i}:")
        print(f"   - Found: {feedback.get('feedback', 'N/A')[:80]}")
        print(f"   - Tried: {feedback.get('suggestion', 'N/A')[:80]}")


# ═════════════════════════════════════════════════════════════════════════
# EXAMPLE 8: Intelligent Retry with Format Detection
# ═════════════════════════════════════════════════════════════════════════

async def example_8_smart_retry():
    """Demonstrate intelligent retry and format detection"""
    print("\n" + "="*70)
    print("EXAMPLE 8: Smart Retry with Format Detection")
    print("="*70)
    
    companion = IntelligenceCompanion()
    
    # This example shows how the system auto-detects best extraction strategy
    # If first attempt fails to find structured data (table), it:
    # 1. Analyzes the failure
    # 2. Suggests looking for list-based data
    # 3. Or tries to extract from text blocks
    # 4. Retries until successful or max attempts reached
    
    result = await companion.extract_from_query(
        query="Extract company financials: revenue, profit, employees",
        data_type="company_financials",
        urls=["https://finance.yahoo.com/"]
    )
    
    print(f"\n✅ Extraction Strategy Evolution:")
    
    if result.get('history'):
        for i, attempt in enumerate(result['history'], 1):
            strategy = attempt.get('strategy', 'unknown')
            print(f"\n   Attempt {i}:")
            print(f"   Strategy: {strategy}")
            if attempt.get('extracted_fields'):
                print(f"   Fields Found: {len(attempt['extracted_fields'])}")


# ═════════════════════════════════════════════════════════════════════════
# EXAMPLE 9: Integration with Lead Generation
# ═════════════════════════════════════════════════════════════════════════

async def example_9_leads_with_intelligence():
    """Combine Intelligence Agent with lead generation"""
    print("\n" + "="*70)
    print("EXAMPLE 9: Lead Generation with Intelligence Agent")
    print("="*70)
    
    companion = IntelligenceCompanion()
    
    # Use intelligence agent to extract high-quality lead data
    result = await companion.extract_from_query(
        query="""
        Extract local businesses for lead generation:
        - Business name
        - Google rating
        - Number of reviews
        - Phone number
        - Website URL
        - Service category
        """,
        data_type="lead_generation",
        urls=["https://www.google.com/maps/search/restaurants+new+york/"]
    )
    
    print(f"\n💼 Leads Identified: {len(result.get('data', []))}")
    print(f"   Quality Threshold: {result['quality_score']:.0%}")
    
    # Could feed this into lead_finder for qualification
    print("\n🔗 Next Step: Feed to lead_finder for qualification")


# ═════════════════════════════════════════════════════════════════════════
# MAIN: Run Selected Examples
# ═════════════════════════════════════════════════════════════════════════

async def main():
    print("""
╔════════════════════════════════════════════════════════════╗
║     Intelligence Agent - Usage Examples                   ║
║   Smart Web Data Extraction with Iterative Refinement     ║
╚════════════════════════════════════════════════════════════╝

Choose an example to run:
  1. Restaurant Extraction
  2. Product Listings
  3. Job Postings
  4. Real Estate
  5. Multi-Source Aggregation
  6. News Aggregation
  7. Custom Data Extraction
  8. Smart Retry & Format Detection
  9. Leads with Intelligence
  0. Run All Examples
  q. Quit
""")
    
    choice = input("Enter your choice (0-9, q): ").strip().lower()
    
    examples = {
        '1': example_1_restaurant_extraction,
        '2': example_2_product_extraction,
        '3': example_3_job_extraction,
        '4': example_4_realestate_extraction,
        '5': example_5_multi_source,
        '6': example_6_news_aggregation,
        '7': example_7_custom_extraction,
        '8': example_8_smart_retry,
        '9': example_9_leads_with_intelligence,
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
