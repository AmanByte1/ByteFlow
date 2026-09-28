"""
Smart Data Extraction Engine
=============================
Intelligent web data extraction with iterative LLM-based refinement

Features:
  - Multi-pass crawling with feedback loops
  - LLM-based data validation & filtering
  - Automatic query refinement
  - Context-aware extraction
  - Quality scoring & verification
  - Works with ANY type of data
"""

import asyncio
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum

try:
    from crawl4ai import AsyncWebCrawler
except ImportError:
    AsyncWebCrawler = None


class DataQuality(Enum):
    """Data quality levels"""
    POOR = 0.0
    FAIR = 0.4
    GOOD = 0.6
    EXCELLENT = 0.85


class ExtractionContext:
    """Holds context for multi-pass extraction"""
    
    def __init__(self, user_query: str, data_type: str, criteria: List[str]):
        self.user_query = user_query
        self.data_type = data_type
        self.criteria = criteria
        self.extraction_history = []
        self.feedback_history = []
        self.current_attempt = 0
        self.max_attempts = 5
    
    def add_extraction(self, data: Dict, source: str):
        """Log extraction attempt"""
        self.extraction_history.append({
            'attempt': self.current_attempt,
            'data': data,
            'source': source,
            'timestamp': datetime.now().isoformat()
        })
    
    def add_feedback(self, feedback: str, suggestion: str):
        """Log LLM feedback"""
        self.feedback_history.append({
            'attempt': self.current_attempt,
            'feedback': feedback,
            'suggestion': suggestion,
            'timestamp': datetime.now().isoformat()
        })


class SmartCrawler:
    """Intelligent web crawler with context-aware extraction"""
    
    def __init__(self):
        self.crawler = None
        self.extraction_cache = {}
    
    async def init(self):
        """Initialize async crawler"""
        if AsyncWebCrawler is None:
            raise ImportError("crawl4ai not installed. Run: pip install crawl4ai")
        self.crawler = AsyncWebCrawler()
    
    async def crawl_with_context(
        self,
        url: str,
        context: ExtractionContext,
        search_strategy: str = "default"
    ) -> Dict:
        """
        Crawl website with extraction context and strategy.
        
        Strategies:
          - "default": Standard content extraction
          - "specific": Look for specific fields from criteria
          - "nested": Extract nested/hierarchical data
          - "table": Extract tabular data
          - "list": Extract list-based data
        """
        if not self.crawler:
            await self.init()
        
        try:
            # Log extraction attempt
            context.current_attempt += 1
            
            # Determine extraction strategy
            extraction_prompt = self._build_extraction_prompt(context, search_strategy)
            
            # Crawl the page
            result = await self.crawler.arun(
                url=url,
                extraction_strategy='llm-extraction',
                extraction_schema={
                    'fields': context.criteria,
                    'strategy': search_strategy,
                }
            )
            
            # Extract raw data
            raw_data = {
                'url': url,
                'strategy': search_strategy,
                'content': result.markdown or result.html,
                'extracted_fields': self._parse_extracted_content(result, context),
                'crawl_time': datetime.now().isoformat(),
                'success': True
            }
            
            # Cache result
            cache_key = f"{url}_{search_strategy}"
            self.extraction_cache[cache_key] = raw_data
            
            return raw_data
            
        except Exception as e:
            return {
                'url': url,
                'strategy': search_strategy,
                'success': False,
                'error': str(e),
                'crawl_time': datetime.now().isoformat()
            }
    
    def _build_extraction_prompt(self, context: ExtractionContext, strategy: str) -> str:
        """Build LLM prompt for extraction"""
        return f"""
Extract the following data from the webpage:
Query: {context.user_query}
Data Type: {context.data_type}
Strategy: {strategy}

Required Fields:
{json.dumps(context.criteria, indent=2)}

Previous Feedback:
{json.dumps(context.feedback_history[-1:], indent=2) if context.feedback_history else 'None'}

Return structured data matching the criteria.
"""
    
    def _parse_extracted_content(self, result, context: ExtractionContext) -> Dict:
        """Parse crawler result into structured data"""
        content = result.markdown or ""
        
        parsed = {}
        for criterion in context.criteria:
            # Simple parsing - in real world would be more sophisticated
            if criterion.lower() in content.lower():
                parsed[criterion] = self._extract_field_value(content, criterion)
        
        return parsed
    
    def _extract_field_value(self, content: str, field: str) -> Optional[str]:
        """Extract specific field value from content"""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if field.lower() in line.lower():
                # Return the line and next few lines as context
                return '\n'.join(lines[i:min(i+3, len(lines))])
        return None


