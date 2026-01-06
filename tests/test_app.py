import sys
import os
import pytest
import uuid

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import app, init_db

TEST_DB = "test_todo.db"

# -------------------------
# TEST CLIENT FIXTURE
# -------------------------
@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["DATABASE"] = TEST_DB

    # Create fresh test DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    init_db()

    with app.test_client() as client:
        yield client

    # Cleanup
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


# -------------------------
# HELPER FUNCTIONS
# -------------------------
def register(client, username, password):
    return client.post(
        "/register",
        data={
            "username": username,
            "password": password
        },
        follow_redirects=True
    )


def login(client, username, password):
    return client.post(
        "/login",
        data={
            "username": username,
            "password": password
        },
        follow_redirects=True
    )


def logout(client):
    return client.get("/logout", follow_redirects=True)


# -------------------------
# BASIC APP TEST
# -------------------------
def test_app_starts(client):
    response = client.get("/login")
    assert response.status_code == 200


# -------------------------
# AUTHENTICATION TESTS
# -------------------------
def test_user_registration(client):
    username = f"user_{uuid.uuid4().hex[:6]}"
    response = register(client, username, "testpass")
    assert b"Registered successfully" in response.data


def test_user_login(client):
    username = f"user_{uuid.uuid4().hex[:6]}"
    register(client, username, "testpass")

    response = login(client, username, "testpass")
    assert response.status_code == 200
    assert b"My Tasks" in response.data


def test_user_logout(client):
    username = f"user_{uuid.uuid4().hex[:6]}"
    register(client, username, "testpass")
    login(client, username, "testpass")

    response = logout(client)
    assert b"Login" in response.data


# -------------------------
# TASK FUNCTIONALITY TESTS
# -------------------------
def test_add_task(client):
    username = f"user_{uuid.uuid4().hex[:6]}"
    register(client, username, "testpass")
    login(client, username, "testpass")

    response = client.post(
        "/add",
        data={
            "title": "Test Task",
            "priority": "High"
        },
        follow_redirects=True
    )

    assert b"Test Task" in response.data


def test_delete_task(client):
    username = f"user_{uuid.uuid4().hex[:6]}"
    register(client, username, "testpass")
    login(client, username, "testpass")

    client.post(
        "/add",
        data={"title": "Delete Me"},
        follow_redirects=True
    )

    from app import get_db
    conn = get_db()
    task = conn.execute(
        "SELECT id FROM tasks WHERE title='Delete Me'"
    ).fetchone()
    conn.close()

    response = client.get(f"/delete/{task['id']}", follow_redirects=True)
    assert b"Delete Me" not in response.data


# -------------------------
# DASHBOARD & ANALYTICS TESTS
# -------------------------
def test_dashboard_access(client):
    username = f"user_{uuid.uuid4().hex[:6]}"
    register(client, username, "testpass")
    login(client, username, "testpass")

    response = client.get("/dashboard")
    assert response.status_code == 200


def test_analytics_access(client):
    username = f"user_{uuid.uuid4().hex[:6]}"
    register(client, username, "testpass")
    login(client, username, "testpass")

    response = client.get("/analytics")
    assert response.status_code == 200
