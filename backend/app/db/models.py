from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON, Boolean, CheckConstraint, DateTime, Float, ForeignKey,
    ForeignKeyConstraint, Integer, String, UniqueConstraint, Uuid,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (
        CheckConstraint("status IN ('lobby', 'swiping', 'finished')", name="ck_room_status"),
        CheckConstraint("min_budget >= 0 AND max_budget >= min_budget", name="ck_room_budget"),
        ForeignKeyConstraint(
            ["id", "host_participant_id"], ["participants.room_id", "participants.id"],
            name="fk_room_host", use_alter=True, ondelete="NO ACTION",
            deferrable=True, initially="DEFERRED",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    room_code: Mapped[str] = mapped_column(String(6), unique=True)
    host_participant_id: Mapped[UUID] = mapped_column(Uuid)
    status: Mapped[str] = mapped_column(String(12), default="lobby")
    location_name: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[float] = mapped_column(Float)
    min_budget: Mapped[int] = mapped_column(Integer)
    max_budget: Mapped[int] = mapped_column(Integer)
    cuisine_preferences: Mapped[list[str]] = mapped_column(JSON)
    vegetarian_only: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    round_number: Mapped[int] = mapped_column(Integer, default=1)


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("room_id", "id", name="uq_participant_room_id"),
        UniqueConstraint("room_id", "name_key", name="uq_participant_room_name"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    room_id: Mapped[UUID] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    display_name: Mapped[str] = mapped_column(String(40))
    name_key: Mapped[str] = mapped_column(String(120))
    guest_token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_swiping: Mapped[bool] = mapped_column(Boolean, default=False)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Restaurant(Base):
    __tablename__ = "restaurants"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    source: Mapped[str] = mapped_column(String(12))
    provider_id: Mapped[str] = mapped_column(String(300), unique=True)
    google_place_id: Mapped[str | None] = mapped_column(String(300), unique=True)
    name: Mapped[str | None] = mapped_column(String(240))
    address: Mapped[str | None] = mapped_column(String(300))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    cuisines: Mapped[list[str] | None] = mapped_column(JSON)
    rating: Mapped[float | None] = mapped_column(Float)
    price_level: Mapped[str | None] = mapped_column(String(40))
    photo_reference: Mapped[str | None] = mapped_column(String(300))
    maps_url: Mapped[str | None] = mapped_column(String(500))


class RoomRestaurant(Base):
    __tablename__ = "room_restaurants"
    __table_args__ = (UniqueConstraint("room_id", "display_order", name="uq_pool_order"),)

    room_id: Mapped[UUID] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True)
    restaurant_id: Mapped[UUID] = mapped_column(ForeignKey("restaurants.id"), primary_key=True)
    display_order: Mapped[int] = mapped_column(Integer)


class Vote(Base):
    __tablename__ = "votes"
    __table_args__ = (
        ForeignKeyConstraint(
            ["room_id", "participant_id"], ["participants.room_id", "participants.id"], ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["room_id", "restaurant_id"], ["room_restaurants.room_id", "room_restaurants.restaurant_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("room_id", "participant_id", "restaurant_id", name="uq_room_vote"),
        CheckConstraint("vote IN ('like', 'dislike')", name="ck_vote_choice"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    room_id: Mapped[UUID] = mapped_column(Uuid)
    participant_id: Mapped[UUID] = mapped_column(Uuid)
    restaurant_id: Mapped[UUID] = mapped_column(Uuid)
    vote: Mapped[str] = mapped_column(String(7))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (
        ForeignKeyConstraint(
            ["room_id", "restaurant_id"], ["room_restaurants.room_id", "room_restaurants.restaurant_id"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("room_id", "restaurant_id", name="uq_room_match"),
        UniqueConstraint("room_id", "rank", name="uq_match_rank"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    room_id: Mapped[UUID] = mapped_column(Uuid)
    restaurant_id: Mapped[UUID] = mapped_column(Uuid)
    match_score: Mapped[float] = mapped_column(Float)
    like_count: Mapped[int] = mapped_column(Integer)
    dislike_count: Mapped[int] = mapped_column(Integer)
    participant_count: Mapped[int] = mapped_column(Integer)
    unanimous: Mapped[bool] = mapped_column(Boolean)
    rank: Mapped[int] = mapped_column(Integer)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
