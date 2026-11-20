from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import Participant, Room, Vote, now


PREFS = {"latitude": 12.9716, "longitude": 77.5946, "location_name": "Bengaluru", "display_name": "Host"}


def create(client, **prefs):
    response = client.post("/api/rooms", json={**PREFS, **prefs})
    assert response.status_code == 201, response.text
    body = response.json()
    return f"/api/rooms/{body['room']['room_code']}", headers(body["token"])


def headers(token):
    return {"Authorization": f"Bearer {token}"}


def join(client, path, name):
    response = client.post(f"{path}/join", json={"display_name": name})
    assert response.status_code == 201, response.text
    return headers(response.json()["token"])


ROUND = {"round_number": 1}


def begin(client, path, host):
    assert client.post(f"{path}/start", json=ROUND, headers=host).status_code == 200
    return client.get(f"{path}/restaurants", headers=host).json()["restaurants"]


def vote(client, path, auth, restaurant, choice):
    return client.post(f"{path}/votes", json={**ROUND, "restaurant_id": restaurant, "vote": choice}, headers=auth)


def test_room_authentication_and_expiration(client, session):
    path, host = create(client)
    assert client.get(path).json()["me"] is None
    assert client.get(path, headers=headers("invalid")).status_code == 401
    room = client.get(path, headers=host).json()
    assert room["me"]["is_host"]
    assert room["restaurant_count"] > 0
    with session() as db:
        participant = db.scalar(select(Participant))
        assert participant.guest_token_hash != host["Authorization"].split()[1]
        db.scalar(select(Room)).expires_at = now()
        db.commit()
    assert client.get(path).status_code == 410
    assert client.post(f"{path}/start", json=ROUND, headers=host).status_code == 410


def test_join_names_and_host_permissions(client):
    path, host = create(client)
    guest = join(client, path, "Sam")
    assert client.post(f"{path}/join", json={"display_name": "sAM "}).status_code == 409
    assert client.post(f"{path}/start", json=ROUND, headers=guest).status_code == 403
    begin(client, path, host)
    assert client.post(f"{path}/join", json={"display_name": "Late"}).status_code == 409
    assert client.post(f"{path}/finish", json=ROUND, headers=guest).status_code == 403


def test_votes_refresh_and_early_finish(client, session):
    path, host = create(client)
    guest = join(client, path, "Anika")
    first = begin(client, path, host)[0]["id"]
    assert client.get(f"{path}/results", headers=guest).status_code == 409
    assert vote(client, path, host, str(uuid4()), "like").status_code == 404
    assert vote(client, path, headers("wrong"), first, "like").status_code == 401
    assert vote(client, path, host, first, "like").status_code == 200
    assert vote(client, path, host, first, "like").status_code == 200
    assert vote(client, path, host, first, "dislike").status_code == 409
    with session() as db:
        assert len(list(db.scalars(select(Vote)))) == 1
    assert client.get(f"{path}/restaurants", headers=host).json()["voted_ids"] == [first]
    assert client.get(f"{path}/restaurants", headers=guest).json()["voted_ids"] == []
    assert client.post(f"{path}/complete", headers=host, json=ROUND).status_code == 409
    assert client.post(f"{path}/finish", headers=host, json=ROUND).status_code == 200
    match = client.get(f"{path}/results", headers=guest).json()["matches"][0]
    assert (match["like_count"], match["dislike_count"], match["participant_like_percent"]) == (1, 0, 50)
    assert match["approval_percent"] == 100 and not match["unanimous"]


def test_four_guests_complete_and_host_restarts(client):
    path, host = create(client, vegetarian_only=True)
    guests = [host] + [join(client, path, name) for name in ("Anika", "Veda", "Arun")]
    deck = begin(client, path, host)
    assert all(restaurant["vegetarian_only"] for restaurant in deck)
    for index, auth in enumerate(guests):
        assert client.get(f"{path}/restaurants", headers=auth).json()["restaurants"] == deck
        for card_no, restaurant in enumerate(deck):
            choice = "like" if card_no == 0 or (card_no == 1 and index == 0) else "dislike"
            assert vote(client, path, auth, restaurant["id"], choice).status_code == 200
        result = client.post(f"{path}/complete", headers=auth, json=ROUND)
        assert result.status_code == 200
        assert result.json()["status"] == ("finished" if index == 3 else "swiping")
    results = client.get(f"{path}/results", headers=host).json()["matches"]
    assert results[0]["unanimous"] and results[0]["like_count"] == 4
    assert not results[1]["unanimous"] and results[1]["participant_like_percent"] == 25
    next_round = client.post(f"{path}/rounds", headers=host, json=ROUND)
    assert next_round.status_code == 200
    assert next_round.json()["round_number"] == 2
    assert all(p["vote_count"] == 0 for p in next_round.json()["participants"])
    assert client.post(f"{path}/start", headers=host, json=ROUND).status_code == 409