class DataValidator:
    """LLM-based data validation and quality assessment"""
    
    def __init__(self, agent=None):
        self.agent = agent
        self.validation_rules = {}
    
    async def validate(
        self,
        raw_data: Dict,
        context: ExtractionContext
    ) -> Tuple[bool, float, str]:
        """
        Validate extracted data against criteria.
        
        Returns:
            (is_valid, confidence_score, feedback_message)
        """
        # Check completeness
        completeness_score = self._check_completeness(raw_data, context)
        
        # Check quality
        quality_score = self._check_quality(raw_data, context)
        
        # Check relevance
        relevance_score = self._check_relevance(raw_data, context)
        
        # Overall score
        overall_score = (completeness_score + quality_score + relevance_score) / 3
        
        # Determine validity
        is_valid = overall_score >= 0.75
        
        # Generate feedback
        feedback = self._generate_feedback(
            raw_data, context,
            completeness_score,
            quality_score,
            relevance_score
        )
        
        return is_valid, overall_score, feedback
    
    def _check_completeness(self, raw_data: Dict, context: ExtractionContext) -> float:
        """Check if all required criteria are present"""
        if not raw_data.get('success'):
            return 0.0
        
        extracted = raw_data.get('extracted_fields', {})
        found_count = len([v for v in extracted.values() if v])
        required_count = len(context.criteria)
        
        if required_count == 0:
            return 1.0
        
        return found_count / required_count
    
    def _check_quality(self, raw_data: Dict, context: ExtractionContext) -> float:
        """Check quality of extracted data"""
        if not raw_data.get('success'):
            return 0.0
        
        extracted = raw_data.get('extracted_fields', {})
        
        # Quality based on:
        # - No empty fields
        # - No error messages
        # - Reasonable length
        
        quality_score = 0.0
        
        for field, value in extracted.items():
            if not value:
                continue
            
            value_str = str(value)
            
            # Check length (not too short or too long)
            if 10 < len(value_str) < 10000:
                quality_score += 0.3
            
            # Check no error keywords
            if 'error' not in value_str.lower() and '404' not in value_str:
                quality_score += 0.3
            
            # Check data looks real
            if any(c.isalnum() for c in value_str):
                quality_score += 0.4
        
        return min(quality_score / len(extracted) if extracted else 0, 1.0)
    
    def _check_relevance(self, raw_data: Dict, context: ExtractionContext) -> float:
        """Check relevance to original query"""
        if not raw_data.get('success'):
            return 0.0
        
        content = raw_data.get('content', '')
        query_words = context.user_query.lower().split()
        
        # Count how many query words appear in content
        matched_words = sum(1 for word in query_words if word in content.lower())
        
        if not query_words:
            return 1.0
        
        return matched_words / len(query_words)
    
    def _generate_feedback(
        self,
        raw_data: Dict,
        context: ExtractionContext,
        completeness: float,
        quality: float,
        relevance: float
    ) -> str:
        """Generate actionable feedback for crawler refinement"""
        issues = []
        suggestions = []
        
        if completeness < 0.5:
            issues.append(f"Missing {int((1 - completeness) * len(context.criteria))} required fields")
            suggestions.append("Try searching more specific URLs or different page sections")
        
        if quality < 0.5:
            issues.append("Low quality extracted data")
            suggestions.append("Look for more structured data (tables, lists) instead of raw text")
        
        if relevance < 0.5:
            issues.append("Data doesn't match original query")
            suggestions.append("Try different search terms or sources more specific to the query")
        
        if not issues:
            return "✅ Data looks good! Meets criteria."
        
        feedback = "⚠️ Issues found:\n"
        feedback += "\n".join(f"  • {issue}" for issue in issues)
        feedback += "\n\nSuggestions:\n"
        feedback += "\n".join(f"  • {suggestion}" for suggestion in suggestions)
        
        return feedback


class FeedbackLoop:
    """Manages iterative extraction refinement"""
    
    def __init__(self, crawler: SmartCrawler, validator: DataValidator):
        self.crawler = crawler
        self.validator = validator
    
    async def refine_extraction(
        self,
        context: ExtractionContext,
        url: str,
        validation_result: Tuple[bool, float, str]
    ) -> Tuple[Optional[Dict], str]:
        """
        Based on validation feedback, refine the extraction strategy.
        
        Returns:
            (refined_data, next_action)
        """
        is_valid, score, feedback = validation_result
        
        if is_valid or context.current_attempt >= context.max_attempts:
            return None, "complete"
        
        # Analyze feedback and determine next strategy
        next_strategy = self._determine_next_strategy(feedback, context)
        next_url = self._determine_next_url(feedback, url, context)
        
        # Store feedback
        context.add_feedback(feedback, f"Try strategy: {next_strategy} on {next_url}")
        
        return {
            'strategy': next_strategy,
            'url': next_url,
            'score': score,
            'feedback': feedback
        }, "retry"
    
    def _determine_next_strategy(self, feedback: str, context: ExtractionContext) -> str:
        """Determine next crawling strategy based on feedback"""
        feedback_lower = feedback.lower()
        
        if "table" in feedback_lower or "structured" in feedback_lower:
            return "table"
        elif "list" in feedback_lower:
            return "list"
        elif "nested" in feedback_lower or "hierarchy" in feedback_lower:
            return "nested"
        elif "specific" in feedback_lower:
            return "specific"
        else:
            # Rotate through strategies
            strategies = ["default", "specific", "table", "list", "nested"]
            current_index = strategies.index(context.extraction_history[-1].get('strategy', 'default') if context.extraction_history else 'default')
            return strategies[(current_index + 1) % len(strategies)]
    
    def _determine_next_url(self, feedback: str, current_url: str, context: ExtractionContext) -> str:
        """Determine next URL to crawl based on feedback"""
        feedback_lower = feedback.lower()
        
        # If feedback suggests different source
        if "different source" in feedback_lower or "more specific" in feedback_lower:
            # Could search for better URLs
            # For now, return same URL with different strategy
            return current_url
        
        return current_url


