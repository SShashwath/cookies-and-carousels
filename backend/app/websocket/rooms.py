import asyncio
import json
from collections import defaultdict
from contextlib import suppress
from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.schemas import RoomCode
from app.core.config import settings
from app.db.models import now
from app.db.session import get_db
from app.services.rooms import authenticate, get_room


class RoomHub:
    def __init__(self):
        self.listeners: dict[str, dict[asyncio.Queue, str]] = defaultdict(dict)

    def online(self, code: str):
        return sorted(set(self.listeners.get(code, {}).values()))

    def add(self, code: str, participant: str):
        queue = asyncio.Queue(maxsize=32)
        self.listeners[code][queue] = participant
        return queue

    def remove(self, code: str, queue: asyncio.Queue):
        listeners = self.listeners.get(code, {})
        participant = listeners.pop(queue, None)
        if not listeners:
            self.listeners.pop(code, None)
        return participant

    async def revoke(self, code: str, participant: str):
        for queue, owner in list(self.listeners.get(code, {}).items()):
            if owner == participant:
                self.remove(code, queue)
                while not queue.empty():
                    queue.get_nowait()
                queue.put_nowait(None)
        await self.publish(code, "participant_left", participant_id=participant, online_ids=self.online(code))

    async def publish(self, code: str, event: str, **data):
        message = {"event": event, **data}
        for queue in self.listeners.get(code, {}):
            if queue.full():
                queue.get_nowait()
            queue.put_nowait(message)


router = APIRouter()


def identify(db: Session, code: str, token: str):
    with db:
        room = get_room(db, code)
        participant = authenticate(db, room, token)
        return str(participant.id), room.expires_at.replace(tzinfo=timezone.utc)


@router.websocket("/ws/rooms/{code}")
async def stream(websocket: WebSocket, code: RoomCode, db: Session = Depends(get_db)):
    code = code.upper()
    origin = websocket.headers.get("origin")
    if origin and origin not in settings().cors_origins:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        message = await asyncio.wait_for(websocket.receive_text(), timeout=5)
        data = json.loads(message)
        token = data.get("token") if isinstance(data, dict) else None
        if not isinstance(token, str) or not 1 <= len(token) <= 128 or not token.isascii():
            await websocket.close(code=1008)
            return
        participant, expires_at = await run_in_threadpool(identify, db, code, token)
    except (ValueError, TimeoutError, HTTPException):
        await websocket.close(code=1008)
        return
    except WebSocketDisconnect:
        return

    hub: RoomHub = websocket.app.state.hub
    queue = hub.add(code, participant)

    async def send_events():
        while True:
            message = await queue.get()
            if message is None:
                return
            await websocket.send_json(message)

    async def read_messages():
        while True:
            await websocket.receive_text()

    sender = asyncio.create_task(send_events())
    receiver = asyncio.create_task(read_messages())
    try:
        await hub.publish(code, "presence_updated", online_ids=hub.online(code))
        await asyncio.wait(
            (sender, receiver), return_when=asyncio.FIRST_COMPLETED,
            timeout=max(0, (expires_at - now()).total_seconds()),
        )
    finally:
        for task in (sender, receiver):
            task.cancel()
            with suppress(asyncio.CancelledError, WebSocketDisconnect, RuntimeError, OSError):
                await task
        removed = hub.remove(code, queue)
        online = hub.online(code)
        if removed and participant not in online:
            await hub.publish(code, "participant_left", participant_id=participant, online_ids=online)
        with suppress(RuntimeError, WebSocketDisconnect):
            await websocket.close()
