"""HTTP-level tests for the application.

These exist because a Starlette upgrade silently broke every server-rendered page:
`TemplateResponse(name, context)` was removed in favour of
`TemplateResponse(request, name, context)`, and the old form raised at request time
rather than at import. The unit tests all passed and the app imported cleanly, so
nothing caught it. Anything that renders a template or parses an upload needs a test
that actually issues a request.
"""

import io

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    import importlib
    import os

    # Force the zero-configuration backend into a throwaway directory.
    os.environ["DATABASE_TYPE"] = "sqlite"
    os.environ.setdefault("SECRET_KEY", "test_secret_key_used_only_by_the_test_suite")
    cwd = os.getcwd()
    os.chdir(cwd)  # templates and static are resolved relative to the repo root

    import app as app_module

    importlib.reload(app_module)
    with TestClient(app_module.app) as c:
        yield c


PUBLIC_PAGES = [
    "/",
    "/analyzer",
    "/csv-guide",
    "/dev-docs",
    "/admin/login",
    "/realtime",
]


@pytest.mark.parametrize("path", PUBLIC_PAGES)
def test_public_pages_render(client, path):
    """Every server-rendered page must return HTML, not a template error."""
    response = client.get(path)
    assert response.status_code == 200, response.text[:300]
    assert "text/html" in response.headers["content-type"]
    assert len(response.text) > 500, "page rendered but looks empty"


@pytest.mark.parametrize("path", ["/user/dashboard", "/budgets"])
def test_authenticated_pages_reject_anonymous_requests(client, path):
    response = client.get(path)
    assert response.status_code in (401, 403), response.text[:200]


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_csv_template_download(client):
    response = client.get("/api/csv-template")
    assert response.status_code == 200
    header = response.text.splitlines()[0]
    assert header == "model,prompt_tokens,completion_tokens,team"


def test_csv_upload_is_parsed_and_priced(client):
    """Covers the multipart path, which is handled by python-multipart."""
    csv = (
        "model,prompt_tokens,completion_tokens,team\n"
        "gpt-5,1000,1000,engineering\n"
        "claude-opus-5,1000,1000,data_science\n"
    )
    response = client.post(
        "/analyze",
        files={"file": ("usage.csv", io.BytesIO(csv.encode()), "text/csv")},
    )
    assert response.status_code == 200, response.text[:300]

    body = response.json()
    assert body["total_requests"] == 2
    # gpt-5 at $1.25/$10 per 1M plus claude-opus-5 at $5/$25 per 1M, over 1K tokens
    # each, is $0.04125 exactly. The endpoint rounds to four decimal places.
    assert body["total_cost"] == pytest.approx(0.0413, abs=5e-5)
    assert not body["unknown_models"]


def test_upload_rejects_a_non_csv_content_type(client):
    response = client.post(
        "/analyze",
        files={"file": ("payload.exe", io.BytesIO(b"MZ\x90\x00"), "application/x-msdownload")},
    )
    assert response.status_code >= 400


def test_openapi_schema_is_served(client):
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["paths"]