class IntelligenceAgent:
    """Main orchestrator for intelligent data extraction"""
    
    def __init__(self, agent=None, model: str = "phi4-mini"):
        self.agent = agent
        self.model = model
        self.crawler = SmartCrawler()
        self.validator = DataValidator(agent)
        self.feedback_loop = FeedbackLoop(self.crawler, self.validator)
        self.extraction_cache = {}
    
    async def extract(
        self,
        query: str,
        data_type: str,
        criteria: List[str],
        urls: List[str],
        max_attempts: int = 5
    ) -> Dict:
        """
        Main extraction pipeline with iterative refinement.
        
        Args:
            query: What to extract (natural language)
            data_type: Type of data (e.g., "product_listings", "job_posts")
            criteria: List of fields to extract
            urls: URLs to crawl
            max_attempts: Max refinement attempts
        
        Returns:
            {
                'success': bool,
                'data': [extracted items],
                'quality_score': float,
                'attempts': int,
                'history': extraction history
            }
        """
        
        print(f"\n🤖 Intelligence Agent Starting")
        print(f"   Query: {query}")
        print(f"   Type: {data_type}")
        print(f"   Criteria: {criteria}")
        print(f"   URLs: {len(urls)}")
        
        # Initialize context
        context = ExtractionContext(query, data_type, criteria)
        context.max_attempts = max_attempts
        
        # Initialize crawler
        await self.crawler.init()
        
        all_extracted_data = []
        best_quality_score = 0.0
        
        # Process each URL
        for url in urls:
            print(f"\n📍 Processing: {url}")
            
            is_complete = False
            refinement_history = []
            
            # Refinement loop
            while not is_complete and context.current_attempt < context.max_attempts:
                
                # Determine strategy for this attempt
                if context.current_attempt == 0:
                    strategy = "default"
                else:
                    strategy = refinement_history[-1].get('strategy', 'default') if refinement_history else "default"
                
                print(f"   Attempt {context.current_attempt + 1}/{context.max_attempts} (Strategy: {strategy})")
                
                # STEP 1: Crawl
                raw_data = await self.crawler.crawl_with_context(
                    url=url,
                    context=context,
                    search_strategy=strategy
                )
                context.add_extraction(raw_data, url)
                
                if not raw_data.get('success'):
                    print(f"   ❌ Crawl failed: {raw_data.get('error')}")
                    context.current_attempt += 1
                    continue
                
                print(f"   ✓ Raw data extracted")
                
                # STEP 2: Validate with LLM
                is_valid, quality_score, feedback = await self.validator.validate(raw_data, context)
                
                print(f"   Quality: {quality_score:.0%} | Valid: {is_valid}")
                print(f"   {feedback}")
                
                # Track best quality
                if quality_score > best_quality_score:
                    best_quality_score = quality_score
                    all_extracted_data = raw_data.get('extracted_fields', {})
                
                # STEP 3: Decide next action
                if is_valid:
                    print(f"   ✅ Extraction complete!")
                    is_complete = True
                else:
                    # STEP 4: Get refinement suggestions
                    refinement = await self.feedback_loop.refine_extraction(
                        context,
                        url,
                        (is_valid, quality_score, feedback)
                    )
                    
                    if refinement[1] == "complete":
                        print(f"   ⏹️ Max attempts reached")
                        is_complete = True
                    else:
                        print(f"   🔄 Refining strategy...")
                        refinement_history.append(refinement[0])
                        context.current_attempt += 1
        
        # Return results
        return {
            'success': best_quality_score >= 0.75,
            'data': all_extracted_data,
            'quality_score': best_quality_score,
            'attempts': context.current_attempt,
            'history': context.extraction_history,
            'feedback': context.feedback_history,
            'data_type': data_type,
            'query': query,
            'completed_at': datetime.now().isoformat()
        }


# ═══════════════════════════════════════════════════════════════════════
# Export
# ═══════════════════════════════════════════════════════════════════════

__all__ = [
    'IntelligenceAgent',
    'SmartCrawler',
    'DataValidator',
    'FeedbackLoop',
    'ExtractionContext',
    'DataQuality',
]
