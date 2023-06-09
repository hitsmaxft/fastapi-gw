from typing import List
import queue
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from .html import html

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

def myfunc(app, manager):
    async def job():
        for i in range(app.queue_limit):
            if not app.queue_system.empty():
                obj = app.queue_system.get_nowait()
                if obj['websocket'] in manager.active_connections:
                    await manager.send_personal_message(f"You wrote: {obj['message']}", obj['websocket'])
    return job

manager = ConnectionManager()
app = FastAPI()

app.queue_system = queue.Queue()
app.queue_limit = 5
app.scheduler = AsyncIOScheduler()
app.scheduler.add_job(myfunc(app, manager), 'interval', seconds=5)
app.scheduler.start()


@app.get("/")
async def main():
    return HTMLResponse(html)


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            app.queue_system.put({"message": message, "websocket": websocket})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print(f"Client #{client_id} disconnected")