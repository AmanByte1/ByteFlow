"""
Smart Data Extraction Engine v2 - IMPROVED
============================================
Intelligent web data extraction with LLM-based validation and AI agent loop.

Key Improvements:
  - Real LLM-based extraction (not just keyword matching)
  - Proper crawl4ai integration with timeouts
  - Genuine validation using AI agent
  - Smart feedback loop with LLM reasoning
  - Error recovery and retry logic
  - Structured data parsing (JSON-LD, metadata, tables)
  - Type-aware field validation
"""

import asyncio
import json
import re
from typing import Dict, List, Optional, Tuple, Any
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
        self.validation_history = []
        self.current_attempt = 0
        self.max_attempts = 5
    
    def add_extraction(self, data: Dict, source: str, strategy: str):
        """Log extraction attempt"""
        self.extraction_history.append({
            'attempt': self.current_attempt,
            'data': data,
            'source': source,
            'strategy': strategy,
            'timestamp': datetime.now().isoformat()
        })
    
    def add_feedback(self, feedback: str, suggestion: str):
        """Log AI feedback"""
        self.feedback_history.append({
            'attempt': self.current_attempt,
            'feedback': feedback,
            'suggestion': suggestion,
            'timestamp': datetime.now().isoformat()
        })
    
    def add_validation(self, is_valid: bool, score: float, details: Dict):
        """Log validation result"""
        self.validation_history.append({
            'attempt': self.current_attempt,
            'valid': is_valid,
            'score': score,
            'details': details,
            'timestamp': datetime.now().isoformat()
        })


class SmartCrawler:
    """Intelligent web crawler with context-aware extraction"""
    
    def __init__(self, timeout: float = 30.0):
        self.crawler = None
        self.extraction_cache = {}
        self.timeout = timeout
    
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
        Crawl website with timeout and error recovery.
        
        Strategies:
          - "default": Standard content extraction
          - "specific": Look for specific fields from criteria
          - "nested": Extract nested/hierarchical data
          - "table": Extract tabular data
          - "list": Extract list-based data
        """
        if not self.crawler:
            await self.init()
        
        context.current_attempt += 1
        cache_key = f"{url}_{search_strategy}"
        
        # Try cache first for same strategy
        if cache_key in self.extraction_cache and context.current_attempt > 1:
            cached = self.extraction_cache[cache_key]
            return {
                **cached,
                'cached': True,
                'cache_age': datetime.now().isoformat()
            }
        
        try:
            # Crawl with timeout
            result = await asyncio.wait_for(
                self._do_crawl(url),
                timeout=self.timeout
            )
            
            # Extract raw data
            content = result.markdown or result.cleaned_html or ""
            
            if not content or len(content) < 50:
                return {
                    'url': url,
                    'strategy': search_strategy,
                    'success': False,
                    'error': 'No meaningful content extracted',
                    'crawl_time': datetime.now().isoformat()
                }
            
            raw_data = {
                'url': url,
                'strategy': search_strategy,
                'content': content,
                'html': result.html or "",
                'success': True,
                'crawl_time': datetime.now().isoformat()
            }
            
            # Cache result
            self.extraction_cache[cache_key] = raw_data
            context.add_extraction(raw_data, url, search_strategy)
            
            return raw_data
        
        except asyncio.TimeoutError:
            return {
                'url': url,
                'strategy': search_strategy,
                'success': False,
                'error': f'Crawl timeout (>{self.timeout}s)',
                'crawl_time': datetime.now().isoformat()
            }
        except Exception as e:
            error_msg = str(e)[:100]
            return {
                'url': url,
                'strategy': search_strategy,
                'success': False,
                'error': f'Crawl failed: {error_msg}',
                'crawl_time': datetime.now().isoformat()
            }
    
    async def _do_crawl(self, url: str):
        """Actual crawl operation - can be overridden for testing"""
        return await self.crawler.arun(
            url=url,
            bypass_cache=True,
            wait_until="networkidle",
            screenshot=False
        )


class StructuredDataExtractor:
    """Extract data from JSON-LD, metadata, tables"""
    
    @staticmethod
    def extract_json_ld(content: str) -> Dict:
        """Extract JSON-LD structured data"""
        try:
            pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            
            for match in matches:
                try:
                    data = json.loads(match)
                    return data
                except:
                    continue
        except:
            pass
        return {}
    
    @staticmethod
    def extract_metadata(content: str) -> Dict:
        """Extract from meta tags and Open Graph"""
        metadata = {}
        
        # Open Graph
        og_pattern = r'<meta[^>]*property=["\']og:([^"\']+)["\'][^>]*content=["\']([^"\']*)["\']'
        for key, value in re.findall(og_pattern, content, re.IGNORECASE):
            metadata[f"og_{key}"] = value
        
        # Twitter Card
        twitter_pattern = r'<meta[^>]*name=["\']twitter:([^"\']+)["\'][^>]*content=["\']([^"\']*)["\']'
        for key, value in re.findall(twitter_pattern, content, re.IGNORECASE):
            metadata[f"twitter_{key}"] = value
        
        # Schema.org microdata
        schema_pattern = r'<meta[^>]*itemprop=["\']([^"\']+)["\'][^>]*content=["\']([^"\']*)["\']'
        for key, value in re.findall(schema_pattern, content, re.IGNORECASE):
            metadata[f"schema_{key}"] = value
        
        return metadata
    
    @staticmethod
    def extract_tables(content: str) -> List[Dict]:
        """Extract basic table data"""
        tables = []
        
        # Simple table extraction from markdown (crawl4ai provides markdown)
        lines = content.split('\n')
        current_table = None
        
        for line in lines:
            if '|' in line and current_table is None:
                current_table = {'headers': [], 'rows': []}
            
            if current_table and '|' in line:
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                if current_table['headers'] and cells:
                    current_table['rows'].append(cells)
                elif not current_table['headers']:
                    current_table['headers'] = cells
            elif current_table and '|' not in line and current_table['headers']:
                tables.append(current_table)
                current_table = None
        
        if current_table and current_table['headers']:
            tables.append(current_table)
        
        return tables


class AIExtractor:
    """Use AI agent to intelligently extract fields"""
    
    def __init__(self, agent=None):
        self.agent = agent
    
    async def extract_fields(
        self,
        content: str,
        criteria: List[str],
        user_query: str,
        data_type: str,
        strategy: str
    ) -> Dict:
        """Use AI to extract specific fields from content"""
        
        if not self.agent:
            return {}
        
        # Build extraction prompt
        prompt = f"""You are an expert data extraction AI.

