#!/usr/bin/env python3
"""Collect mechanical signals about a Magento 2 module for the Mage-OS standards audit.

Usage: python3 audit.py <module-root>

Prints JSON. Every finding is a lead to verify by reading the file, not a verdict.
"""

import json
import re
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from datetime import date
from pathlib import Path

ACCEPTED_LICENSES = {"OSL-3.0", "AFL-3.0", "MIT", "BSD-3-Clause"}
SKIPPED_DIRECTORIES = {"vendor", "node_modules", ".git", "generated"}
CORE_TABS = {"general", "catalog", "customer", "sales", "service", "advanced"}
SHARED_MAGEOS_TAB = "mageos"
TARGET_PHPSTAN_LEVEL = 8
SCORECARD_FILE = ".mage-os-standards.json"
CURRENT_SCORECARD_VERSION = 2
SEMVER_TAG = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")
DECISIONS_BLOCKING_ACCEPTANCE = {"identity.rename", "license.change", "integrity.removal", "admin_ux.merge_sections"}

RISKY_PATTERNS = {
    "http_client": r"curl_init|GuzzleHttp|HTTP\\Client\\Curl|file_get_contents\(\s*['\"]https?:",
    "admin_notification_feed": r"AdminNotification\\Model\\Feed",
    "dangerous_functions": r"(?<![>:$\w])(eval|exec|shell_exec|system|passthru|proc_open|unserialize)\s*\(",
    "untranslated_messages": r"(add(Success|Error|Warning|Notice|Complex\w+)Message|LocalizedException)\(\s*['\"]",
    "obfuscation": r"base64_decode\s*\(.*\)\s*\)|ionCube|gzinflate\s*\(",
    "request_based_redirect": r"(setUrl|setRedirect|_redirect|setPath)\(.*getParam\(",
    "superglobals": r"\$_(GET|POST|REQUEST|COOKIE|SERVER)\b",
    "raw_sql_concatenation": r"(->query|->fetchAll|->fetchRow|->fetchOne)\s*\(\s*['\"][^'\"]*['\"]\s*\.",
}
TEMPLATE_PATTERNS = {
    "unescaped_output": r"<\?=\s*\$(?!escaper|block->escape|secureRenderer)[^;?]*\?>",
}


def iter_files(root: Path, suffixes: tuple[str, ...]):
    for path in root.rglob("*"):
        if any(part in SKIPPED_DIRECTORIES for part in path.relative_to(root).parts):
            continue
        if path.is_file() and path.suffix in suffixes:
            yield path


def read_composer(root: Path) -> dict:
    composer_file = root / "composer.json"
    if not composer_file.exists():
        return {"present": False}
    data = json.loads(composer_file.read_text())
    licenses = data.get("license", [])
    licenses = [licenses] if isinstance(licenses, str) else licenses
    return {
        "present": True,
        "name": data.get("name"),
        "type": data.get("type"),
        "description": data.get("description"),
        "license": licenses,
        "license_accepted": bool(licenses) and all(item in ACCEPTED_LICENSES for item in licenses),
        "has_version_field": "version" in data,
        "require": data.get("require", {}),
        "require_dev": data.get("require-dev", {}),
        "autoload": data.get("autoload", {}),
        "replace": data.get("replace", {}),
        "repositories": data.get("repositories", []),
    }


def find_module_directory(root: Path) -> Path:
    candidates = sorted(
        (path.parent.parent for path in root.rglob("etc/module.xml") if not SKIPPED_DIRECTORIES & set(path.relative_to(root).parts)),
        key=lambda path: len(path.parts),
    )
    return candidates[0] if candidates else root


def read_git_tags(root: Path) -> dict:
    result = subprocess.run(["git", "-C", str(root), "tag", "--list"], capture_output=True, text=True)
    if result.returncode != 0:
        return {"is_git_repository": False, "tags": [], "is_new_package": None}
    tags = result.stdout.split()
    remote = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"], capture_output=True, text=True).stdout.strip()
    return {
        "is_git_repository": True,
        "tag_count": len(tags),
        "latest_version": find_latest_version(tags),
        "is_new_package": tags == [],
        "origin": remote or None,
        "is_in_mage_os_org": bool(re.search(r"github\.com[:/]mage-os(-lab)?/", remote)) if remote else None,
    }


def find_latest_version(tags: list[str]) -> str | None:
    versions = [tag for tag in tags if SEMVER_TAG.match(tag)]
    return max(versions, key=lambda tag: tuple(int(part) for part in SEMVER_TAG.match(tag).groups())) if versions else None


