"""
Paged Attention - Inspired by vLLM
Efficient memory management for KV cache using paging
"""

import torch
import logging
from dataclasses import dataclass
from typing import List, Tuple, Optional
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class PagedAttentionConfig:
    """Configuration for paged attention"""
    page_size: int = 16  # Number of tokens per page
    max_pages: int = 512  # Maximum number of pages
    enable_reuse: bool = True  # Enable KV cache reuse


class KVCache:
    """Key-Value cache with paging support"""
    
    def __init__(self, config: PagedAttentionConfig, device: str = "cuda"):
        self.config = config
        self.device = device
        self.pages = []  # List of allocated pages
        self.free_pages = deque()  # Queue of free pages
        self.allocated_pages = {}  # Mapping of sequence to pages
        self.total_allocated = 0
        
        logger.info(f"Initialized KV Cache: page_size={config.page_size}, "
                   f"max_pages={config.max_pages}")
    
    def allocate_pages(self, seq_id: str, num_tokens: int) -> List[int]:
        """Allocate pages for a sequence"""
        num_pages_needed = (num_tokens + self.config.page_size - 1) // self.config.page_size
        
        if len(self.free_pages) < num_pages_needed:
            # Allocate new pages
            for _ in range(num_pages_needed):
                page_id = len(self.pages)
                self.pages.append({
                    'k': torch.zeros(self.config.page_size, 4096, device=self.device),  # Placeholder dims
                    'v': torch.zeros(self.config.page_size, 4096, device=self.device),
                    'seq_id': seq_id,
                    'offset': 0,
                })
                self.total_allocated += 1
        
        # Allocate from free pages
        page_ids = []
        for _ in range(num_pages_needed):
            if self.free_pages:
                page_id = self.free_pages.popleft()
            else:
                page_id = len(self.pages)
                self.pages.append({
                    'k': torch.zeros(self.config.page_size, 4096, device=self.device),
                    'v': torch.zeros(self.config.page_size, 4096, device=self.device),
                    'seq_id': seq_id,
                    'offset': 0,
                })
            
            page_ids.append(page_id)
        
        self.allocated_pages[seq_id] = page_ids
        logger.debug(f"Allocated {num_pages_needed} pages for sequence {seq_id}")
        return page_ids
    
    def free_pages(self, seq_id: str) -> None:
        """Free pages for a sequence"""
        if seq_id in self.allocated_pages:
            page_ids = self.allocated_pages[seq_id]
            for page_id in page_ids:
                self.free_pages.append(page_id)
            del self.allocated_pages[seq_id]
            logger.debug(f"Freed {len(page_ids)} pages for sequence {seq_id}")
    
    def get_cache_size(self) -> int:
        """Get total cache size in bytes"""
        page_size_bytes = self.config.page_size * 4096 * 4  # Assuming float32
        return len(self.pages) * page_size_bytes * 2  # K and V caches
    
    def get_utilization(self) -> float:
        """Get cache utilization percentage"""
        max_size = self.config.max_pages * self.config.page_size * 4096 * 4 * 2
        current_size = self.get_cache_size()
        return (current_size / max_size) * 100 if max_size > 0 else 0


class PagedAttentionScheduler:
    """Schedule and manage paged attention operations"""
    
    def __init__(self, config: PagedAttentionConfig):
        self.config = config
        self.kv_cache = KVCache(config)
        self.active_sequences = {}
        
    def schedule_request(self, request_id: str, num_tokens: int) -> dict:
        """Schedule a request with paged attention"""
        pages = self.kv_cache.allocate_pages(request_id, num_tokens)
        
        self.active_sequences[request_id] = {
            'pages': pages,
            'num_tokens': num_tokens,
            'created_at': torch.cuda.Event(enable_timing=True),
        }
        
        return {
            'request_id': request_id,
            'pages': pages,
            'page_size': self.config.page_size,
            'cache_size_mb': self.kv_cache.get_cache_size() / (1024**2),
        }
    
    def complete_request(self, request_id: str) -> None:
        """Mark request as complete and free resources"""
        if request_id in self.active_sequences:
            self.kv_cache.free_pages(request_id)
            del self.active_sequences[request_id]
            logger.info(f"Completed request {request_id}, freed pages")
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics"""
        return {
            'total_pages': len(self.kv_cache.pages),
            'allocated_pages': sum(len(p) for p in self.kv_cache.allocated_pages.values()),
            'free_pages': len(self.kv_cache.free_pages),
            'utilization_percent': self.kv_cache.get_utilization(),
            'active_sequences': len(self.active_sequences),
        }


class PagedAttentionOptimizer:
    """Optimize attention computation with paging"""
    
    def __init__(self, config: PagedAttentionConfig):
        self.config = config
        self.scheduler = PagedAttentionScheduler(config)
    
    def compute_attention(self, query: torch.Tensor, page_ids: List[int]) -> torch.Tensor:
        """
        Compute attention using paged KV cache
        
        This is a simplified version - actual implementation would use CUDA kernels
        """
        batch_size, seq_len, hidden_dim = query.shape
        output = torch.zeros_like(query)
        
        # For each page
        for page_id in page_ids:
            page = self.scheduler.kv_cache.pages[page_id]
            k = page['k'][:self.config.page_size]
            v = page['v'][:self.config.page_size]
            
            # Compute attention scores
            scores = torch.matmul(query, k.transpose(-2, -1)) / (hidden_dim ** 0.5)
            scores = torch.softmax(scores, dim=-1)
            
            # Apply attention to values
            page_output = torch.matmul(scores, v)
            output += page_output
        
        return output
    
    def optimize_batch(self, requests: List[dict]) -> dict:
        """
        Optimize a batch of requests with paged attention
        
        Returns: Optimized batch configuration
        """
        scheduled = []
        total_cache_needed = 0
        
        for request in requests:
            request_id = request['id']
            num_tokens = request['num_tokens']
            
            schedule = self.scheduler.schedule_request(request_id, num_tokens)
            scheduled.append(schedule)
            total_cache_needed += schedule['cache_size_mb']
        
        return {
            'scheduled_requests': scheduled,
            'total_cache_mb': total_cache_needed,
            'cache_stats': self.scheduler.get_cache_stats(),
        }