TASK: Extract ONLY the following fields from the webpage content.

QUERY: {user_query}
DATA TYPE: {data_type}
EXTRACTION STRATEGY: {strategy}

REQUIRED FIELDS:
{json.dumps(criteria, indent=2)}

WEBPAGE CONTENT (first 3000 chars):
{content[:3000]}

RULES:
1. Return ONLY a JSON object with the exact field names
2. Use actual values from the page, not descriptions
3. If a field is not found, use null
4. For numeric fields (price, rating, count), extract ONLY the number
5. For text fields, keep it brief (under 100 chars)
6. Use proper JSON format - ONLY return JSON, nothing else

EXAMPLE OUTPUT:
{{
  "name": "Product Name",
  "price": "99.99",
  "rating": "4.5",
  "reviews_count": "1234"
}}

Now extract:"""
        
        try:
            # Call agent with timeout
            response = await asyncio.wait_for(
                self._call_agent(prompt),
                timeout=15.0
            )
            
            # Parse JSON response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                extracted = json.loads(json_match.group())
                return extracted
        except Exception as e:
            pass
        
        return {}
    
    async def _call_agent(self, prompt: str) -> str:
        """Call agent - can be overridden for testing"""
        if self.agent and hasattr(self.agent, 'chat'):
            # Async wrapper
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.agent.chat, prompt)
        return "{}"


class AIValidator:
    """Use AI agent to validate extraction quality"""
    
    def __init__(self, agent=None):
        self.agent = agent
    
    async def validate(
        self,
        extracted_fields: Dict,
        content: str,
        context: ExtractionContext
    ) -> Tuple[bool, float, Dict]:
        """
        Use AI to validate extracted data.
        
        Returns:
            (is_valid, confidence_score, validation_details)
        """
        
        if not self.agent:
            return self._fallback_validate(extracted_fields, context)
        
        validation_prompt = f"""You are a data quality validator.

ORIGINAL QUERY: {context.user_query}
REQUIRED FIELDS: {json.dumps(context.criteria)}
DATA TYPE: {context.data_type}

EXTRACTED DATA:
{json.dumps(extracted_fields, indent=2)}

WEBPAGE CONTENT (first 2000 chars):
{content[:2000]}

