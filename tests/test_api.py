from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

import src.app as app_module


INITIAL_ACTIVITIES = deepcopy(app_module.activities)


@pytest.fixture(autouse=True)
def reset_activities():
    app_module.activities = deepcopy(INITIAL_ACTIVITIES)
    yield
    app_module.activities = deepcopy(INITIAL_ACTIVITIES)


@pytest.fixture
def client():
    return TestClient(app_module.app)


def test_root_redirects_to_static_index(client):
    # Arrange

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities_returns_data_and_no_store_cache_header(client):
    # Arrange

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert "Chess Club" in response.json()


def test_signup_adds_normalized_participant_to_activity(client):
    # Arrange
    activity_name = "Chess Club"
    email = "  NewStudent@Mergington.edu  "

    # Act
    response = client.post(f"/activities/{activity_name}/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json() == {
        "message": "Signed up newstudent@mergington.edu for Chess Club"
    }
    assert "newstudent@mergington.edu" in app_module.activities[activity_name]["participants"]


def test_signup_rejects_duplicate_participant(client):
    # Arrange
    activity_name = "Chess Club"
    email = "MICHAEL@MERGINGTON.EDU"
    original_participants = list(app_module.activities[activity_name]["participants"])

    # Act
    response = client.post(f"/activities/{activity_name}/signup", params={"email": email})

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "Student already signed up"}
    assert app_module.activities[activity_name]["participants"] == original_participants


def test_signup_rejects_unknown_activity(client):
    # Arrange
    activity_name = "Robotics Club"

    # Act
    response = client.post(f"/activities/{activity_name}/signup", params={"email": "student@mergington.edu"})

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_signup_rejects_full_activity(client):
    # Arrange
    activity_name = "Chess Club"
    max_participants = app_module.activities[activity_name]["max_participants"]
    app_module.activities[activity_name]["participants"] = [
        f"student{index}@mergington.edu" for index in range(max_participants)
    ]

    # Act
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": "latecomer@mergington.edu"},
    )

    # Assert
    assert response.status_code == 400
    assert response.json() == {"detail": "Activity is full"}
    assert len(app_module.activities[activity_name]["participants"]) == max_participants


def test_signup_increases_participant_count_by_one(client):
    # Arrange
    activity_name = "Programming Class"
    before_count = len(app_module.activities[activity_name]["participants"])

    # Act
    response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": "newcoder@mergington.edu"},
    )

    # Assert
    after_count = len(app_module.activities[activity_name]["participants"])
    assert response.status_code == 200
    assert after_count == before_count + 1


def test_signup_is_visible_in_activities_response(client):
    # Arrange
    activity_name = "Art Studio"
    email = "artist@mergington.edu"

    # Act
    signup_response = client.post(
        f"/activities/{activity_name}/signup",
        params={"email": email},
    )
    activities_response = client.get("/activities")

    # Assert
    assert signup_response.status_code == 200
    assert activities_response.status_code == 200
    assert email in activities_response.json()[activity_name]["participants"]


def test_unregister_removes_existing_participant(client):
    # Arrange
    activity_name = "Basketball Team"
    email = "james@mergington.edu"

    # Act
    response = client.delete(
        f"/activities/{activity_name}/participants",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": "Removed james@mergington.edu from Basketball Team"}
    assert email not in app_module.activities[activity_name]["participants"]


def test_unregister_rejects_unknown_activity(client):
    # Arrange
    activity_name = "Robotics Club"

    # Act
    response = client.delete(
        f"/activities/{activity_name}/participants",
        params={"email": "student@mergington.edu"},
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Activity not found"}


def test_unregister_rejects_participant_not_registered(client):
    # Arrange
    activity_name = "Art Studio"
    email = "nobody@mergington.edu"
    original_participants = list(app_module.activities[activity_name]["participants"])

    # Act
    response = client.delete(
        f"/activities/{activity_name}/participants",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 404
    assert response.json() == {"detail": "Student is not registered for this activity"}
    assert app_module.activities[activity_name]["participants"] == original_participants


def test_unregister_decreases_participant_count_by_one(client):
    # Arrange
    activity_name = "Debate Club"
    email = "ryan@mergington.edu"
    before_count = len(app_module.activities[activity_name]["participants"])

    # Act
    response = client.delete(
        f"/activities/{activity_name}/participants",
        params={"email": email},
    )

    # Assert
    after_count = len(app_module.activities[activity_name]["participants"])
    assert response.status_code == 200
    assert after_count == before_count - 1


def test_unregister_normalizes_email_before_removing(client):
    # Arrange
    activity_name = "Chess Club"
    email = "  DANIEL@MERGINGTON.EDU  "

    # Act
    response = client.delete(
        f"/activities/{activity_name}/participants",
        params={"email": email},
    )

    # Assert
    assert response.status_code == 200
    assert "daniel@mergington.edu" not in app_module.activities[activity_name]["participants"]