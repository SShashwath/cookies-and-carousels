import httpx
import pytest
from fastapi import HTTPException

from app.api.schemas import Search
from app.services.places import FIELDS, GooglePlaces, MOCK_PLACES, discover


QUERY = Search(latitude=12.9716, longitude=77.5946, vegetarian_only=True)
GOOGLE_URL = "https://places.googleapis.com/v1/"
PHOTO = "places/example/photos/sample_reference"


def test_mock_catalog_has_thirty_distinct_restaurants_and_filters_diet():
    assert len({place.id for place in MOCK_PLACES.search(QUERY)}) >= 30
    assert all(place.vegetarian_only for place in discover(MOCK_PLACES, QUERY))


def test_google_nearby_requests_field_mask_parses_attribution_and_enforces_diet():
    def respond(request):
        assert request.headers["X-Goog-Api-Key"] == "test"
        assert request.url.path == "/v1/places:searchNearby"
        assert request.headers["X-Goog-FieldMask"] == ",".join(f"places.{field}" for field in FIELDS.split(","))
        assert b'"vegetarian_restaurant","vegan_restaurant"' in request.content
        fields = {
            "displayName": {"text": "Sample Live Venue"},
            "location": {"latitude": 12.97, "longitude": 77.59},
            "photos": [{"name": PHOTO, "authorAttributions": [{"displayName": "Photographer", "uri": "//maps.google.com/maps/contrib/123"}]}],
            "attributions": [{"provider": "Contributor"}],
        }
        return httpx.Response(200, json={"places": [
            {**fields, "id": "example", "types": ["vegetarian_restaurant"]},
            {**fields, "id": "other", "types": ["restaurant"], "servesVegetarianFood": True},
        ]})

    with httpx.Client(base_url=GOOGLE_URL, transport=httpx.MockTransport(respond)) as client:
        matches = discover(GooglePlaces("test", client), QUERY)
    assert [place.id for place in matches] == ["example"]
    assert matches[0].photo_url == f"/api/restaurants/photo/{PHOTO}"
    assert matches[0].photo_attributions[0].name == "Photographer"
    assert matches[0].photo_attributions[0].uri == "https://maps.google.com/maps/contrib/123"
    assert matches[0].attributions[0].name == "Contributor"
    assert not matches[0].cuisines and matches[0].min_price_per_person is None


def test_google_rate_limits_are_retryable():
    transport = httpx.MockTransport(lambda request: httpx.Response(429))
    with httpx.Client(base_url=GOOGLE_URL, transport=transport) as client:
        with pytest.raises(HTTPException) as failure:
            GooglePlaces("test", client).search(QUERY)
    assert failure.value.status_code == 503 and failure.value.headers["Retry-After"] == "30"