Validate each field. Return JSON with:
{{
  "field_validations": {{
    "field_name": {{
      "valid": true/false,
      "reason": "why valid or not"
    }}
  }},
  "overall_completeness": 0.0-1.0,
  "overall_accuracy": 0.0-1.0,
  "overall_relevance": 0.0-1.0,
  "confidence": 0.0-1.0,
  "feedback": "brief feedback"
}}"""
        
        try:
            response = await asyncio.wait_for(
                self._call_agent(validation_prompt),
                timeout=15.0
            )
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                completeness = result.get('overall_completeness', 0.0)
                accuracy = result.get('overall_accuracy', 0.0)
                relevance = result.get('overall_relevance', 0.0)
                confidence = result.get('confidence', 0.0)
                
                # Calculate overall score
                overall_score = (accuracy + completeness + relevance) / 3
                overall_score = overall_score * confidence  # Reduce by confidence
                
                is_valid = overall_score >= 0.75
                
                validation_details = {
                    'completeness': completeness,
                    'accuracy': accuracy,
                    'relevance': relevance,
                    'confidence': confidence,
                    'field_validations': result.get('field_validations', {}),
                    'feedback': result.get('feedback', '')
                }
                
                context.add_validation(is_valid, overall_score, validation_details)
                
                return is_valid, overall_score, validation_details
        except Exception as e:
            pass
        
        # Fallback if AI fails
        return self._fallback_validate(extracted_fields, context)
    
    def _fallback_validate(self, extracted_fields: Dict, context: ExtractionContext) -> Tuple:
        """Fallback validation without AI"""
        # Count non-null fields
        valid_fields = sum(1 for v in extracted_fields.values() if v is not None and str(v).strip())
        completeness = valid_fields / len(context.criteria) if context.criteria else 0.0
        
        # Basic checks
        has_numeric = any(isinstance(v, (int, float)) for v in extracted_fields.values())
        has_text = any(isinstance(v, str) and len(v) > 2 for v in extracted_fields.values())
        quality = 0.5 if (has_numeric or has_text) else 0.0
        
        overall_score = (completeness + quality) / 2
        is_valid = overall_score >= 0.75
        
        context.add_validation(is_valid, overall_score, {
            'completeness': completeness,
            'quality': quality,
            'feedback': 'Fallback validation (no AI)'
        })
        
        return is_valid, overall_score, {'completeness': completeness, 'quality': quality}
    
    async def _call_agent(self, prompt: str) -> str:
        """Call agent - can be overridden for testing"""
        if self.agent and hasattr(self.agent, 'chat'):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.agent.chat, prompt)
        return "{}"


class AIFeedbackLoop:
    """AI-powered feedback loop for intelligent refinement"""
    
    def __init__(self, agent=None):
        self.agent = agent
    
    async def analyze_and_refine(
        self,
        context: ExtractionContext,
        last_validation_details: Dict,
        current_strategy: str
    ) -> Tuple[str, str]:
        """
        Use AI to analyze validation feedback and decide next strategy.
        
        Returns:
            (next_strategy, reasoning)
        """
        
        if not self.agent:
            return self._fallback_next_strategy(context, current_strategy)
        
        feedback_prompt = f"""You are an extraction strategy optimizer.

ORIGINAL QUERY: {context.user_query}
DATA TYPE: {context.data_type}

CURRENT STRATEGY USED: {current_strategy}

VALIDATION FEEDBACK:
{json.dumps(last_validation_details, indent=2)}

AVAILABLE STRATEGIES:
- "default": General extraction
- "table": For data in tables/grids
- "list": For bulleted/numbered lists
- "nested": For hierarchical/nested data
- "specific": For targeted field extraction
- "metadata": For meta tags/JSON-LD

Based on the validation feedback, what's the BEST strategy to try next?

