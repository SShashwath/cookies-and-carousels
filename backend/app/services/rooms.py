import secrets
from collections import Counter
from datetime import timedelta, timezone
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.algorithms.matching import Candidate, rank_matches
from app.api.schemas import (
    CastVote, CreateRoom, Deck, MatchView, ParticipantView, RestaurantView, Results, RoomView, Search,
)
from app.core.config import settings
from app.core.security import digest, new_token
from app.db.models import Match, Participant, Restaurant, Room, RoomRestaurant, Vote, now
from app.services.places import budget_gap, discover, provider_for

ROOM_ALPHABET = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def get_room(db: Session, code: str, lock: bool = False) -> Room:
    query = select(Room).where(Room.room_code == code.upper())
    room = db.scalar(query.with_for_update() if lock else query)
    if room is None:
        raise HTTPException(404, "This room couldn’t be found. Check the invite link.")
    if room.expires_at.replace(tzinfo=timezone.utc) <= now():
        raise HTTPException(410, "This room has expired. Create a new room to keep swiping.")
    return room


def authenticate(db: Session, room: Room, token: str | None, *, host: bool = False) -> Participant:
    participant = db.scalar(select(Participant).where(
        Participant.room_id == room.id, Participant.guest_token_hash == digest(token or ""),
        Participant.left_at.is_(None),
    ))
    if participant is None:
        raise HTTPException(401, "Your guest session has ended. Reopen your invite to join again.")
    if host and participant.id != room.host_participant_id:
        raise HTTPException(403, "Only the host can do that.")
    return participant


def prefs(room: Room) -> Search:
    return Search.model_validate(room, from_attributes=True)


def active_participants(db: Session, room: Room):
    return list(db.scalars(select(Participant).where(
        Participant.room_id == room.id, Participant.left_at.is_(None),
    ).order_by(Participant.joined_at, Participant.id)))


def pool(db: Session, room: Room) -> list[Restaurant]:
    return list(db.scalars(select(Restaurant).join(RoomRestaurant).where(
        RoomRestaurant.room_id == room.id,
    ).order_by(RoomRestaurant.display_order)))


def room_view(db: Session, room: Room, participant: Participant | None) -> RoomView:
    counts = dict(db.execute(select(Vote.participant_id, func.count()).where(
        Vote.room_id == room.id,
    ).group_by(Vote.participant_id)).all())
    participants = [
        ParticipantView(
            id=p.id, display_name=p.display_name, is_host=p.id == room.host_participant_id,
            completed_swiping=p.completed_swiping, vote_count=counts.get(p.id, 0),
        )
        for p in active_participants(db, room)
    ]
    return RoomView(
        room_code=room.room_code, status=room.status, location_name=room.location_name,
        preferences=prefs(room) if participant else None, round_number=room.round_number,
        expires_at=room.expires_at.replace(tzinfo=timezone.utc),
        restaurant_count=db.scalar(select(func.count()).select_from(RoomRestaurant).where(
            RoomRestaurant.room_id == room.id,
        )) or 0,
        participants=participants,
        me=next((p for p in participants if participant and p.id == participant.id), None),
    )


def add_participant(db: Session, room: Room, name: str, participant_id: UUID | None = None):
    token = new_token()
    participant = Participant(
        id=participant_id or uuid4(), room_id=room.id, display_name=name,
        name_key=name.casefold(), guest_token_hash=digest(token),
    )
    db.add(participant)
    db.flush()
    return participant, token


