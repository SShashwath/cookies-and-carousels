import math
import re
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from typing import Protocol, get_args
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import HTTPException

from app.api.schemas import Attribution, Cuisine, RestaurantView, Search
from app.core.config import settings
from app.services.mock_places import SAMPLES

POOL_LIMIT = 10
GOOGLE_BASE = "https://places.googleapis.com/v1/"
FIELDS = (
    "id,displayName,formattedAddress,location,types,rating,priceLevel,priceRange,"
    "googleMapsUri,photos,attributions,businessStatus"
)
PHOTO_NAME = re.compile(r"places/[\w-]{1,300}/photos/[\w-]{1,2000}", re.ASCII)

CUISINE_TYPES = {
    "indian_restaurant": "Indian", "chinese_restaurant": "Chinese",
    "italian_restaurant": "Italian", "asian_restaurant": "Asian",
    "cafe": "Cafe", "coffee_shop": "Cafe", "pizza_restaurant": "Pizza",
}
MOCK_CUISINES = list(get_args(Cuisine))
GOOGLE_CUISINES = [item for item in MOCK_CUISINES if item in CUISINE_TYPES.values()]
PRICE_LEVELS = {
    "PRICE_LEVEL_FREE": "Free", "PRICE_LEVEL_INEXPENSIVE": "Inexpensive",
    "PRICE_LEVEL_MODERATE": "Moderate", "PRICE_LEVEL_EXPENSIVE": "Expensive",
    "PRICE_LEVEL_VERY_EXPENSIVE": "Very expensive",
}


class PlacesProvider(Protocol):
    def search(self, query: Search) -> list[RestaurantView]: ...
    def details(self, ids: list[str], query: Search) -> dict[str, RestaurantView]: ...


def budget_gap(place: RestaurantView, query: Search) -> float:
    lower, upper = place.min_price_per_person, place.max_price_per_person
    if lower is None and upper is None:
        return math.inf
    return max(0, (lower or 0) - query.max_budget, query.min_budget - (upper if upper is not None else math.inf))


def discover(provider: PlacesProvider, query: Search, avoid: set[str] | None = None):
    eligible = [
        place for place in provider.search(query)
        if place.available
        and (not query.vegetarian_only or place.vegetarian_only)
        and (place.distance_km is not None and place.distance_km <= query.radius_km)
        and (not query.cuisine_preferences or set(place.cuisines).intersection(query.cuisine_preferences))
        and budget_gap(place, query) in (0, math.inf)
    ]
    excluded = avoid or set()
    return sorted(eligible, key=lambda p: (
        p.id in excluded, budget_gap(p, query), p.distance_km, -(p.rating or 0), p.id,
    ))[:POOL_LIMIT]


def distance(lat: float, lng: float, query: Search) -> float:
    a = math.sin(math.radians(lat - query.latitude) / 2) ** 2
    a += math.cos(math.radians(lat)) * math.cos(math.radians(query.latitude)) * (
        math.sin(math.radians(lng - query.longitude) / 2) ** 2
    )
    return 12742 * math.asin(math.sqrt(min(1, a)))


