#!/usr/bin/env python3
"""Read-only checks against a live store the maintainer owns and agreed to have checked.

Usage: python3 live_check.py <base-url> [--admin-path <path>] [--cafile <ca.pem>]

--cafile trusts an extra certificate authority, such as the mkcert CA of a local store.
Certificates are always verified.

Only GET requests, on a fixed list of paths, redirects not followed. Prints JSON with
status codes and whether a response looks like the real file; never response bodies.
"""

import hashlib
import json
import secrets
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT_SECONDS = 10
USER_AGENT = "store-security-check (read-only)"
# path -> text that proves the response is the real file, not a soft 404 page
PROBES = {
    ".git/HEAD": "ref:",
    ".git/config": "[core]",
    "app/etc/env.php": "<?php",
    "app/etc/config.php": "<?php",
    "composer.json": '"require"',
    "composer.lock": '"packages"',
    "auth.json": '"http-basic"',
    ".env": "=",
    "var/log/system.log": "main.",
    "var/log/exception.log": "main.",
    "phpinfo.php": "PHP Version",
    "info.php": "PHP Version",
    "adminer.php": "Adminer",
    "setup/": "Setup",
    "magento_version": "Magento/",
}
GUESSABLE_ADMIN_PATHS = ("admin", "backend")
ADMIN_LOGIN_MARKER = "login[username]"
SECURITY_HEADERS = ("strict-transport-security", "content-security-policy", "content-security-policy-report-only", "x-frame-options", "x-content-type-options")
DISCLOSING_HEADERS = ("server", "x-powered-by", "x-magento-cache-debug", "x-magento-tags", "x-magento-debug")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *arguments, **keywords):
        return None


CAFILE = sys.argv[sys.argv.index("--cafile") + 1] if "--cafile" in sys.argv else None
OPENER = urllib.request.build_opener(NoRedirect, urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=CAFILE)))
ERRORS: list[dict] = []


def fetch(url: str) -> tuple[int | None, dict, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with OPENER.open(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, {key.lower(): value for key, value in response.headers.items()}, response.read(65536).decode(errors="ignore")
    except urllib.error.HTTPError as error:
        return error.code, {key.lower(): value for key, value in error.headers.items()}, ""
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        ERRORS.append({"url_path": urllib.parse.urlparse(url).path, "error": str(getattr(error, "reason", error))})
        return None, {}, ""


def fingerprint(body: str) -> str:
    return hashlib.sha256(body.encode()).hexdigest()


def main() -> None:
    arguments = sys.argv[1:]
    if not arguments or arguments[0].startswith("-"):
        sys.exit("Usage: live_check.py <base-url> [--admin-path <path>] [--cafile <ca.pem>]")
    base = arguments[0].rstrip("/") + "/"
    admin_path = arguments[arguments.index("--admin-path") + 1] if "--admin-path" in arguments else None
    if urllib.parse.urlparse(base).scheme not in ("http", "https"):
        sys.exit("The base URL must start with http:// or https://")

    if fetch(base)[0] is None:
        print(json.dumps({"base_url": base, "reachable": False, "errors": ERRORS}, indent=2))
        sys.exit(1)

    soft_404_status, _, soft_404_body = fetch(base + f"store-security-{secrets.token_hex(6)}")
    soft_404 = fingerprint(soft_404_body) if soft_404_status == 200 else None

    exposed = []
    for path, marker in PROBES.items():
        status, _, body = fetch(base + path)
        if status == 200 and marker in body and fingerprint(body) != soft_404:
            exposed.append({"path": path, "status": status})

    admin = {}
    for path in [*GUESSABLE_ADMIN_PATHS, *([admin_path] if admin_path else [])]:
        status, headers, body = fetch(base + path.strip("/") + "/")
        admin[path if path in GUESSABLE_ADMIN_PATHS else "configured_admin_path"] = {
            "status": status,
            "login_form_public": status == 200 and ADMIN_LOGIN_MARKER in body,
            "redirects_to": headers.get("location") if status in (301, 302) else None,
        }

    status, headers, _ = fetch(base)
    plain_http = None
    if base.startswith("https://"):
        http_status, http_headers, _ = fetch("http://" + base[len("https://"):])
        plain_http = {"status": http_status, "redirects_to_https": (http_headers.get("location") or "").startswith("https://")}

    print(json.dumps({
        "base_url": base,
        "reachable": True,
        "homepage_status": status,
        "soft_404": soft_404 is not None,
        "exposed": exposed,
        "admin": admin,
        "security_headers": {name: headers.get(name) for name in SECURITY_HEADERS},
        "disclosing_headers": {name: headers[name] for name in DISCLOSING_HEADERS if name in headers},
        "plain_http": plain_http,
        "errors": ERRORS,
    }, indent=2))


if __name__ == "__main__":
    main()
