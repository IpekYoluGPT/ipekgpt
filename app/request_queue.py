"""
Request Queue Manager - Concurrent processing for chat requests
Allows multiple requests to be processed in parallel with a configurable limit
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Callable, Awaitable
from dataclasses import dataclass, field
import uuid


# Maximum number of concurrent requests to process
MAX_CONCURRENT_REQUESTS = 5


@dataclass
class QueuedRequest:
    """Represents a request in the queue"""
    request_id: str
    session_id: str
    message: str
    history: list = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    result_future: asyncio.Future = field(default_factory=lambda: asyncio.get_event_loop().create_future())


class RequestQueue:
    """
    Concurrent request processor for chat messages.
    Allows multiple requests to be processed in parallel (up to MAX_CONCURRENT_REQUESTS).
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if RequestQueue._initialized:
            return
        
        self._semaphore: asyncio.Semaphore = None  # Will be initialized on first use
        self._processing = False
        self._active_requests = 0
        self._request_handler: Callable[[str, str, list], Awaitable[Dict[str, Any]]] = None
        
        RequestQueue._initialized = True
        print(f"[OK] Request Queue initialized (max concurrent: {MAX_CONCURRENT_REQUESTS})")
    
    def set_handler(self, handler: Callable[[str, str, list], Awaitable[Dict[str, Any]]]):
        """
        Set the handler function for processing requests.
        Handler should be async and take (session_id, message, history) -> Dict
        """
        self._request_handler = handler
    
    async def start_processor(self):
        """Start the queue processor if not already running"""
        if self._processing:
            return
        
        self._processing = True
        self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        print("[START] Concurrent request processor started")
    
    async def stop_processor(self):
        """Stop the queue processor"""
        self._processing = False
        # Wait for active requests to complete (with timeout)
        timeout = 30
        while self._active_requests > 0 and timeout > 0:
            await asyncio.sleep(0.5)
            timeout -= 0.5
        print("[STOP] Request processor stopped")
    
    async def _handle_request(self, request: QueuedRequest):
        """Handle a single request with semaphore-based concurrency control"""
        async with self._semaphore:
            self._active_requests += 1
            try:
                if self._request_handler:
                    result = await self._request_handler(
                        request.session_id, 
                        request.message, 
                        request.history
                    )
                    request.result_future.set_result(result)
                else:
                    request.result_future.set_exception(
                        Exception("No request handler configured")
                    )
            except Exception as e:
                request.result_future.set_exception(e)
            finally:
                self._active_requests -= 1
    
    async def enqueue(self, session_id: str, message: str, history: list = None) -> Dict[str, Any]:
        """
        Process a request with concurrent execution.
        Returns the result from the handler.
        Multiple requests can be processed in parallel (up to MAX_CONCURRENT_REQUESTS).
        """
        # Ensure processor is running
        if not self._processing:
            await self.start_processor()
        
        # Create request
        request = QueuedRequest(
            request_id=str(uuid.uuid4()),
            session_id=session_id,
            message=message,
            history=history or []
        )
        
        # Start processing immediately (don't wait for others to complete)
        asyncio.create_task(self._handle_request(request))
        
        # Wait for THIS request's result
        result = await request.result_future
        return result
    
    def get_active_count(self) -> int:
        """Get number of currently active requests"""
        return self._active_requests
    
    def get_status(self) -> Dict:
        """Get processor status"""
        return {
            'active_requests': self._active_requests,
            'max_concurrent': MAX_CONCURRENT_REQUESTS,
            'is_processing': self._processing,
            'has_handler': self._request_handler is not None
        }


# Global instance
request_queue = RequestQueue()
