import asyncio
from typing import Set
from app.core.logger import logger

class EventBroadcaster:
    def __init__(self):
        # Store active queues for each connected client
        self.queues: Set[asyncio.Queue] = set()

    async def broadcast(self, message: str):
        """Send a message to all connected clients."""
        logger.info(f"Broadcasting '{message}' to {len(self.queues)} queues.")
        for queue in list(self.queues):
            try:
                await queue.put(message)
            except Exception as e:
                logger.error(f"Failed to put in queue: {e}")
                pass

    def add_queue(self, queue: asyncio.Queue):
        self.queues.add(queue)
        logger.info(f"Added queue. Total queues: {len(self.queues)}")

    def remove_queue(self, queue: asyncio.Queue):
        if queue in self.queues:
            self.queues.remove(queue)
            logger.info(f"Removed queue. Total queues: {len(self.queues)}")

# Global singleton instance
broadcaster = EventBroadcaster()