Respond with ONLY:
{{"strategy": "name", "reasoning": "brief explanation"}}"""
        
        try:
            response = await asyncio.wait_for(
                self._call_agent(feedback_prompt),
                timeout=10.0
            )
            
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                strategy = result.get('strategy', 'default')
                reasoning = result.get('reasoning', 'AI refinement')
                
                valid_strategies = ["default", "table", "list", "nested", "specific", "metadata"]
                if strategy in valid_strategies:
                    return strategy, reasoning
        except:
            pass
        
        return self._fallback_next_strategy(context, current_strategy)
    
    def _fallback_next_strategy(self, context: ExtractionContext, current: str) -> Tuple[str, str]:
        """Fallback strategy rotation"""
        strategies = ["default", "specific", "table", "list", "nested", "metadata"]
        try:
            current_idx = strategies.index(current)
            next_strategy = strategies[(current_idx + 1) % len(strategies)]
        except:
            next_strategy = strategies[1]
        
        return next_strategy, "Strategy rotation (no AI available)"
    
    async def _call_agent(self, prompt: str) -> str:
        """Call agent - can be overridden for testing"""
        if self.agent and hasattr(self.agent, 'chat'):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.agent.chat, prompt)
        return "{}"


class IntelligenceAgent:
    """Main orchestrator for intelligent data extraction with AI loop"""
    
    def __init__(self, agent=None, model: str = "llama3"):
        self.agent = agent
        self.model = model
        self.crawler = SmartCrawler(timeout=30.0)
        self.extractor = AIExtractor(agent)
        self.validator = AIValidator(agent)
        self.feedback_loop = AIFeedbackLoop(agent)
        self.structured_extractor = StructuredDataExtractor()
    
    async def extract(
        self,
        query: str,
        data_type: str,
        criteria: List[str],
        urls: List[str],
        max_attempts: int = 5
    ) -> Dict:
        """
        Main extraction pipeline with AI-driven refinement.
        
        Args:
            query: What to extract (natural language)
            data_type: Type of data (e.g., "product", "restaurant")
            criteria: List of fields to extract
            urls: URLs to crawl
            max_attempts: Max refinement attempts per URL
        
        Returns:
            {
                'success': bool,
                'data': extracted_fields,
                'quality_score': float,
                'attempts': int,
                'history': extraction_history,
                'feedback': feedback_history,
                'strategy_evolution': strategy_changes,
                'validation_details': final_validation
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
        
        best_extracted_data = None
        best_quality_score = 0.0
        best_validation_details = {}
        strategy_evolution = []
        
        # Process each URL
        for url in urls:
            print(f"\n📍 Processing: {url}")
            
            is_complete = False
            current_strategy = "default"
            
            # Refinement loop for this URL
            while not is_complete and context.current_attempt < context.max_attempts:
                
                print(f"   Attempt {context.current_attempt + 1}/{context.max_attempts} (Strategy: {current_strategy})")
                
                # STEP 1: Crawl with timeout and error recovery
                raw_data = await self.crawler.crawl_with_context(
                    url=url,
                    context=context,
                    search_strategy=current_strategy
                )
                
                if not raw_data.get('success'):
                    print(f"   ❌ Crawl failed: {raw_data.get('error')}")
                    context.current_attempt += 1
                    continue
                
                print(f"   ✓ Content crawled ({len(raw_data.get('content', ''))} chars)")
                
                # STEP 2: Try structured extraction first
                structured_data = {}
                if current_strategy in ["metadata", "default"]:
                    json_ld = self.structured_extractor.extract_json_ld(raw_data.get('content', ''))
                    metadata = self.structured_extractor.extract_metadata(raw_data.get('content', ''))
                    structured_data = {**json_ld, **metadata}
                    print(f"   ✓ Structured data found: {len(structured_data)} fields")
                
                # STEP 3: Use AI to extract fields
                extracted_fields = await self.extractor.extract_fields(
                    content=raw_data.get('content', ''),
                    criteria=criteria,
                    user_query=query,
                    data_type=data_type,
                    strategy=current_strategy
                )
                
                # Merge with structured data
                if structured_data:
                    for key, value in structured_data.items():
                        if key not in extracted_fields or extracted_fields[key] is None:
                            extracted_fields[key] = value
                
                print(f"   ✓ AI extracted: {sum(1 for v in extracted_fields.values() if v)} fields")
                
                # STEP 4: Validate with AI
                is_valid, quality_score, validation_details = await self.validator.validate(
                    extracted_fields=extracted_fields,
                    content=raw_data.get('content', ''),
                    context=context
                )
                
                print(f"   Quality: {quality_score:.0%} | Valid: {is_valid}")
                print(f"   Feedback: {validation_details.get('feedback', 'N/A')[:80]}")
                
                # Track best quality
                if quality_score > best_quality_score:
                    best_quality_score = quality_score
                    best_extracted_data = extracted_fields
                    best_validation_details = validation_details
                
                # STEP 5: AI-powered decision
                if is_valid:
                    print(f"   ✅ Extraction complete!")
                    is_complete = True
                else:
                    # STEP 6: AI feedback loop
                    if context.current_attempt < context.max_attempts:
                        next_strategy, reasoning = await self.feedback_loop.analyze_and_refine(
                            context=context,
                            last_validation_details=validation_details,
                            current_strategy=current_strategy
                        )
                        
                        print(f"   🔄 Next strategy: {next_strategy}")
                        print(f"   Reasoning: {reasoning[:80]}")
                        
                        strategy_evolution.append({
                            'from': current_strategy,
                            'to': next_strategy,
                            'reason': reasoning,
                            'quality_before': quality_score
                        })
                        
                        current_strategy = next_strategy
                        context.current_attempt += 1
                    else:
                        print(f"   ⏹️ Max attempts reached")
                        is_complete = True
        
        # Return results
        return {
            'success': best_quality_score >= 0.75,
            'data': best_extracted_data or {},
            'quality_score': best_quality_score,
            'attempts': context.current_attempt,
            'history': context.extraction_history,
            'feedback': context.feedback_history,
            'validation_history': context.validation_history,
            'strategy_evolution': strategy_evolution,
            'validation_details': best_validation_details,
            'data_type': data_type,
            'query': query,
            'completed_at': datetime.now().isoformat()
        }


__all__ = [
    'IntelligenceAgent',
    'SmartCrawler',
    'AIExtractor',
    'AIValidator',
    'AIFeedbackLoop',
    'StructuredDataExtractor',
    'ExtractionContext',
    'DataQuality',
]