class MockPlaces:
    def search(self, query: Search) -> list[RestaurantView]:
        places = []
        for index, sample in enumerate(SAMPLES):
            cuisines = [sample.cuisine]
            if sample.cuisine in {"North Indian", "South Indian", "Biryani"}:
                cuisines.append("Indian")
            if sample.cuisine == "Pizza":
                cuisines.append("Italian")
            offset = 0.24 + (index // 9) * 0.31 + (index % 9) * 0.025
            coords = f"{max(-90, query.latitude - offset / 111):.6f},{query.longitude:.6f}"
            maps_url = "https://www.google.com/maps/search/?" + urlencode({"api": 1, "query": coords})
            places.append(RestaurantView(
                id=f"mock-{index + 1}", source="mock", name=sample.name,
                cuisines=cuisines, rating=sample.rating,
                min_price_per_person=sample.price, max_price_per_person=sample.price,
                distance_km=round(offset, 2), photo_url=f"/food/{sample.photo}.jpg",
                maps_url=maps_url, vegetarian_only=sample.vegetarian,
            ))
        return places

    def details(self, ids: list[str], query: Search) -> dict[str, RestaurantView]:
        wanted = set(ids)
        return {place.id: place for place in self.search(query) if place.id in wanted}


def safe_https(value: str | None) -> str | None:
    if not value:
        return None
    url = "https:" + value if value.startswith("//") else value
    parsed = urlparse(url)
    return url if parsed.scheme == "https" and parsed.hostname else None


def money(value: dict) -> int | None:
    if value.get("currencyCode") == "INR":
        return int(value.get("units", 0))
    return None


def decode_place(raw: dict, query: Search) -> RestaurantView:
    location = raw.get("location")
    kilometres = distance(location["latitude"], location["longitude"], query) if location else None
    types = set(raw.get("types", []))
    photos = raw.get("photos", [])
    photo = photos[0] if photos else {}
    reference = photo.get("name", "")
    prices = raw.get("priceRange", {})
    name = raw.get("displayName", {}).get("text")
    maps_url = safe_https(raw.get("googleMapsUri"))
    if not maps_url and name:
        maps_url = "https://www.google.com/maps/search/?" + urlencode({
            "api": 1, "query": name, "query_place_id": raw["id"],
        })
    return RestaurantView(
        id=raw["id"], source="google", name=name or "Restaurant details unavailable",
        address=raw.get("formattedAddress"), cuisines=sorted({CUISINE_TYPES[t] for t in types if t in CUISINE_TYPES}),
        rating=raw.get("rating"), price_level=PRICE_LEVELS.get(raw.get("priceLevel")),
        min_price_per_person=money(prices.get("startPrice", {})),
        max_price_per_person=money(prices.get("endPrice", {})),
        distance_km=kilometres,
        photo_url=f"/api/restaurants/photo/{reference}" if PHOTO_NAME.fullmatch(reference) else None,
        photo_attributions=[
            Attribution(name=author["displayName"], uri=safe_https(author.get("uri")))
            for author in photo.get("authorAttributions", []) if author.get("displayName")
        ],
        attributions=[
            Attribution(name=entry["provider"], uri=safe_https(entry.get("providerUri")))
            for entry in raw.get("attributions", []) if entry.get("provider")
        ],
        maps_url=maps_url,
        vegetarian_only="vegetarian_restaurant" in types or "vegan_restaurant" in types,
        available=raw.get("businessStatus", "OPERATIONAL") == "OPERATIONAL",
    )


class GooglePlaces:
    def __init__(self, api_key: str, client: httpx.Client | None = None):
        self.api_key = api_key
        self.client = client or httpx.Client(timeout=6)

    def request(self, method: str, path: str, fields: str = "", **kwargs):
        if not self.api_key:
            raise HTTPException(503, "Live restaurant search is currently unavailable.")
        try:
            headers = {"X-Goog-Api-Key": self.api_key}
            if fields:
                headers["X-Goog-FieldMask"] = fields
            response = self.client.request(method, GOOGLE_BASE + path, headers=headers, **kwargs)
            if response.status_code == 404:
                return None
            if response.status_code == 429:
                raise HTTPException(503, "Restaurant search is busy. Try again in a moment.", headers={"Retry-After": "30"})
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError):
            raise HTTPException(502, "Restaurant details couldn't be loaded. Please try again.") from None

    def search(self, query: Search) -> list[RestaurantView]:
        location = {"latitude": query.latitude, "longitude": query.longitude}
        if query.vegetarian_only:
            types = ["vegetarian_restaurant", "vegan_restaurant"]
        else:
            types = [key for key, cuisine in CUISINE_TYPES.items() if cuisine in query.cuisine_preferences]
            types = types or ["restaurant"]
        data = self.request("POST", "places:searchNearby", ",".join(f"places.{f}" for f in FIELDS.split(",")), json={
            "includedTypes": types,
            "maxResultCount": 20,
            "rankPreference": "DISTANCE",
            "regionCode": "IN",
            "locationRestriction": {"circle": {"center": location, "radius": query.radius_km * 1000}},
        })
        return [decode_place(item, query) for item in (data or {}).get("places", [])]

    def details(self, ids: list[str], query: Search) -> dict[str, RestaurantView]:
        def fetch(place_id: str):
            raw = self.request("GET", f"places/{place_id}", FIELDS, params={"regionCode": "IN"})
            return decode_place(raw, query) if raw else None

        if not ids:
            return {}
        with ThreadPoolExecutor(max_workers=5) as executor:
            return {place.id: place for place in executor.map(fetch, ids) if place}

    def photo(self, reference: str):
        if not PHOTO_NAME.fullmatch(reference):
            raise HTTPException(404, "Photo unavailable.")
        result = self.request("GET", f"{reference}/media", params={"maxWidthPx": 960, "skipHttpRedirect": "true"})
        url = safe_https((result or {}).get("photoUri"))
        hostname = urlparse(url).hostname if url else None
        if not hostname or not (hostname == "googleusercontent.com" or hostname.endswith(".googleusercontent.com")):
            raise HTTPException(404, "Photo unavailable.")
        return url


@lru_cache
def google_places():
    return GooglePlaces(settings().google_places_api_key)


MOCK_PLACES = MockPlaces()


def provider_for(source: str) -> PlacesProvider:
    return google_places() if source == "google" else MOCK_PLACES
