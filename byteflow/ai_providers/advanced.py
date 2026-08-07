"""
Advanced Provider Features Module
==================================

Provides advanced capabilities for all providers:
- Caching and response management
- Rate limiting and throttling
- Provider health monitoring
- Load balancing across providers
- Fallback chains
- Cost tracking
"""

import asyncio
import hashlib
import json
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum


class HealthStatus(Enum):
    """Provider health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class CacheEntry:
    """Single cache entry"""
    key: str
    value: str
    created_at: datetime
    ttl: int  # seconds
    hit_count: int = 0
    
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl)
    
    def mark_hit(self):
        """Mark this entry as accessed"""
        self.hit_count += 1


@dataclass
class ProviderStats:
    """Statistics for a provider"""
    name: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_tokens_used: int = 0
    total_cost: float = 0.0
    average_latency: float = 0.0
    last_request_at: Optional[datetime] = None
    last_error: Optional[str] = None
    uptime_percentage: float = 100.0
    
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 100.0
        return (self.successful_requests / self.total_requests) * 100
    
    def __repr__(self):
        return (f"ProviderStats({self.name}: "
                f"requests={self.total_requests}, "
                f"success_rate={self.success_rate():.1f}%, "
                f"cost=${self.total_cost:.2f})")


@dataclass
class ProviderHealth:
    """Health status of a provider"""
    name: str
    status: HealthStatus
    last_check: datetime
    response_time: float
    error_message: Optional[str] = None
    
    def is_healthy(self) -> bool:
        """Check if provider is healthy"""
        return self.status == HealthStatus.HEALTHY
    
    def is_available(self) -> bool:
        """Check if provider is available"""
        return self.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]


class ResponseCache:
    """Response caching system"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0
    
    def _make_key(self, prompt: str, provider: str, model: str) -> str:
        """Generate cache key from prompt and settings"""
        combined = f"{provider}:{model}:{prompt}"
        return hashlib.sha256(combined.encode()).hexdigest()
    
    def get(self, prompt: str, provider: str, model: str) -> Optional[str]:
        """Get cached response"""
        key = self._make_key(prompt, provider, model)
        
        if key not in self.cache:
            self.misses += 1
            return None
        
        entry = self.cache[key]
        if entry.is_expired():
            del self.cache[key]
            self.misses += 1
            return None
        
        entry.mark_hit()
        self.hits += 1
        return entry.value
    
    def set(self, prompt: str, provider: str, model: str, response: str, ttl: Optional[int] = None):
        """Cache a response"""
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), 
                           key=lambda k: self.cache[k].created_at)
            del self.cache[oldest_key]
        
        key = self._make_key(prompt, provider, model)
        ttl = ttl or self.default_ttl
        self.cache[key] = CacheEntry(key, response, datetime.now(), ttl)
    
    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return (self.hits / total) * 100
    
    def size(self) -> int:
        """Get cache size"""
        return len(self.cache)
    
    def __repr__(self):
        return f"ResponseCache(size={self.size()}, hit_rate={self.hit_rate():.1f}%)"


class RateLimiter:
    """Token bucket rate limiter"""
    
    def __init__(self, rate: int = 100, per_second: float = 1.0):
        """
        Initialize rate limiter.
        
        Args:
            rate: Number of requests allowed
            per_second: Time window in seconds
        """
        self.rate = rate
        self.per_second = per_second
        self.tokens = rate
        self.last_update = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """Try to acquire a token"""
        async with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # Add tokens based on elapsed time
            self.tokens = min(
                self.rate,
                self.tokens + (elapsed * self.rate / self.per_second)
            )
            self.last_update = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            return False
    
    async def wait_until_ready(self):
        """Wait until a token is available"""
        while not await self.acquire():
            await asyncio.sleep(0.01)


