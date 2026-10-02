"""
Request Optimizer - Queue and prioritize inference requests intelligently
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class RequestPriority(Enum):
    """Request priority levels"""
    LOW = 3
    NORMAL = 2
    HIGH = 1
    CRITICAL = 0


@dataclass(order=True)
class InferenceRequest:
    """An inference request"""
    priority: int = field(compare=True)
    request_id: str = field(compare=False)
    prompt: str = field(compare=False)
    model_name: str = field(compare=False)
    max_tokens: int = field(compare=False, default=256)
    temperature: float = field(compare=False, default=0.7)
    callback: Optional[Callable] = field(compare=False, default=None)
    timestamp: float = field(compare=False, default_factory=time.time)
    metadata: dict = field(compare=False, default_factory=dict)


@dataclass
class InferenceResult:
    """Result of an inference"""
    request_id: str
    response: str
    model_name: str
    tokens_generated: int
    latency_ms: float
    timestamp: float = field(default_factory=time.time)
    success: bool = True
    error: Optional[str] = None


class RequestOptimizer:
    """Manages inference request queue with intelligent prioritization"""
    
    def __init__(self, max_queue_size: int = 100, max_batch_size: int = 4):
        self.max_queue_size = max_queue_size
        self.max_batch_size = max_batch_size
        self.queue: asyncio.PriorityQueue = None
        self.results_cache: dict = {}
        self.request_count = 0
        self.completed_count = 0
        self.failed_count = 0
        self.total_latency = 0.0
    
    async def initialize(self):
        """Initialize async queue"""
        self.queue = asyncio.PriorityQueue(maxsize=self.max_queue_size)
    
    async def submit_request(self, 
                            prompt: str,
                            model_name: str,
                            priority: RequestPriority = RequestPriority.NORMAL,
                            max_tokens: int = 256,
                            temperature: float = 0.7,
                            callback: Optional[Callable] = None,
                            metadata: dict = None) -> str:
        """
        Submit an inference request
        
        Returns:
            request_id: Unique ID for this request
        """
        self.request_count += 1
        request_id = f"req_{self.request_count}_{int(time.time() * 1000)}"
        
        request = InferenceRequest(
            priority=priority.value,
            request_id=request_id,
            prompt=prompt,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            callback=callback,
            metadata=metadata or {}
        )
        
        try:
            await asyncio.wait_for(
                self.queue.put(request),
                timeout=5.0
            )
            logger.info(f"Request {request_id} queued with {priority.name} priority")
            return request_id
        except asyncio.TimeoutError:
            logger.error(f"Failed to queue request {request_id}: queue full")
            raise RuntimeError("Request queue is full")
    
    async def get_next_request(self, timeout: float = 5.0) -> Optional[InferenceRequest]:
        """Get next request from queue"""
        try:
            priority, request = await asyncio.wait_for(
                self.queue.get(),
                timeout=timeout
            )
            return request
        except asyncio.TimeoutError:
            return None
    
    async def batch_requests(self, batch_size: int = None) -> list:
        """Get a batch of requests from queue"""
        batch_size = batch_size or self.max_batch_size
        batch = []
        
        while len(batch) < batch_size:
            try:
                request = await asyncio.wait_for(
                    self.get_next_request(timeout=0.5),
                    timeout=0.5
                )
                if request:
                    batch.append(request)
            except asyncio.TimeoutError:
                break
        
        return batch
    
    async def store_result(self, result: InferenceResult) -> None:
        """Store inference result"""
        self.results_cache[result.request_id] = result
        
        if result.success:
            self.completed_count += 1
            self.total_latency += result.latency_ms
        else:
            self.failed_count += 1
        
        logger.info(f"Result stored for {result.request_id}: {result.latency_ms:.1f}ms")
        
        # Call callback if provided
        if result.request_id in self.results_cache:
            # Find original request
            # This is a simplified version - full implementation would track callbacks
            pass
    
    async def get_result(self, request_id: str, timeout: float = 60.0) -> Optional[InferenceResult]:
        """Get result for a specific request"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if request_id in self.results_cache:
                return self.results_cache[request_id]
            await asyncio.sleep(0.1)
        
        logger.warning(f"Result for {request_id} not available after {timeout}s")
        return None
    
    async def wait_for_result(self, request_id: str, timeout: float = 60.0) -> InferenceResult:
        """Wait for and return a result"""
        result = await self.get_result(request_id, timeout)
        if result is None:
            raise TimeoutError(f"No result for request {request_id} after {timeout}s")
        return result
    
    def get_queue_stats(self) -> dict:
        """Get queue statistics"""
        queue_size = 0
        if self.queue:
            queue_size = self.queue.qsize()
        
        avg_latency = (self.total_latency / self.completed_count) if self.completed_count > 0 else 0
        
        return {
            "queue_size": queue_size,
            "total_requests": self.request_count,
            "completed": self.completed_count,
            "failed": self.failed_count,
            "pending": self.request_count - self.completed_count - self.failed_count,
            "average_latency_ms": avg_latency,
            "success_rate": (self.completed_count / self.request_count * 100) if self.request_count > 0 else 0,
        }
    
    def print_stats(self):
        """Print queue statistics"""
        stats = self.get_queue_stats()
        print(f"""
╔═══════════════════════════════════╗
║    REQUEST QUEUE STATISTICS       ║
╚═══════════════════════════════════╝
Queue Size: {stats['queue_size']}
Total Requests: {stats['total_requests']}
Completed: {stats['completed']}
Failed: {stats['failed']}
Pending: {stats['pending']}
Average Latency: {stats['average_latency_ms']:.1f}ms
Success Rate: {stats['success_rate']:.1f}%
        """)
    
    def export_stats(self) -> dict:
        """Export statistics as dictionary"""
        return self.get_queue_stats()
    
    def clear_old_results(self, max_age_seconds: int = 3600) -> int:
        """Clear results older than max_age_seconds"""
        current_time = time.time()
        to_remove = []
        
        for request_id, result in self.results_cache.items():
            if current_time - result.timestamp > max_age_seconds:
                to_remove.append(request_id)
        
        for request_id in to_remove:
            del self.results_cache[request_id]
        
        logger.info(f"Cleared {len(to_remove)} old results")
        return len(to_remove)
