"""Browser-level checks for the server-rendered pages.

Every defect these cover shipped to production unnoticed, because nothing in the test
suite had ever loaded a page in a browser:

  - the analyzer's option cards overflowed a phone screen by 420px
  - the CSV guide's navbar and the developer docs' tables did the same
  - the Content Security Policy blocked every analytics beacon and the syntax
    highlighter, so both features were silently dead
  - the hero referenced an image that had been deleted

Skipped automatically when Playwright or its browser binary is unavailable, so a plain
`pytest` run still works without the extra dependency.
"""

import socket
import subprocess
import sys
import time

import pytest

pytest.importorskip("playwright", reason="playwright is not installed")
from playwright.sync_api import sync_playwright  # noqa: E402

PUBLIC_PAGES = ["/", "/analyzer", "/csv-guide", "/dev-docs", "/admin/login", "/realtime"]
MOBILE = {"width": 390, "height": 844}
DESKTOP = {"width": 1440, "height": 900}


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """Run the real application; TestClient does not execute CSP or layout."""
    port = _free_port()
    workdir = tmp_path_factory.mktemp("run")
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin",
        "SECRET_KEY": "test_secret_key_used_only_by_the_test_suite",
        "DATABASE_TYPE": "sqlite",
        "BASE_URL": f"http://127.0.0.1:{port}",
        "HOME": str(workdir),
    }
    import os

    env["PATH"] = os.environ.get("PATH", env["PATH"])
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--port", str(port), "--log-level", "warning"],
        env={**os.environ, **env},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    base = f"http://127.0.0.1:{port}"
    for _ in range(120):
        try:
            import urllib.request

            urllib.request.urlopen(base + "/health", timeout=2)
            break
        except Exception:
            time.sleep(0.5)
    else:
        proc.terminate()
        pytest.fail("application did not become healthy")

    yield base
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(headless=True)
        except Exception as exc:  # browser binary not installed
            pytest.skip(f"chromium unavailable: {exc}")
        yield b
        b.close()


def _load(browser, base, path, viewport):
    ctx = browser.new_context(viewport=viewport)
    page = ctx.new_page()
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(base + path, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(800)
    return ctx, page, errors


@pytest.mark.parametrize("path", PUBLIC_PAGES)
def test_no_horizontal_overflow_on_mobile(browser, server, path):
    """The document must never scroll sideways on a phone-width viewport."""
    ctx, page, _ = _load(browser, server, path, MOBILE)
    overflow = page.evaluate(
        "() => Math.max(0, document.documentElement.scrollWidth - window.innerWidth)"
    )
    ctx.close()
    assert overflow <= 2, f"{path} overflows its viewport by {overflow}px"


@pytest.mark.parametrize("path", PUBLIC_PAGES)
def test_no_content_security_policy_violations(browser, server, path):
    """A CSP that blocks a resource the page needs is a silent outage."""
    ctx, page, errors = _load(browser, server, path, DESKTOP)
    ctx.close()
    blocked = [e for e in errors if "Content Security Policy" in e]
    assert not blocked, f"{path} has CSP violations:\n" + "\n".join(blocked)


def test_hero_demo_and_social_image_are_served(browser, server):
    """Both assets have been broken by a repository change before."""
    ctx = browser.new_context(viewport=DESKTOP)
    page = ctx.new_page()
    statuses = {}
    for asset in [
        "/static/media/demo.mp4",
        "/static/media/demo.webm",
        "/static/media/demo-poster.jpg",
        "/static/assets/og-image.jpg",
    ]:
        statuses[asset] = page.request.get(server + asset).status
    ctx.close()
    broken = {a: s for a, s in statuses.items() if s != 200}
    assert not broken, f"assets not served: {broken}"


def test_social_preview_uses_absolute_urls(browser, server):
    """Scrapers ignore relative og:image paths, which renders no preview at all."""
    ctx = browser.new_context(viewport=DESKTOP)
    page = ctx.new_page()
    page.goto(server + "/", wait_until="domcontentloaded", timeout=60000)
    image = page.get_attribute('meta[property="og:image"]', "content")
    url = page.get_attribute('meta[property="og:url"]', "content")
    ctx.close()
    assert image and image.startswith("http"), f"og:image is not absolute: {image!r}"
    assert url and url.startswith("http"), f"og:url is not absolute: {url!r}"


AXE_URL = "https://cdn.jsdelivr.net/npm/axe-core@4.10.2/axe.min.js"


@pytest.fixture(scope="module")
def axe_source():
    """axe-core is fetched once; skip rather than fail when offline."""
    import urllib.error
    import urllib.request

    try:
        return urllib.request.urlopen(AXE_URL, timeout=60).read().decode()
    except (urllib.error.URLError, TimeoutError) as exc:
        pytest.skip(f"axe-core unavailable: {exc}")


@pytest.mark.parametrize("path", PUBLIC_PAGES)
@pytest.mark.parametrize("viewport", [DESKTOP, MOBILE], ids=["desktop", "mobile"])
def test_wcag_21_aa(browser, server, axe_source, path, viewport):
    """No WCAG 2.1 A or AA violations on any public page, at either width.

    The site previously had 33 contrast failures and several scrollable regions that
    could not be reached from the keyboard.
    """
    ctx, page, _ = _load(browser, server, path, viewport)
    page.add_script_tag(content=axe_source)
    violations = page.evaluate(
        """async () => {
            const r = await axe.run(document, {
                runOnly: {type: 'tag', values: ['wcag2a','wcag2aa','wcag21a','wcag21aa']}
            });
            return r.violations.map(v => ({
                id: v.id,
                impact: v.impact,
                count: v.nodes.length,
                sample: (v.nodes[0] || {}).html
            }));
        }"""
    )
    ctx.close()

    if violations:
        detail = "\n".join(
            f"  {v['id']} ({v['impact']}) x{v['count']}: {v['sample']}" for v in violations
        )
        pytest.fail(f"{path} has accessibility violations:\n{detail}")