def replace_pool(db: Session, room: Room, places: list[RestaurantView]):
    if not places:
        raise HTTPException(422, "No restaurants match these filters. Try a wider radius or more cuisines.")
    insert = postgres_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    keys = {f"{p.source}:{p.id}": p for p in places}
    for key, place in sorted(keys.items()):
        metadata = {}
        if place.source == "mock":
            metadata = dict(name=place.name, cuisines=place.cuisines, rating=place.rating, photo_reference=place.photo_url)
        db.execute(insert(Restaurant).values(
            provider_id=key, source=place.source, **metadata,
            google_place_id=place.id if place.source == "google" else None,
        ).on_conflict_do_nothing(index_elements=["provider_id"]))
    records = {r.provider_id: r.id for r in db.scalars(select(Restaurant).where(Restaurant.provider_id.in_(keys)))}
    db.execute(delete(RoomRestaurant).where(RoomRestaurant.room_id == room.id))
    db.add_all([
        RoomRestaurant(room_id=room.id, restaurant_id=records[key], display_order=position)
        for position, key in enumerate(keys)
    ])
    db.flush()


def create_room(db: Session, data: CreateRoom):
    places = discover(provider_for(settings().restaurant_provider), data)
    for _ in range(5):
        try:
            with db.begin_nested():
                room = Room(
                    **data.model_dump(exclude={"display_name"}),
                    room_code="".join(secrets.choice(ROOM_ALPHABET) for _ in range(6)),
                    host_participant_id=uuid4(),
                    expires_at=now() + timedelta(hours=settings().room_ttl_hours),
                )
                db.add(room)
                db.flush()
        except IntegrityError as error:
            if "room_code" not in str(error.orig):
                raise
            continue
        participant, token = add_participant(db, room, data.display_name, room.host_participant_id)
        replace_pool(db, room, places)
        return room, participant, token
    raise HTTPException(503, "A room code couldn’t be reserved. Try again.")


def join_room(db: Session, room: Room, name: str):
    if room.status != "lobby":
        raise HTTPException(409, "This round has already started. You can join in the next lobby.")
    if len(active_participants(db, room)) >= 30:
        raise HTTPException(409, "This room has reached its guest limit.")
    name_taken = db.scalar(select(Participant).where(
        Participant.room_id == room.id, Participant.name_key == name.casefold(),
    ))
    if name_taken:
        if name_taken.left_at is None:
            raise HTTPException(409, "That name is already taken in this room.")
        db.delete(name_taken)
        db.flush()
    return add_participant(db, room, name)


def check_round(room: Room, number: int):
    if room.round_number != number:
        raise HTTPException(409, "This round has changed. Reload the room and try again.")


def hydrate(restaurants: list[Restaurant], query: Search) -> dict[UUID, RestaurantView]:
    hydrated = {}
    for source in {r.source for r in restaurants}:
        records = {r.provider_id.split(":", 1)[1]: r.id for r in restaurants if r.source == source}
        details = provider_for(source).details(list(records), query)
        for provider_id, restaurant_id in records.items():
            place = details.get(provider_id)
            eligible = place and place.available and (not query.vegetarian_only or place.vegetarian_only)
            hydrated[restaurant_id] = place.model_copy(update={"id": str(restaurant_id)}) if eligible else RestaurantView(
                id=str(restaurant_id), name="Restaurant unavailable", source=source, available=False,
            )
    return hydrated


def deck(db: Session, room: Room, participant: Participant) -> Deck:
    if room.status == "lobby":
        raise HTTPException(409, "The host hasn’t started the round yet.")
    restaurants = pool(db, room)
    votes = list(db.scalars(select(Vote.restaurant_id).where(
        Vote.room_id == room.id, Vote.participant_id == participant.id,
    )))
    # Release the room lock before waiting for live restaurant metadata.
    db.commit()
    hydrated = hydrate(restaurants, prefs(room))
    return Deck(
        round_number=room.round_number, restaurants=[hydrated[r.id] for r in restaurants],
        voted_ids=[str(restaurant_id) for restaurant_id in votes],
    )


