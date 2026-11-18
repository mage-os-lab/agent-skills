#!/usr/bin/env python3
"""Collect offline security signals about a Magento 2 / Mage-OS store for the store-security audit.

Usage: python3 audit.py <store-root>

Prints JSON. Never prints a secret: env.php and git history are reported as facts
("crypt key committed in a1b2c3d"), not values. Every finding is a lead to verify.
"""

import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

SCORECARD_FILE = Path("var") / "mage-os-security.json"
PRODUCT_PACKAGES = (
    "mage-os/product-community-edition", "magento/product-community-edition",
    "mage-os/magento2-base", "magento/magento2-base",
)
GUESSABLE_ADMIN_PATHS = {"admin", "backend", "admin_1", "adminhtml", "magento", "manager", "administrator"}
PUB_PHP_FILES = {"index.php", "get.php", "static.php", "health_check.php", "cron.php"}
SENSITIVE_PATHS = ["app/etc/env.php", "auth.json", ".env", "var/", "generated/", "pub/media/", "pub/static/"]
NEVER_TRACKED = re.compile(r"(^|/)(app/etc/env\.php|auth\.json|\.env|[^/]+\.(sql|sql\.gz|pem|key)|id_(rsa|ed25519))$")
# Patterns for git log -G: they only select commits, the matched text is never printed
SECRET_PATTERNS = {
    "magento_crypt_key": r"'key'\s*=>\s*'[0-9a-zA-Z:_]{32,}",
    "db_password": r"'password'\s*=>\s*'[^']{4,}'",
    "repo_magento_auth": r"\"username\"\s*:\s*\"[0-9a-f]{32}\"",
    "private_key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "aws_access_key": r"AKIA[0-9A-Z]{16}",
    "stripe_live_key": r"sk_live_[0-9a-zA-Z]{20,}",
    "github_token": r"gh[pousr]_[0-9A-Za-z]{36}",
}
OBFUSCATION = re.compile(r"eval\s*\(\s*(base64_decode|gzinflate|gzuncompress|str_rot13)|assert\s*\(\s*\$_(GET|POST|REQUEST|COOKIE)|\$_(GET|POST|REQUEST|COOKIE)\s*\[[^]]*\]\s*\(")
GIT_TIMEOUT_SECONDS = 120


def git(root: Path, *arguments: str) -> str | None:
    try:
        result = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, text=True, timeout=GIT_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def read_version(root: Path) -> dict:
    lock = root / "composer.lock"
    if not lock.exists():
        return {"composer_lock": False}
    packages = {package["name"]: package for package in json.loads(lock.read_text()).get("packages", [])}
    composer = root / "composer.json"
    direct = set(json.loads(composer.read_text()).get("require", {})) if composer.exists() else set()
    product = next((name for name in PRODUCT_PACKAGES if name in packages), None)
    return {
        "composer_lock": True,
        "distribution": "mage-os" if (product or "").startswith("mage-os/") else "magento" if product else None,
        "product_package": product,
        "version": packages[product]["version"].lstrip("v") if product else None,
        "quality_patches_installed": "magento/quality-patches" in packages,
        "composer_patches_installed": "cweagans/composer-patches" in packages,
        # Abandoned packages the core pulls in are the core's problem: only direct requirements are the store's
        "abandoned_direct_requirements": sorted(name for name, package in packages.items() if package.get("abandoned") and name in direct),
        "abandoned_through_core_or_extensions": len([name for name, package in packages.items() if package.get("abandoned") and name not in direct]),
        "package_count": len(packages),
    }


def read_composer_patches(root: Path) -> dict:
    composer = root / "composer.json"
    if not composer.exists():
        return {}
    extra = json.loads(composer.read_text()).get("extra", {})
    patches = extra.get("patches", {})
    patches_file = extra.get("patches-file")
    if patches_file and (root / patches_file).exists():
        patches = json.loads((root / patches_file).read_text()).get("patches", patches)
    return {package: list(entries) if isinstance(entries, dict) else entries for package, entries in patches.items()}


def list_app_code_modules(root: Path) -> list[str]:
    base = root / "app" / "code"
    return sorted(f"{vendor.name}_{module.name}" for vendor in base.iterdir() if vendor.is_dir() for module in vendor.iterdir() if module.is_dir()) if base.is_dir() else []


def php_string(source: str, key: str) -> str | None:
    match = re.search(rf"'{re.escape(key)}'\s*=>\s*'([^']*)'", source)
    return match.group(1) if match else None


def read_env(root: Path) -> dict:
    """Facts about env.php, never its secret values."""
    env = root / "app" / "etc" / "env.php"
    if not env.exists():
        return {"present": False}
    source = env.read_text(errors="ignore")
    front_name = php_string(source, "frontName")
    return {
        "present": True,
        "mage_mode": php_string(source, "MAGE_MODE"),
        "admin_path_guessable": (front_name or "admin").lower() in GUESSABLE_ADMIN_PATHS,
        "admin_path_length": len(front_name) if front_name else None,
        "x_frame_options": php_string(source, "x-frame-options"),
        "has_crypt_key": "'crypt'" in source,
    }


