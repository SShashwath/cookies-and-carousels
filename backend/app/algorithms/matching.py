from dataclasses import dataclass
from fractions import Fraction
from math import inf


@dataclass(frozen=True)
class Candidate:
    restaurant_id: str
    likes: int
    dislikes: int
    distance_km: float = inf
    budget_gap: float = inf
    eligible: bool = True


@dataclass(frozen=True)
class RankedMatch:
    restaurant_id: str
    like_count: int
    dislike_count: int
    participant_count: int
    approval_percent: float
    participant_like_percent: float
    unanimous: bool


def rank_matches(candidates: list[Candidate], participant_count: int) -> list[RankedMatch]:
    if participant_count < 1:
        return []

    def approval(candidate: Candidate) -> Fraction:
        return Fraction(candidate.likes, candidate.likes + candidate.dislikes)

    ordered = sorted(
        (c for c in candidates if c.eligible and c.likes > 0),
        key=lambda c: (-c.likes, -approval(c), c.budget_gap, c.distance_km, c.restaurant_id),
    )
    return [
        RankedMatch(
            c.restaurant_id, c.likes, c.dislikes, participant_count,
            round(float(approval(c) * 100), 2),
            round(100 * c.likes / participant_count, 2),
            c.likes == participant_count,
        )
        for c in ordered
    ]