def test_disconnected_participant_can_leave_round(client):
    path, host = create(client)
    guest = join(client, path, "Anika")
    deck = begin(client, path, host)
    for card in deck:
        vote(client, path, host, card["id"], "dislike")
    assert client.post(f"{path}/complete", headers=host, json=ROUND).json()["status"] == "swiping"
    assert client.post(f"{path}/leave", headers=guest, json=ROUND).status_code == 200
    assert client.get(path, headers=host).json()["status"] == "finished"
    assert client.get(f"{path}/results", headers=host).json()["matches"] == []


def test_realtime_room_events_reconnect_and_no_ballot_leak(client):
    path, host = create(client)
    code = path.rsplit("/", 1)[1]
    socket_path = f"/ws/rooms/{code}"
    with client.websocket_connect(socket_path) as socket:
        socket.send_json({"token": host["Authorization"].split()[1]})
        assert socket.receive_json()["event"] == "presence_updated"
        guest = join(client, path, "Veda")
        assert socket.receive_json() == {"event": "participant_joined"}
        restaurant = begin(client, path, host)[0]["id"]
        assert socket.receive_json() == {"event": "room_started"}

        with client.websocket_connect(socket_path) as guest_socket:
            guest_socket.send_json({"token": guest["Authorization"].split()[1]})
            assert guest_socket.receive_json()["event"] == "presence_updated"
            assert socket.receive_json()["event"] == "presence_updated"
            assert vote(client, path, guest, restaurant, "like").status_code == 200
            assert guest_socket.receive_json() == {"event": "vote_progress_updated"}
            assert socket.receive_json() == {"event": "vote_progress_updated"}

        assert socket.receive_json()["event"] == "participant_left"
        assert client.get(f"{path}/restaurants", headers=guest).json()["voted_ids"] == [restaurant]
        assert client.post(f"{path}/finish", headers=host, json=ROUND).status_code == 200
        assert socket.receive_json() == {"event": "room_finished"}
        assert socket.receive_json() == {"event": "results_ready"}


def test_simultaneous_votes_on_postgres(client, session):
    from concurrent.futures import ThreadPoolExecutor

    if session.kw["bind"].dialect.name != "postgresql":
        pytest.skip("Row-lock behavior is specific to PostgreSQL.")
    path, host = create(client)
    guest = join(client, path, "Anika")
    restaurant = begin(client, path, host)[0]["id"]

    with ThreadPoolExecutor(max_workers=4) as executor:
        responses = list(executor.map(
            lambda auth: vote(client, path, auth, restaurant, "like"),
            [host, guest, host, guest],
        ))
    assert [response.status_code for response in responses] == [200] * 4
    with session() as db:
        assert len(list(db.scalars(select(Vote)))) == 2


def test_empty_search_and_request_validation(client):
    assert client.post("/api/rooms", json={**PREFS, "display_name": "Invalid\0name"}).status_code == 422
    assert client.post("/api/rooms", json={**PREFS, "location_name": "Invalid\0place"}).status_code == 422
    assert client.post("/api/rooms", json={**PREFS, "min_budget": 1000, "max_budget": 100}).status_code == 422
    assert client.post("/api/rooms", json={**PREFS, "max_budget": 100}).status_code == 422
    response = client.get("/api/restaurants/nearby", params={
        "latitude": 12.9716, "longitude": 77.5946, "vegetarian_only": "true",
        "cuisine_preferences": "South Indian",
    })
    assert response.status_code == 200
    assert response.json() and all(place["vegetarian_only"] for place in response.json())
    assert all("South Indian" in place["cuisines"] for place in response.json())


def test_explicit_leave_revokes_existing_socket_access(client):
    from starlette.websockets import WebSocketDisconnect

    path, host = create(client)
    guest = join(client, path, "Veda")
    socket_path = "/ws/rooms/" + path.rsplit("/", 1)[1]

    with client.websocket_connect(socket_path) as socket:
        socket.send_json({"token": guest["Authorization"].split()[1]})
        assert socket.receive_json()["event"] == "presence_updated"
        assert client.post(f"{path}/leave", headers=guest, json=ROUND).status_code == 200
        with pytest.raises(WebSocketDisconnect):
            socket.receive_json()
    assert client.get(path, headers=guest).status_code == 401
    assert client.get(path, headers=host).json()["participants"][0]["display_name"] == "Host"


def test_lobby_capacity_counts_current_guests(client, session):
    path, _host = create(client)
    from app.core.security import digest

    with session() as db:
        room_id = db.scalar(select(Room.id))
        db.add_all([
            Participant(room_id=room_id, display_name=f"Former {index}", name_key=f"former {index}",
                        guest_token_hash=digest(str(index)), left_at=now())
            for index in range(30)
        ])
        db.commit()
    join(client, path, "New guest")
