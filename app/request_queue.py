"""
Request Queue Manager - FIFO queue for chat requests
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Callable, Awaitable
from dataclasses import dataclass, field
import uuid


@dataclass
class QueuedRequest:
    """Represents a request in the queue"""
    request_id: str
    session_id: str
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    result_future: asyncio.Future = field(default_factory=lambda: asyncio.get_event_loop().create_future())


class RequestQueue:
    """
    FIFO request queue for chat messages.
    Ensures requests are processed in order of submission.
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
        
        self._queue: asyncio.Queue[QueuedRequest] = asyncio.Queue()
        self._processing = False
        self._processor_task = None
        self._request_handler: Callable[[str, str], Awaitable[Dict[str, Any]]] = None
        
        RequestQueue._initialized = True
        print("[OK] Request Queue initialized (FIFO)")
    
    def set_handler(self, handler: Callable[[str, str], Awaitable[Dict[str, Any]]]):
        """
        Set the handler function for processing requests.
        Handler should be async and take (session_id, message) -> Dict
        """
        self._request_handler = handler
    
    async def start_processor(self):
        """Start the queue processor if not already running"""
        if self._processing:
            return
        
        self._processing = True
        self._processor_task = asyncio.create_task(self._process_queue())
        print("[START] Queue processor started")
    
    async def stop_processor(self):
        """Stop the queue processor"""
        self._processing = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass
        print("[STOP] Queue processor stopped")
    
    async def _process_queue(self):
        """Main queue processing loop (FIFO)"""
        while self._processing:
            try:
                # Wait for next request
                request = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0  # Check every second if we should stop
                )
                
                try:
                    if self._request_handler:
                        # Process the request
                        result = await self._request_handler(request.session_id, request.message)
                        request.result_future.set_result(result)
                    else:
                        request.result_future.set_exception(
                            Exception("No request handler configured")
                        )
                except Exception as e:
                    request.result_future.set_exception(e)
                finally:
                    self._queue.task_done()
                    
            except asyncio.TimeoutError:
                # No request in queue, continue loop
                continue
            except asyncio.CancelledError:
                break
    
    async def enqueue(self, session_id: str, message: str) -> Dict[str, Any]:
        """
        Add a request to the queue and wait for its result.
        Returns the result from the handler.
        """
        # Ensure processor is running
        if not self._processing:
            await self.start_processor()
        
        # Create queued request
        request = QueuedRequest(
            request_id=str(uuid.uuid4()),
            session_id=session_id,
            message=message
        )
        
        # Add to queue
        await self._queue.put(request)
        
        # Wait for result
        result = await request.result_future
        return result
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self._queue.qsize()
    
    def get_status(self) -> Dict:
        """Get queue status"""
        return {
            'queue_size': self._queue.qsize(),
            'is_processing': self._processing,
            'has_handler': self._request_handler is not None
        }


# Global instance
request_queue = RequestQueue()