def major_version(tag: str | None) -> int:
    match = SEMVER_TAG.match(tag or "")
    return int(match.group(1)) if match else -1


def suggest_identity(package_name: str | None, module_name: str | None) -> dict:
    return {
        "package_is_mage_os": (package_name or "").startswith("mage-os/"),
        "module_is_mage_os": (module_name or "").startswith("MageOS_"),
        "suggested_package_name": f"mage-os/{package_name.split('/', 1)[1]}" if package_name and "/" in package_name else None,
        "suggested_module_name": f"MageOS_{module_name.split('_', 1)[1]}" if module_name and "_" in module_name else None,
    }


def read_module_name(root: Path) -> str | None:
    module_xml = root / "etc" / "module.xml"
    if not module_xml.exists():
        return None
    module = ElementTree.parse(module_xml).getroot().find("module")
    return module.get("name") if module is not None else None


def find_config_tabs_and_sections(root: Path) -> dict:
    tabs, sections = [], []
    for system_xml in (root / "etc" / "adminhtml").rglob("*.xml") if (root / "etc" / "adminhtml").exists() else []:
        if system_xml.name == "menu.xml":
            continue
        try:
            tree = ElementTree.parse(system_xml).getroot()
        except ElementTree.ParseError:
            continue
        tabs += [{"id": tab.get("id"), "file": str(system_xml.relative_to(root))} for tab in tree.iter("tab") if tab.get("id") and tab.get("id") != SHARED_MAGEOS_TAB]
        for section in tree.iter("section"):
            tab = section.findtext("tab")
            sections.append({
                "id": section.get("id"),
                "tab": tab,
                "tab_is_allowed": tab is None or tab in CORE_TABS or tab == SHARED_MAGEOS_TAB,
                "has_resource": section.find("resource") is not None,
            })
    return {"custom_tabs": tabs, "sections": sections}


def find_top_level_menu_items(root: Path) -> list[str]:
    menu_xml = root / "etc" / "adminhtml" / "menu.xml"
    if not menu_xml.exists():
        return []
    return [item.get("id") for item in ElementTree.parse(menu_xml).getroot().iter("add") if not item.get("parent")]


def find_admin_controllers_without_acl(root: Path) -> list[str]:
    controller_directory = root / "Controller" / "Adminhtml"
    if not controller_directory.exists():
        return []
    sources = {path.stem: path.read_text(errors="ignore") for path in root.rglob("*.php") if "vendor" not in path.parts}

    def declares_acl(source: str, seen: frozenset[str] = frozenset()) -> bool:
        if "ADMIN_RESOURCE" in source or "_isAllowed" in source:
            return True
        parent = re.search(r"\bextends\s+\\?([\w\\]+)", source)
        parent_name = parent.group(1).split("\\")[-1] if parent else None
        if parent_name is None or parent_name in seen or parent_name not in sources:
            return False
        return declares_acl(sources[parent_name], seen | {parent_name})

    return [
        str(path.relative_to(root))
        for path in controller_directory.rglob("*.php")
        if "abstract class" not in path.read_text(errors="ignore")
        and re.search(r"\bclass\s+\w+\s+(extends|implements)\b", path.read_text(errors="ignore"))
        and not declares_acl(path.read_text(errors="ignore"))
    ]


