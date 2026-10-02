"""
Continuous Batching - Inspired by vLLM
Efficient batching of requests with different sequence lengths
"""

import torch
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from collections import OrderedDict
import heapq

logger = logging.getLogger(__name__)


@dataclass
class BatchItem:
    """Item in a batch"""
    request_id: str
    tokens: List[int]
    seq_len: int
    priority: int
    created_at: datetime = field(default_factory=datetime.now)
    max_new_tokens: int = 256
    
    def __lt__(self, other):
        """For priority queue ordering"""
        return self.priority < other.priority


@dataclass
class BatchConfig:
    """Configuration for continuous batching"""
    max_batch_size: int = 32
    max_batch_tokens: int = 4096
    max_seq_len: int = 2048
    enable_continuous: bool = True
    timeout_ms: int = 100


class ContinuousBatcher:
    """
    Manages continuous batching of requests
    
    Key features:
    - Requests of different lengths in one batch
    - Efficient use of GPU memory
    - Priority-based scheduling
    - Token-based batching
    """
    
    def __init__(self, config: BatchConfig):
        self.config = config
        self.pending_requests = OrderedDict()
        self.current_batch: List[BatchItem] = []
        self.completed_batches = 0
        self.total_tokens_processed = 0
    
    def add_request(self, request_id: str, tokens: List[int], 
                   priority: int = 0, max_new_tokens: int = 256) -> bool:
        """Add request to pending queue"""
        seq_len = len(tokens)
        
        if seq_len > self.config.max_seq_len:
            logger.warning(f"Request {request_id} exceeds max sequence length")
            return False
        
        batch_item = BatchItem(
            request_id=request_id,
            tokens=tokens,
            seq_len=seq_len,
            priority=priority,
            max_new_tokens=max_new_tokens
        )
        
        self.pending_requests[request_id] = batch_item
        logger.debug(f"Added request {request_id} to pending queue (seq_len={seq_len})")
        return True
    
    def create_batch(self) -> Optional[List[BatchItem]]:
        """Create a batch from pending requests"""
        if not self.pending_requests:
            return None
        
        batch = []
        total_tokens = 0
        
        # Sort by priority
        sorted_requests = sorted(
            self.pending_requests.values(),
            key=lambda x: (x.priority, x.created_at)
        )
        
        for item in sorted_requests:
            # Check if batch is full
            if len(batch) >= self.config.max_batch_size:
                break
            
            # Check token limit
            new_tokens = total_tokens + item.seq_len + item.max_new_tokens
            if new_tokens > self.config.max_batch_tokens and batch:
                break
            
            batch.append(item)
            total_tokens = new_tokens
            del self.pending_requests[item.request_id]
        
        if batch:
            self.current_batch = batch
            logger.info(f"Created batch with {len(batch)} requests, "
                       f"total tokens: {total_tokens}")
            return batch
        
        return None
    
    def process_batch(self, batch: List[BatchItem]) -> Dict:
        """Process a batch (simulate inference)"""
        batch_tokens = sum(item.seq_len + item.max_new_tokens for item in batch)
        
        result = {
            'batch_size': len(batch),
            'batch_tokens': batch_tokens,
            'requests': [
                {
                    'id': item.request_id,
                    'seq_len': item.seq_len,
                    'max_new_tokens': item.max_new_tokens,
                }
                for item in batch
            ],
            'efficiency': self._calculate_efficiency(batch),
        }
        
        self.completed_batches += 1
        self.total_tokens_processed += batch_tokens
        
        return result
    
    def _calculate_efficiency(self, batch: List[BatchItem]) -> float:
        """Calculate batch efficiency (tokens utilized vs theoretical max)"""
        max_seq_len = max(item.seq_len for item in batch)
        utilized = sum(item.seq_len for item in batch)
        theoretical_max = len(batch) * max_seq_len
        
        return (utilized / theoretical_max * 100) if theoretical_max > 0 else 0
    
    def get_stats(self) -> Dict:
        """Get batching statistics"""
        return {
            'pending_requests': len(self.pending_requests),
            'completed_batches': self.completed_batches,
            'total_tokens_processed': self.total_tokens_processed,
            'avg_batch_size': (self.total_tokens_processed / self.completed_batches
                              if self.completed_batches > 0 else 0),
        }


class TokenBasedScheduler:
    """
    Schedule requests based on token budget
    Ensures GPU stays at target token throughput
    """
    
    def __init__(self, target_tokens_per_sec: int = 1000, 
                 max_tokens_per_batch: int = 4096):
        self.target_tokens_per_sec = target_tokens_per_sec
        self.max_tokens_per_batch = max_tokens_per_batch
        self.token_budget = 0
        self.processed_count = 0
    
    def should_batch(self, pending_tokens: int) -> bool:
        """Decide if batch should be processed"""
        return pending_tokens >= min(self.max_tokens_per_batch // 2, 256)
    
    def allocate_tokens(self, num_tokens: int) -> None:
        """Allocate tokens from budget"""
        self.token_budget -= num_tokens
        self.processed_count += 1
    
    def get_budget(self) -> int:
        """Get remaining token budget"""
        return max(0, self.token_budget)


class DynamicBatchingScheduler:
    """
    Advanced scheduler combining continuous batching with dynamic sizing
    """
    
    def __init__(self, config: BatchConfig):
        self.config = config
        self.batcher = ContinuousBatcher(config)
        self.token_scheduler = TokenBasedScheduler()
        self.batch_history = []
    
    def schedule_request(self, request_id: str, tokens: List[int],
                        priority: int = 0) -> bool:
        """Schedule a request using advanced scheduling"""
        success = self.batcher.add_request(
            request_id=request_id,
            tokens=tokens,
            priority=priority
        )
        
        if success:
            # Check if we should create a batch
            pending_tokens = sum(
                item.seq_len for item in self.batcher.pending_requests.values()
            )
            
            if self.token_scheduler.should_batch(pending_tokens):
                batch = self.batcher.create_batch()
                if batch:
                    result = self.batcher.process_batch(batch)
                    self.batch_history.append(result)
                    
                    total_batch_tokens = result['batch_tokens']
                    self.token_scheduler.allocate_tokens(total_batch_tokens)
        
        return success
    
    def get_schedule_efficiency(self) -> float:
        """Get overall scheduling efficiency"""
        if not self.batch_history:
            return 0.0
        
        avg_efficiency = sum(
            b['efficiency'] for b in self.batch_history
        ) / len(self.batch_history)
        
        return avg_efficiency
    
    def print_stats(self) -> None:
        """Print scheduling statistics"""
        stats = self.batcher.get_stats()
        print(f"""
╔═══════════════════════════════════╗
║   CONTINUOUS BATCHING STATS       ║
╚═══════════════════════════════════╝
Pending Requests: {stats['pending_requests']}
Completed Batches: {stats['completed_batches']}
Total Tokens Processed: {stats['total_tokens_processed']}
Avg Batch Size: {stats['avg_batch_size']:.1f}
Schedule Efficiency: {self.get_schedule_efficiency():.1f}%
        """)