class ProviderHealthMonitor:
    """Monitor provider health"""
    
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.health_status: Dict[str, ProviderHealth] = {}
        self.checking = False
    
    async def check_provider_health(self, provider) -> ProviderHealth:
        """Check if provider is healthy"""
        start_time = time.time()
        
        try:
            if not provider._initialized:
                await provider.initialize()
            
            # Try to get models
            await provider.list_models()
            
            response_time = time.time() - start_time
            
            health = ProviderHealth(
                name=provider.name,
                status=HealthStatus.HEALTHY,
                last_check=datetime.now(),
                response_time=response_time
            )
        except Exception as e:
            response_time = time.time() - start_time
            health = ProviderHealth(
                name=provider.name,
                status=HealthStatus.UNHEALTHY,
                last_check=datetime.now(),
                response_time=response_time,
                error_message=str(e)
            )
        
        self.health_status[provider.name] = health
        return health
    
    def get_healthy_providers(self, providers: List) -> List:
        """Filter to only healthy providers"""
        return [p for p in providers if self.health_status.get(p.name).is_healthy()]
    
    def get_available_providers(self, providers: List) -> List:
        """Get available providers (healthy or degraded)"""
        return [p for p in providers if self.health_status.get(p.name).is_available()]


class LoadBalancer:
    """Load balancing across multiple providers"""
    
    def __init__(self, providers: List, strategy: str = "round_robin"):
        self.providers = providers
        self.strategy = strategy
        self.current_index = 0
        self.request_counts: Dict[str, int] = {p.name: 0 for p in providers}
    
    def select_provider(self):
        """Select next provider based on strategy"""
        if not self.providers:
            return None
        
        if self.strategy == "round_robin":
            provider = self.providers[self.current_index % len(self.providers)]
            self.current_index += 1
            return provider
        
        elif self.strategy == "least_loaded":
            return min(self.providers, 
                      key=lambda p: self.request_counts[p.name])
        
        elif self.strategy == "random":
            import random
            return random.choice(self.providers)
        
        return self.providers[0]
    
    def record_request(self, provider):
        """Record request to provider"""
        self.request_counts[provider.name] += 1
    
    def reset_counts(self):
        """Reset request counts"""
        for provider in self.providers:
            self.request_counts[provider.name] = 0


class ProviderFallback:
    """Fallback chain for provider failures"""
    
    def __init__(self, providers: List, max_retries: int = 3):
        self.providers = providers
        self.max_retries = max_retries
    
    async def execute_with_fallback(
        self,
        generate_func: Callable,
        *args,
        **kwargs
    ) -> Optional[str]:
        """Execute with fallback to next provider on failure"""
        
        for attempt in range(self.max_retries):
            for provider in self.providers:
                try:
                    if not provider._initialized:
                        await provider.initialize()
                    
                    return await generate_func(provider, *args, **kwargs)
                
                except Exception as e:
                    print(f"Provider {provider.name} failed: {e}")
                    continue
            
            if attempt < self.max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return None


class CostTracker:
    """Track costs across providers"""
    
    def __init__(self):
        self.costs: Dict[str, float] = {}
        self.tokens_used: Dict[str, int] = {}
    
    def add_cost(self, provider_name: str, cost: float, tokens: int = 0):
        """Record cost for provider"""
        self.costs[provider_name] = self.costs.get(provider_name, 0) + cost
        self.tokens_used[provider_name] = self.tokens_used.get(provider_name, 0) + tokens
    
    def get_provider_cost(self, provider_name: str) -> float:
        """Get total cost for provider"""
        return self.costs.get(provider_name, 0)
    
    def get_total_cost(self) -> float:
        """Get total cost across all providers"""
        return sum(self.costs.values())
    
    def get_breakdown(self) -> Dict[str, float]:
        """Get cost breakdown by provider"""
        return self.costs.copy()
    
    def get_cost_per_1k_tokens(self, provider_name: str) -> float:
        """Calculate cost per 1K tokens"""
        tokens = self.tokens_used.get(provider_name, 0)
        if tokens == 0:
            return 0.0
        cost = self.costs.get(provider_name, 0)
        return (cost / tokens) * 1000
    
    def __repr__(self):
        return f"CostTracker(total=${self.get_total_cost():.2f})"


