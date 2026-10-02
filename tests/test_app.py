# Unit tests for the payment service HTTP layer. The database is stubbed so the
# suite runs in CI without a live PostgreSQL instance.

import pytest

import app as payment_app


@pytest.fixture
def client():
    payment_app.app.config["TESTING"] = True
    with payment_app.app.test_client() as test_client:
        yield test_client


class _FakeCursor:
    def execute(self, *_args, **_kwargs):
        return None

    def fetchone(self):
        return (3,)

    def close(self):
        return None


class _FakeConn:
    def cursor(self):
        return _FakeCursor()

    def close(self):
        return None


def test_health_returns_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_root_reports_db_connected(client, monkeypatch):
    monkeypatch.setattr(payment_app, "get_conn", lambda: _FakeConn())

    response = client.get("/")
    body = response.get_json()

    assert response.status_code == 200
    assert body["service"] == "payment"
    assert body["status"] == "success"
    assert body["db"] == "connected"
    assert body["transactions"] == 3


def test_root_reports_error_when_db_unreachable(client, monkeypatch):
    def _boom():
        raise RuntimeError("connection refused")

    monkeypatch.setattr(payment_app, "get_conn", _boom)

    response = client.get("/")
    body = response.get_json()

    assert response.status_code == 500
    assert body["status"] == "error"
    assert body["db"] == "unreachable"
    assert "connection refused" in body["error"]
