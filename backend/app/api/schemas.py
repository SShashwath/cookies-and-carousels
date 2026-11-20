from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Cuisine = Literal["Indian", "North Indian", "South Indian", "Chinese", "Italian", "Asian", "Cafe", "Biryani", "Pizza"]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40, pattern=r"^[^\x00]+$")]
RoomCode = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9]{6}$")]


class Search(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    radius_km: float = Field(default=5, ge=0.5, le=30)
    min_budget: int = Field(default=0, ge=0, le=10000)
    max_budget: int = Field(default=1000, ge=100, le=20000)
    cuisine_preferences: list[Cuisine] = Field(default_factory=list, max_length=9)
    vegetarian_only: bool = False

    @model_validator(mode="after")
    def valid_budget(self):
        if self.min_budget > self.max_budget:
            raise ValueError("Minimum budget must be less than or equal to maximum budget.")
        return self


class Join(BaseModel):
    display_name: Name


class CreateRoom(Search, Join):
    location_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100, pattern=r"^[^\x00]+$")]


class RoundAction(BaseModel):
    round_number: int = Field(ge=1)


class CastVote(RoundAction):
    restaurant_id: UUID
    vote: Literal["like", "dislike"]


class ParticipantView(BaseModel):
    id: UUID
    display_name: str
    is_host: bool
    completed_swiping: bool
    vote_count: int


class RoomView(BaseModel):
    room_code: str
    status: Literal["lobby", "swiping", "finished"]
    location_name: str
    preferences: Search | None
    round_number: int
    expires_at: datetime
    restaurant_count: int
    participants: list[ParticipantView]
    me: ParticipantView | None


class GuestSession(BaseModel):
    token: str
    room: RoomView


class Attribution(BaseModel):
    name: str
    uri: str | None = None


class RestaurantView(BaseModel):
    id: str
    source: Literal["mock", "google"]
    name: str
    address: str | None = None
    cuisines: list[str] = Field(default_factory=list)
    rating: float | None = None
    price_level: str | None = None
    min_price_per_person: int | None = None
    max_price_per_person: int | None = None
    distance_km: float | None = None
    photo_url: str | None = None
    photo_attributions: list[Attribution] = Field(default_factory=list)
    attributions: list[Attribution] = Field(default_factory=list)
    maps_url: str | None = None
    vegetarian_only: bool = False
    available: bool = True


class Deck(BaseModel):
    round_number: int
    restaurants: list[RestaurantView]
    voted_ids: list[str]


class MatchView(BaseModel):
    rank: int
    restaurant: RestaurantView
    approval_percent: float
    participant_like_percent: float
    like_count: int
    dislike_count: int
    participant_count: int
    unanimous: bool


class Results(BaseModel):
    round_number: int
    matches: list[MatchView]