def record_vote(db: Session, room: Room, participant: Participant, data: CastVote) -> bool:
    previous = db.scalar(select(Vote).where(
        Vote.room_id == room.id, Vote.participant_id == participant.id, Vote.restaurant_id == data.restaurant_id,
    ))
    if previous and previous.vote == data.vote:
        return False
    if previous:
        raise HTTPException(409, "A vote has already been saved for that restaurant.")
    if room.status != "swiping" or participant.completed_swiping:
        raise HTTPException(409, "Voting is closed for this round.")
    if not db.get(RoomRestaurant, (room.id, data.restaurant_id)):
        raise HTTPException(404, "That restaurant isn’t in this round.")
    db.add(Vote(room_id=room.id, participant_id=participant.id, restaurant_id=data.restaurant_id, vote=data.vote))
    db.flush()
    return True


def mark_complete(db: Session, room: Room, participant: Participant):
    if participant.completed_swiping:
        return False
    if room.status != "swiping":
        raise HTTPException(409, "Voting is closed for this round.")
    count = db.scalar(select(func.count()).select_from(Vote).where(
        Vote.room_id == room.id, Vote.participant_id == participant.id,
    ))
    if count != len(pool(db, room)):
        raise HTTPException(409, "Swipe on the remaining cards first.")
    participant.completed_swiping = True
    db.flush()
    return True


def finish_round(db: Session, room: Room, force: bool = False) -> bool:
    if room.status == "finished":
        return False
    if room.status != "swiping":
        if force:
            raise HTTPException(409, "Start the round before finishing it.")
        return False
    participants = active_participants(db, room)
    if not force and not all(p.completed_swiping for p in participants):
        return False

    restaurant_votes = Counter(db.execute(select(Vote.restaurant_id, Vote.vote).where(
        Vote.room_id == room.id, Vote.participant_id.in_([p.id for p in participants]),
    )).all())
    restaurants = [r for r in pool(db, room) if restaurant_votes[r.id, "like"]]
    preferences = prefs(room)
    places = hydrate(restaurants, preferences)
    candidates = [
        Candidate(
            str(r.id), restaurant_votes[r.id, "like"], restaurant_votes[r.id, "dislike"],
            places[r.id].distance_km if places[r.id].distance_km is not None else float("inf"),
            budget_gap(places[r.id], preferences), eligible=places[r.id].available,
        )
        for r in restaurants
    ]
    for index, match in enumerate(rank_matches(candidates, len(participants)), start=1):
        db.add(Match(
            room_id=room.id, restaurant_id=UUID(match.restaurant_id), rank=index,
            match_score=match.participant_like_percent, like_count=match.like_count, dislike_count=match.dislike_count,
            participant_count=match.participant_count, unanimous=match.unanimous,
        ))
    room.status = "finished"
    db.flush()
    return True


def results(db: Session, room: Room) -> Results:
    if room.status != "finished":
        raise HTTPException(409, "Results will be available when the round ends.")
    rows = db.execute(select(Match, Restaurant).join(Restaurant, Match.restaurant_id == Restaurant.id).where(
        Match.room_id == room.id,
    ).order_by(Match.rank)).all()
    db.commit()
    places = hydrate([restaurant for _, restaurant in rows], prefs(room))
    return Results(round_number=room.round_number, matches=[
        MatchView(
            rank=rank, restaurant=places[match.restaurant_id], approval_percent=round(100 * match.like_count / (match.like_count + match.dislike_count), 2),
            participant_like_percent=match.match_score,
            like_count=match.like_count, dislike_count=match.dislike_count,
            participant_count=match.participant_count, unanimous=match.unanimous,
        )
        for rank, match in enumerate(
            (match for match, _ in rows if places[match.restaurant_id].available), start=1,
        )
    ])


def restart(db: Session, room: Room):
    if room.status != "finished":
        raise HTTPException(409, "Finish the current round first.")
    previous = {r.provider_id.split(":", 1)[1] for r in pool(db, room)}
    provider = provider_for(settings().restaurant_provider)
    replace_pool(db, room, discover(provider, prefs(room), previous))
    db.execute(update(Participant).where(Participant.room_id == room.id).values(completed_swiping=False))
    room.round_number += 1
    room.status = "lobby"
    db.flush()