def scan_patterns(root: Path, suffixes: tuple[str, ...], patterns: dict[str, str]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = {name: [] for name in patterns}
    for path in iter_files(root, suffixes):
        if "Test" in path.relative_to(root).parts:
            continue
        for number, line in enumerate(path.read_text(errors="ignore").splitlines(), start=1):
            for name, pattern in patterns.items():
                if re.search(pattern, line):
                    hits[name].append(f"{path.relative_to(root)}:{number}")
    return {name: locations[:25] for name, locations in hits.items() if locations}


UNCACHED_HANDLE_PREFIXES = (
    "checkout_", "customer_account", "customer_address", "sales_order_", "sales_guest_",
    "multishipping_", "paypal_", "braintree_", "vault_", "wishlist_", "review_customer_",
    "newsletter_manage", "downloadable_customer", "persistent_",
)
SHARED_HANDLE_PREFIXES = ("default", "catalog_", "cms_", "catalogsearch_", "page_", "1column", "2columns", "3columns")


def classify_uncacheable_handle(path: Path) -> str:
    if "adminhtml" in path.parts:
        return "acceptable"
    handle = path.stem
    if handle.startswith(UNCACHED_HANDLE_PREFIXES):
        return "acceptable"
    if handle.startswith(SHARED_HANDLE_PREFIXES) or handle.endswith("_index_index"):
        return "severe"
    return "review"


def find_uncacheable_layout_blocks(root: Path) -> list[dict]:
    layout_files = [path for path in iter_files(root, (".xml",)) if "layout" in path.parts]
    return [
        {"file": str(path.relative_to(root)), "block": block.get("name"), "verdict": classify_uncacheable_handle(path)}
        for path in layout_files
        for block in safe_parse(path).iter("block")
        if block.get("cacheable") == "false"
    ]


def safe_parse(path: Path) -> ElementTree.Element:
    try:
        return ElementTree.parse(path).getroot()
    except ElementTree.ParseError:
        return ElementTree.Element("unparseable")


def find_obscure_fields_without_encryption(root: Path) -> list[str]:
    findings = []
    for system_xml in iter_files(root / "etc", (".xml",)) if (root / "etc").exists() else []:
        try:
            tree = ElementTree.parse(system_xml).getroot()
        except ElementTree.ParseError:
            continue
        for field in tree.iter("field"):
            backend_model = field.findtext("backend_model") or ""
            if field.get("type") == "obscure" and "Encrypted" not in backend_model:
                findings.append(f"{system_xml.relative_to(root)}: field {field.get('id')}")
    return findings


def presence(root: Path, module: Path) -> dict[str, bool]:
    workflows = list((root / ".github" / "workflows").glob("*.y*ml")) if (root / ".github" / "workflows").exists() else []
    workflow_text = "\n".join(path.read_text(errors="ignore") for path in workflows)
    return {
        "license_file": any((root / name).exists() for name in ("LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING.txt")),
        "readme": (root / "README.md").exists(),
        "changelog": (root / "CHANGELOG.md").exists(),
        "security_md": (root / "SECURITY.md").exists() or (root / ".github" / "SECURITY.md").exists(),
        "docs_directory": (root / "docs").is_dir(),
        "check_extension_workflow": "check-extension.yaml@" in workflow_text,
        "check_extension_config": (root / ".github" / "check-extension.json").exists(),
        "composer_audit_in_ci": "composer audit" in workflow_text,
        "workflow_permissions_set": "permissions:" in workflow_text,
        "dependabot": (root / ".github" / "dependabot.yml").exists() or (root / ".github" / "dependabot.yaml").exists(),
        "phpstan_config": any((root / name).exists() for name in ("phpstan.neon", "phpstan.neon.dist", "phpstan.dist.neon")),
        "phpstan_baseline": (root / "phpstan-baseline.neon").exists(),
        "phpcs_config": any((root / name).exists() for name in ("phpcs.xml", "phpcs.xml.dist", ".phpcs.xml.dist")),
        "phpunit_config": any((root / name).exists() for name in ("phpunit.xml", "phpunit.xml.dist")),
        "unit_tests": (root / "Test" / "Unit").is_dir() or (module / "Test" / "Unit").is_dir(),
        "integration_tests": (root / "Test" / "Integration").is_dir() or (module / "Test" / "Integration").is_dir(),
        "gitattributes": (root / ".gitattributes").exists(),
        "csp_whitelist": (module / "etc" / "csp_whitelist.xml").exists(),
        "acl_xml": (module / "etc" / "acl.xml").exists(),
        "config_xml": (module / "etc" / "config.xml").exists(),
        "i18n": (module / "i18n").is_dir(),
        "declarative_schema": (module / "etc" / "db_schema.xml").exists(),
        "legacy_schema_scripts": any((module / "Setup" / name).exists() for name in ("InstallSchema.php", "UpgradeSchema.php", "InstallData.php", "UpgradeData.php")),
    }


def read_phpstan_level(root: Path) -> int | str | None:
    for name in ("phpstan.neon", "phpstan.neon.dist", "phpstan.dist.neon"):
        config = root / name
        if config.exists():
            match = re.search(r"^\s*level:\s*(\w+)", config.read_text(), re.MULTILINE)
            return (int(match.group(1)) if match.group(1).isdigit() else match.group(1)) if match else None
    return None


def count_phpstan_baseline_errors(root: Path) -> int | None:
    baseline = root / "phpstan-baseline.neon"
    if not baseline.exists():
        return None
    text = baseline.read_text(errors="ignore")
    counts = re.findall(r"^\s*count:\s*(\d+)", text, re.MULTILINE)
    return sum(int(count) for count in counts) if counts else len(re.findall(r"^\s*-?\s*(?:raw)?[mM]essage:", text, re.MULTILINE))


def read_static_analysis(root: Path) -> dict:
    level = read_phpstan_level(root)
    return {
        "phpstan_level": level,
        "phpstan_target_level": TARGET_PHPSTAN_LEVEL,
        "phpstan_levels_to_go": TARGET_PHPSTAN_LEVEL - level if isinstance(level, int) else None,
        "phpstan_baseline_errors": count_phpstan_baseline_errors(root),
    }


def count_tests(root: Path, module: Path) -> dict:
    def test_files(kind: str) -> set[Path]:
        return {path.resolve() for base in {root, module} for path in (base / "Test" / kind).rglob("*Test.php")} if any((base / "Test" / kind).is_dir() for base in {root, module}) else set()

    def test_methods(files: set[Path]) -> int:
        return sum(len(re.findall(r"function\s+test\w*\s*\(|#\[Test\]|@test\b", path.read_text(errors="ignore"))) for path in files)

    unit, integration = test_files("Unit"), test_files("Integration")
    source_files = [path for path in iter_files(module, (".php",)) if "Test" not in path.relative_to(module).parts and path.name != "registration.php"]
    return {
        "source_php_files": len(source_files),
        "unit_test_files": len(unit),
        "unit_test_methods": test_methods(unit),
        "integration_test_files": len(integration),
        "integration_test_methods": test_methods(integration),
    }


def is_decision_due(decision: dict, latest_version: str | None, today: date) -> bool:
    ask_again = decision.get("ask_again", "next_run")
    if ask_again == "never":
        return False
    if ask_again == "next_run":
        return True
    if ask_again == "next_major":
        return major_version(latest_version) > major_version(decision.get("version_at_decision"))
    try:
        return date.fromisoformat(ask_again) <= today
    except ValueError:
        return True


def read_previous_run(root: Path, latest_version: str | None) -> dict | None:
    scorecard = root / SCORECARD_FILE
    if not scorecard.exists():
        return None
    data = json.loads(scorecard.read_text())
    decisions = data.get("decisions", {})
    today = date.today()
    return {
        "checked_at": data.get("checked_at"),
        "areas": data.get("areas", {}),
        "notes": data.get("notes", []),
        "needs_migration": data.get("skill_version", 1) < CURRENT_SCORECARD_VERSION,
        "decisions_due": {key: value for key, value in decisions.items() if is_decision_due(value, latest_version, today)},
        "decisions_waiting": {key: value for key, value in decisions.items() if not is_decision_due(value, latest_version, today)},
        "declined_blocking_acceptance": sorted(key for key, value in decisions.items() if key in DECISIONS_BLOCKING_ACCEPTANCE and value.get("choice") == "declined"),
    }


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: audit.py <module-root>")
    root = Path(sys.argv[1]).resolve()
    module_directory = find_module_directory(root)
    composer = read_composer(root)
    module_name = read_module_name(module_directory)
    git = read_git_tags(root)
    report = {
        "root": str(root),
        "module_directory": str(module_directory),
        "git": git,
        "previous_run": read_previous_run(root, git.get("latest_version")),
        "composer": composer,
        "module_name": module_name,
        "identity": suggest_identity(composer.get("name"), module_name),
        "presence": presence(root, module_directory),
        "static_analysis": read_static_analysis(root),
        "tests": count_tests(root, module_directory),
        "admin_config": find_config_tabs_and_sections(module_directory),
        "top_level_menu_items": find_top_level_menu_items(module_directory),
        "admin_controllers_without_acl": find_admin_controllers_without_acl(module_directory),
        "obscure_fields_without_encryption": find_obscure_fields_without_encryption(module_directory),
        "code_pattern_hits": scan_patterns(root, (".php",), RISKY_PATTERNS),
        "template_pattern_hits": scan_patterns(root, (".phtml",), TEMPLATE_PATTERNS),
        "uncacheable_layout_blocks": find_uncacheable_layout_blocks(module_directory),
        "external_urls": scan_patterns(root, (".php", ".phtml", ".xml", ".js"), {"url": r"https?://(?!www\.w3\.org|schemas\.|magento\.com/schema|json-schema\.org|opensource\.org)[\w.-]+"}).get("url", []),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
