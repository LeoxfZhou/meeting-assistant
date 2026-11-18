from uuid import uuid4


def authenticate(client, email=None, password="test-only-password-123"):
    email = email or f"user-{uuid4().hex}@example.com"
    response = client.post("/auth/register", json={"email": email, "display_name": "Test user", "password": password})
    assert response.status_code == 201
    token = client.post("/auth/login", json={"email": email, "password": password})
    assert token.status_code == 200
    client.headers["Authorization"] = "Bearer " + token.json()["access_token"]
    return response.json()