def read_enabled_modules(root: Path) -> dict:
    config = root / "app" / "etc" / "config.php"
    if not config.exists():
        return {"present": False}
    source = config.read_text(errors="ignore")
    state = {name: value == "1" for name, value in re.findall(r"'([A-Z]\w*_\w+)'\s*=>\s*(\d)", source)}
    return {
        "present": True,
        "two_factor_auth": state.get("Magento_TwoFactorAuth"),
        "csp": state.get("Magento_Csp"),
        "captcha": state.get("Magento_Captcha"),
        "admin_adobe_ims": state.get("Magento_AdminAdobeIms"),
        "version_module": state.get("Magento_Version"),
        "enabled_third_party_modules": sorted(name for name, enabled in state.items() if enabled and not name.startswith(("Magento_", "MageOS_"))),
        "dumped_config_paths": sorted(set(re.findall(r"'(csp|admin|web|dev|twofactorauth|webapi)'\s*=>", source))),
    }


def read_git(root: Path) -> dict:
    if git(root, "rev-parse", "--is-inside-work-tree") is None:
        return {"is_git_repository": False}
    tracked = (git(root, "ls-files") or "").splitlines()
    ignored = set((git(root, "check-ignore", "--no-index", *SENSITIVE_PATHS) or "").splitlines())
    ever_added = (git(root, "log", "--all", "--diff-filter=A", "--name-only", "--format=") or "").splitlines()
    history = {}
    for name, pattern in SECRET_PATTERNS.items():
        output = git(root, "log", "--all", "-G", pattern, "--format=%h", "--name-only")
        if output is None:
            history[name] = {"error": "git log failed or timed out"}
            continue
        commits, files, current = [], set(), None
        for line in output.splitlines():
            if re.fullmatch(r"[0-9a-f]{7,}", line):
                current = line
                commits.append(line)
            elif line and current:
                files.add(line)
        if commits:
            history[name] = {"commits": commits[:10], "commit_count": len(commits), "files": sorted(files)[:10]}
    return {
        "is_git_repository": True,
        "tracked_sensitive_files": sorted(path for path in tracked if NEVER_TRACKED.search(path)),
        "sensitive_files_in_history": sorted({path for path in ever_added if NEVER_TRACKED.search(path)}),
        "not_ignored": [path for path in SENSITIVE_PATHS if path not in ignored],
        "secret_patterns_in_history": history,
    }


def find_unexpected_php(root: Path) -> dict:
    pub = root / "pub"
    if not pub.is_dir():
        return {"pub_directory": False}
    return {
        "pub_directory": True,
        "pub_root_php": sorted(path.name for path in pub.glob("*.php") if path.name not in PUB_PHP_FILES),
        "media_or_static_php": sorted(str(path.relative_to(root)) for base in (pub / "media", pub / "static") if base.is_dir() for path in base.rglob("*.ph*") if path.is_file() and re.search(r"\.ph(p\d?|tml|ar)$", path.name))[:50],
    }


def find_obfuscated_code(root: Path) -> list[str]:
    hits = []
    for base in ("app/code", "app/design", "pub", "lib"):
        directory = root / base
        if not directory.is_dir():
            continue
        for path in directory.rglob("*.ph*"):
            if path.is_file() and "static" not in path.relative_to(root).parts[:2]:
                for number, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
                    if OBFUSCATION.search(line):
                        hits.append(f"{path.relative_to(root)}:{number}")
    return hits[:50]


def is_decision_due(decision: dict, today: date) -> bool:
    ask_again = decision.get("ask_again", "next_run")
    if ask_again in ("next_run", "next_upgrade"):
        return True
    if ask_again == "never":
        return False
    try:
        return date.fromisoformat(ask_again) <= today
    except ValueError:
        return True


def read_previous_run(root: Path, version: str | None) -> dict | None:
    scorecard = root / SCORECARD_FILE
    if not scorecard.exists():
        return None
    data = json.loads(scorecard.read_text())
    decisions = data.get("decisions", {})
    today = date.today()

    def due(decision: dict) -> bool:
        if decision.get("ask_again") == "next_upgrade":
            return decision.get("version_at_decision") != version
        return is_decision_due(decision, today)

    return {
        "checked_at": data.get("checked_at"),
        "version_at_check": data.get("version"),
        "areas": data.get("areas", {}),
        "decisions_due": {key: value for key, value in decisions.items() if due(value)},
        "decisions_waiting": {key: value for key, value in decisions.items() if not due(value)},
    }


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: audit.py <store-root>")
    root = Path(sys.argv[1]).resolve()
    if not (root / "app" / "etc").is_dir():
        sys.exit(f"{root} has no app/etc: run this from the store root, not a module")
    version = read_version(root)
    report = {
        "root": str(root),
        "previous_run": read_previous_run(root, version.get("version")),
        "version": version,
        "composer_patches": read_composer_patches(root),
        "app_code_modules": list_app_code_modules(root),
        "env": read_env(root),
        "modules": read_enabled_modules(root),
        "git": read_git(root),
        "unexpected_php": find_unexpected_php(root),
        "obfuscated_code": find_obfuscated_code(root),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
