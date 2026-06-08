import asyncio
import json
from typing import List, Dict, Any
from sse_starlette.sse import ServerSentEvent
from src.utils.logger import logger

class NotificationManager:
    """
    Upravlja slanjem real-time notifikacija klijentima putem SSE (Server-Sent Events).
    Singleton pattern.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(NotificationManager, cls).__new__(cls)
            cls._instance.subscribers: List[asyncio.Queue] = []
            cls._instance.loop = None
        return cls._instance

    async def subscribe(self):
        """
        Kreira novi red čekanja za klijenta i vraća generator stream.
        """
        self.loop = asyncio.get_running_loop()
        queue = asyncio.Queue()
        self.subscribers.append(queue)
        logger.info(f"📡 Novi SSE klijent spojen (Loop: {id(self.loop)}). Ukupno: {len(self.subscribers)}")
        
        try:
            while True:
                # Čekaj na poruku
                message = await queue.get()
                yield message
        except asyncio.CancelledError:
            # Klijent se odspojio
            self.subscribers.remove(queue)
            logger.info(f"🔌 SSE klijent odspojen. Ukupno: {len(self.subscribers)}")

    def broadcast_sync(self, event: str, data: Dict[str, Any]):
        """
        Thread-safe slanje poruke svim aktivnim pretplatnicima iz sinkronog koda.
        """
        if not self.subscribers or not self.loop:
            return

        asyncio.run_coroutine_threadsafe(self.broadcast(event, data), self.loop)

    async def broadcast(self, event: str, data: Dict[str, Any]):
        """
        Šalje poruku svim aktivnim pretplatnicima.
        """
        if not self.subscribers:
            return

        message = ServerSentEvent(
            event=event,
            data=json.dumps(data)
        )
        
        # Šalji svima
        for queue in self.subscribers:
            await queue.put(message)
            
        logger.debug(f"📢 Broadcast: {event} -> {len(self.subscribers)} klijenata")

    # Helper metode za specifične događaje
    
    async def notify_job_update(self, job_id: str, status: str, progress: int, msg: str = ""):
        await self.broadcast("job_update", {
            "job_id": job_id,
            "status": status,
            "progress": progress,
            "message": msg
        })

    async def notify_log(self, level: str, message: str):
        await self.broadcast("log", {
            "level": level,
            "message": message,
            "timestamp": "now" # TODO: pravi timestamp
        })

# Globalna instanca
notification_manager = NotificationManager()
