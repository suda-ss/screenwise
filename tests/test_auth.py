import uuid

from fastapi.testclient import TestClient

from backend.main import app
from backend.schemas import RegisterInput


def registration_payload(label: str) -> dict:
    suffix = uuid.uuid4().hex[:10]
    return {
        "name": f"{label} Owner",
        "email": f"{label.lower()}-{suffix}@example.com",
        "password": "correct-horse-battery-staple",
        "company_name": f"{label} Company",
        "company_slug": f"{label.lower()}-{suffix}",
    }


def test_company_registration_login_and_tenant_isolation():
    first_payload = registration_payload("Alpha")
    second_payload = registration_payload("Beta")
    with TestClient(app) as first, TestClient(app) as second:
        first_registration = first.post("/auth/register", json=first_payload)
        assert first_registration.status_code == 201
        first_org = first_registration.json()["organizations"][0]
        assert first_org["name"] == "Alpha Company"
        assert first.get("/auth/me").status_code == 200
        second_company = first.post(
            "/organizations", json={"name": "Another Company", "slug": f"another-{uuid.uuid4().hex[:8]}"}
        )
        assert second_company.status_code == 409

        second_registration = second.post("/auth/register", json=second_payload)
        assert second_registration.status_code == 201
        assert second.get(f"/organizations/{first_org['id']}/jobs").status_code == 403

        assert first.post("/auth/logout").status_code == 204
        assert first.get("/auth/me").status_code == 401
        login = first.post(
            "/auth/login",
            json={"email": first_payload["email"], "password": first_payload["password"]},
        )
        assert login.status_code == 200
        assert login.json()["organizations"][0]["id"] == first_org["id"]


def test_company_url_is_normalized_and_short_names_are_valid():
    payload = registration_payload("A")
    payload["company_slug"] = " A! "
    parsed = RegisterInput.model_validate(payload)
    assert parsed.company_slug == "a"
