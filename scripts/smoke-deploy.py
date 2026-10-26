#!/usr/bin/env python3
"""Smoke-test a deployed coffee-nut through its public origin.

Walks the product story against a live stack: the SPA and its client-side
fallback, admin static files, then register -> refresh by cookie -> coffee ->
bag -> brew -> share -> read the share anonymously. It creates a throwaway
account each run, named smoke+<random>@example.com.

    ./scripts/smoke-deploy.py https://coffee.508.dev

To test a stack with no TLS proxy in front, such as compose.prod.yml run
locally, pass the headers the proxy would have added:

    ./scripts/smoke-deploy.py http://127.0.0.1:18080 --host coffee.localtest

Stdlib only, so it runs with any python3.
"""

import argparse
import json
import secrets
import sys
import urllib.error
import urllib.request
from http.cookies import SimpleCookie


class Smoke:
    def __init__(self, base: str, host: str | None) -> None:
        self.base = base.rstrip("/")
        self.headers = {"Host": host, "X-Forwarded-Proto": "https"} if host else {}
        self.access: str | None = None
        self.refresh_cookie: str | None = None

    def request(
        self, method: str, path: str, body: dict | None = None, auth: bool = True
    ) -> tuple[int, dict[str, str], bytes]:
        headers = dict(self.headers)
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if auth and self.access:
            headers["Authorization"] = f"Bearer {self.access}"
        if self.refresh_cookie:
            headers["Cookie"] = self.refresh_cookie
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as response:
                return response.status, dict(response.headers), response.read()
        except urllib.error.HTTPError as error:
            return error.code, dict(error.headers), error.read()

    def json(self, method: str, path: str, body: dict | None = None, expect: int = 200) -> dict:
        status, headers, raw = self.request(method, path, body)
        if status != expect:
            fail(f"{method} {path}: expected {expect}, got {status}: {raw[:300]!r}")
        set_cookie = headers.get("Set-Cookie")
        if set_cookie:
            self.check_refresh_cookie(set_cookie)
        return json.loads(raw) if raw else {}

    def check_refresh_cookie(self, header: str) -> None:
        cookie = SimpleCookie()
        cookie.load(header)
        for name, morsel in cookie.items():
            if not morsel["httponly"] or not morsel["secure"]:
                fail(f"refresh cookie {name} is not HttpOnly and Secure: {header}")
            self.refresh_cookie = f"{name}={morsel.value}"


def fail(message: str) -> None:
    print(f"FAIL  {message}")
    sys.exit(1)


def ok(message: str) -> None:
    print(f"ok    {message}")


def main() -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    parser.add_argument("base_url")
    parser.add_argument("--host", help="Host header to send, when bypassing the TLS proxy")
    args = parser.parse_args()
    s = Smoke(args.base_url, args.host)

    for path, kind in [
        ("/", "text/html"),
        ("/s/not-a-real-token", "text/html"),
        ("/static/admin/css/base.css", "text/css"),
        ("/health/", "application/json"),
    ]:
        status, headers, _ = s.request("GET", path, auth=False)
        if status != 200 or kind not in headers.get("Content-Type", ""):
            fail(f"GET {path}: {status} {headers.get('Content-Type')}")
        ok(f"GET {path}")

    email = f"smoke+{secrets.token_hex(4)}@example.com"
    tokens = s.json(
        "POST",
        "/api/v1/auth/register/",
        {"email": email, "password": secrets.token_urlsafe(16)},
        expect=201,
    )
    s.access = tokens["access"]
    ok(f"register {email}")

    if not s.refresh_cookie:
        fail("register did not set the refresh cookie")
    s.access = s.json("POST", "/api/v1/auth/token/refresh/")["access"]
    ok("refresh via HttpOnly cookie")

    ethiopia = s.json("GET", "/api/v1/countries/?q=ethiopia")["results"][0]
    pour_over = s.json("GET", "/api/v1/brew-methods/?q=pour%20over")["results"][0]
    ok("catalog is seeded")

    roaster = s.json("POST", "/api/v1/roasters/", {"name": "Smoke Roasters"}, expect=201)
    coffee = s.json(
        "POST",
        "/api/v1/coffees/",
        {"name": "Smoke Test", "roaster": roaster["id"], "country": ethiopia["id"]},
        expect=201,
    )
    bag = s.json(
        "POST",
        "/api/v1/bags/",
        {"coffee": coffee["id"], "weight_grams": "250.0"},
        expect=201,
    )
    brew = s.json(
        "POST",
        "/api/v1/brews/",
        {
            "bag": bag["id"],
            "method": pour_over["id"],
            "dose_grams": "14.0",
            "water_grams": "170.0",
            "liked": True,
        },
        expect=201,
    )
    ok("coffee, bag, and brew created")

    share = s.json("POST", f"/api/v1/brews/{brew['id']}/share/", {})
    s.access = None
    s.refresh_cookie = None
    public = s.json("GET", f"/api/v1/public/brews/{share['share_token']}/")
    if "dose_grams" not in json.dumps(public):
        fail(f"public brew looks wrong: {public}")
    ok(f"share link readable anonymously: {share['share_url']}")


if __name__ == "__main__":
    main()
