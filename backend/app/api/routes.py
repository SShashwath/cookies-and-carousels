import re
from typing import Annotated

from anyio import from_thread
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.schemas import (
    CastVote, CreateRoom, Deck, GuestSession, Join, RestaurantView, Results, RoomCode, RoomView,
    RoundAction, Search,
)
from app.core.config import settings
from app.core.security import client_ip, read_bearer
from app.db.models import now
from app.db.session import get_db
from app.services import rooms
from app.services.places import (
    GOOGLE_CUISINES, MOCK_CUISINES, POOL_LIMIT, discover, google_places, provider_for,
)

router = APIRouter(prefix="/api")
DB = Annotated[Session, Depends(get_db)]


def credentials(authorization: Annotated[str | None, Header()] = None):
    return read_bearer(authorization)


Token = Annotated[str | None, Depends(credentials)]


def commit_room(db, request, room, participant, events=()):
    view = rooms.room_view(db, room, participant)
    db.commit()
    for event in events:
        from_thread.run(request.app.state.hub.publish, room.room_code, event)
    return view


FINAL_EVENTS = ("room_finished", "results_ready")


@router.get("/health")
def health(db: DB):
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(503, "Database unavailable.") from None
    return {"status": "ok"}


@router.get("/restaurants/cuisines")
def cuisines() -> list[str]:
    return GOOGLE_CUISINES if settings().restaurant_provider == "google" else MOCK_CUISINES


@router.get("/restaurants/nearby")
def nearby(request: Request, query: Annotated[Search, Query()]) -> list[RestaurantView]:
    request.app.state.limits.check("nearby", client_ip(request), 45)
    return discover(provider_for(settings().restaurant_provider), query)


@router.get("/restaurants/selection")
def selection(
    request: Request, query: Annotated[Search, Query()],
    ids: Annotated[str, Header(alias="X-Restaurant-Ids", max_length=3100)],
) -> list[RestaurantView]:
    request.app.state.limits.check("selection", client_ip(request), 45)
    ordered = list(dict.fromkeys(ids.split(",")))
    if len(ordered) > POOL_LIMIT or any(not re.fullmatch(r"[A-Za-z0-9_-]{1,300}", item) for item in ordered):
        raise HTTPException(422, "This saved selection couldn’t be loaded.")
    source = settings().restaurant_provider
    details = provider_for(source).details(ordered, query)
    return [
        details[item] if item in details and details[item].available
        and (not query.vegetarian_only or details[item].vegetarian_only)
        else RestaurantView(id=item, source=source, name="Restaurant unavailable", available=False)
        for item in ordered
    ]


@router.get("/restaurants/photo/{reference:path}")
def photo(request: Request, reference: str):
    if settings().restaurant_provider != "google":
        raise HTTPException(404, "Photo unavailable.")
    request.app.state.limits.check("photos", client_ip(request), 120)
    return RedirectResponse(google_places().photo(reference), headers={"Cache-Control": "no-store"})


@router.post("/rooms", status_code=201)
def create(request: Request, data: CreateRoom, db: DB) -> GuestSession:
    request.app.state.limits.check("create", client_ip(request), 12)
    room, participant, token = rooms.create_room(db, data)
    return GuestSession(token=token, room=commit_room(db, request, room, participant))


@router.get("/rooms/{code}")
def read(code: RoomCode, db: DB, token: Token) -> RoomView:
    room = rooms.get_room(db, code, lock=True)
    participant = rooms.authenticate(db, room, token) if token is not None else None
    return rooms.room_view(db, room, participant)


@router.post("/rooms/{code}/join", status_code=201)
def join(code: RoomCode, request: Request, data: Join, db: DB, token: Token) -> GuestSession:
    request.app.state.limits.check("join", client_ip(request), 30)
    room = rooms.get_room(db, code, lock=True)
    if token is not None:
        participant = rooms.authenticate(db, room, token)
        return GuestSession(token=token, room=rooms.room_view(db, room, participant))
    participant, token = rooms.join_room(db, room, data.display_name)
    return GuestSession(token=token, room=commit_room(db, request, room, participant, ("participant_joined",)))


def mutation(db, code, token, number, *, host=False):
    room = rooms.get_room(db, code, lock=True)
    participant = rooms.authenticate(db, room, token, host=host)
    rooms.check_round(room, number)
    return room, participant


@router.post("/rooms/{code}/start")
def start(code: RoomCode, data: RoundAction, db: DB, token: Token, request: Request) -> RoomView:
    room, participant = mutation(db, code, token, data.round_number, host=True)
    if room.status == "swiping":
        return rooms.room_view(db, room, participant)
    if room.status != "lobby":
        raise HTTPException(409, "This round has already finished.")
    room.status = "swiping"
    return commit_room(db, request, room, participant, ("room_started",))


@router.get("/rooms/{code}/restaurants")
def restaurants(code: RoomCode, db: DB, token: Token) -> Deck:
    room = rooms.get_room(db, code, lock=True)
    return rooms.deck(db, room, rooms.authenticate(db, room, token))


@router.post("/rooms/{code}/votes")
def vote(code: RoomCode, data: CastVote, db: DB, token: Token, request: Request) -> RoomView:
    request.app.state.limits.check("vote-ip", client_ip(request), 600)
    room, participant = mutation(db, code, token, data.round_number)
    request.app.state.limits.check("vote", str(participant.id), 60)
    changed = rooms.record_vote(db, room, participant, data)
    return commit_room(db, request, room, participant, ("vote_progress_updated",) if changed else ())


@router.post("/rooms/{code}/complete")
def complete(code: RoomCode, data: RoundAction, db: DB, token: Token, request: Request) -> RoomView:
    room, participant = mutation(db, code, token, data.round_number)
    events = ("participant_completed",) if rooms.mark_complete(db, room, participant) else ()
    if rooms.finish_round(db, room):
        events += FINAL_EVENTS
    return commit_room(db, request, room, participant, events)


@router.post("/rooms/{code}/finish")
def finish(code: RoomCode, data: RoundAction, db: DB, token: Token, request: Request) -> RoomView:
    room, participant = mutation(db, code, token, data.round_number, host=True)
    changed = rooms.finish_round(db, room, force=True)
    return commit_room(db, request, room, participant, FINAL_EVENTS if changed else ())


@router.post("/rooms/{code}/leave")
def leave(code: RoomCode, data: RoundAction, db: DB, token: Token, request: Request) -> RoomView:
    room, participant = mutation(db, code, token, data.round_number)
    if participant.id == room.host_participant_id:
        raise HTTPException(409, "The host can close voting or return later with the same session.")
    participant.left_at = now()
    db.flush()
    events = FINAL_EVENTS if rooms.finish_round(db, room) else ()
    view = commit_room(db, request, room, None)
    hub = request.app.state.hub
    from_thread.run(hub.revoke, room.room_code, str(participant.id))
    for event in events:
        from_thread.run(hub.publish, room.room_code, event)
    return view


@router.get("/rooms/{code}/results")
def results(code: RoomCode, db: DB, token: Token) -> Results:
    room = rooms.get_room(db, code, lock=True)
    rooms.authenticate(db, room, token)
    return rooms.results(db, room)


@router.post("/rooms/{code}/rounds")
def another_round(code: RoomCode, data: RoundAction, db: DB, token: Token, request: Request) -> RoomView:
    room, participant = mutation(db, code, token, data.round_number, host=True)
    rooms.restart(db, room)
    return commit_room(db, request, room, participant, ("round_created",))