class ProviderMetrics:
    """Comprehensive metrics collection"""
    
    def __init__(self):
        self.stats: Dict[str, ProviderStats] = {}
        self.health_monitor = ProviderHealthMonitor()
        self.cache = ResponseCache()
        self.cost_tracker = CostTracker()
    
    def record_request(
        self,
        provider_name: str,
        tokens_used: int = 0,
        cost: float = 0.0,
        latency: float = 0.0,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Record a provider request"""
        if provider_name not in self.stats:
            self.stats[provider_name] = ProviderStats(provider_name)
        
        stats = self.stats[provider_name]
        stats.total_requests += 1
        stats.total_tokens_used += tokens_used
        stats.total_cost += cost
        stats.last_request_at = datetime.now()
        
        if success:
            stats.successful_requests += 1
        else:
            stats.failed_requests += 1
            stats.last_error = error
        
        # Update average latency
        if stats.average_latency == 0:
            stats.average_latency = latency
        else:
            stats.average_latency = (stats.average_latency + latency) / 2
        
        self.cost_tracker.add_cost(provider_name, cost, tokens_used)
    
    def get_stats(self, provider_name: str) -> Optional[ProviderStats]:
        """Get stats for provider"""
        return self.stats.get(provider_name)
    
    def get_all_stats(self) -> Dict[str, ProviderStats]:
        """Get all stats"""
        return self.stats.copy()
    
    def get_summary(self) -> str:
        """Get summary of all metrics"""
        summary = "Provider Metrics Summary:\n"
        summary += f"Cache: {self.cache}\n"
        summary += f"Total Cost: ${self.cost_tracker.get_total_cost():.2f}\n"
        summary += "\nProvider Stats:\n"
        
        for name, stats in self.stats.items():
            summary += f"  {name}: {stats}\n"
        
        return summary


class ProviderPool:
    """Manage pool of providers with advanced features"""
    
    def __init__(self, providers: List):
        self.providers = providers
        self.metrics = ProviderMetrics()
        self.load_balancer = LoadBalancer(providers)
        self.fallback = ProviderFallback(providers)
        self.initialized = False
    
    async def initialize_all(self):
        """Initialize all providers"""
        for provider in self.providers:
            try:
                await provider.initialize()
            except Exception as e:
                print(f"Failed to initialize {provider.name}: {e}")
        
        self.initialized = True
    
    async def generate_with_fallback(
        self,
        prompt: str,
        **kwargs
    ) -> Optional[str]:
        """Generate with fallback support"""
        
        async def _generate(provider, prompt, **kw):
            return await provider.generate(prompt, **kw)
        
        return await self.fallback.execute_with_fallback(_generate, prompt, **kwargs)
    
    async def generate_with_load_balancing(
        self,
        prompt: str,
        **kwargs
    ) -> Optional[str]:
        """Generate using load balanced provider"""
        
        provider = self.load_balancer.select_provider()
        if not provider:
            return None
        
        try:
            if not provider._initialized:
                await provider.initialize()
            
            response = await provider.generate(prompt, **kwargs)
            self.metrics.record_request(provider.name, success=True)
            self.load_balancer.record_request(provider)
            return response
        
        except Exception as e:
            self.metrics.record_request(provider.name, success=False, error=str(e))
            return await self.generate_with_fallback(prompt, **kwargs)
    
    def get_metrics_summary(self) -> str:
        """Get metrics summary"""
        return self.metrics.get_summary()
    
    async def close_all(self):
        """Close all providers"""
        for provider in self.providers:
            await provider.close()


# Utility functions

async def measure_performance(provider, prompt: str) -> Dict[str, Any]:
    """Measure provider performance"""
    
    start_time = time.time()
    token_count = len(prompt.split())  # Rough estimate
    
    try:
        if not provider._initialized:
            await provider.initialize()
        
        response = await provider.generate(prompt)
        latency = time.time() - start_time
        
        return {
            "provider": provider.name,
            "success": True,
            "latency": latency,
            "input_tokens": token_count,
            "output_tokens": len(response.split()),
            "response_length": len(response)
        }
    
    except Exception as e:
        return {
            "provider": provider.name,
            "success": False,
            "error": str(e),
            "latency": time.time() - start_time
        }


async def benchmark_providers(providers: List, test_prompt: str) -> Dict[str, Any]:
    """Benchmark multiple providers"""
    
    results = {}
    for provider in providers:
        results[provider.name] = await measure_performance(provider, test_prompt)
    
    return results


__all__ = [
    'HealthStatus',
    'CacheEntry',
    'ProviderStats',
    'ProviderHealth',
    'ResponseCache',
    'RateLimiter',
    'ProviderHealthMonitor',
    'LoadBalancer',
    'ProviderFallback',
    'CostTracker',
    'ProviderMetrics',
    'ProviderPool',
    'measure_performance',
    'benchmark_providers',
]
