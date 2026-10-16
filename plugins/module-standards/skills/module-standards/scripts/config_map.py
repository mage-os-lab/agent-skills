#!/usr/bin/env python3
"""Print every admin setting of a Magento 2 module with its exact admin path.

Usage: python3 config_map.py <module-root>

Reads etc/adminhtml/system.xml (and <include> partials), etc/config.xml defaults
and etc/adminhtml/menu.xml. Output is a Markdown outline for writing the README.
"""

import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

CORE_TAB_LABELS = {
    "general": "General",
    "catalog": "Catalog",
    "customer": "Customers",
    "sales": "Sales",
    "service": "Services",
    "advanced": "Advanced",
}
CORE_SECTION_LABELS = {
    "general": ("general", "General"),
    "web": ("general", "Web"),
    "design": ("general", "Design"),
    "currency": ("general", "Currency Setup"),
    "contact": ("general", "Contacts"),
    "catalog": ("catalog", "Catalog"),
    "cataloginventory": ("catalog", "Inventory"),
    "sitemap": ("catalog", "XML Sitemap"),
    "rss": ("catalog", "RSS Feeds"),
    "sendfriend": ("catalog", "Email to a Friend"),
    "customer": ("customer", "Customer Configuration"),
    "newsletter": ("customer", "Newsletter"),
    "wishlist": ("customer", "Wish List"),
    "persistent": ("customer", "Persistent Shopping Cart"),
    "sales": ("sales", "Sales"),
    "sales_email": ("sales", "Sales Emails"),
    "checkout": ("sales", "Checkout"),
    "tax": ("sales", "Tax"),
    "shipping": ("sales", "Delivery Methods"),
    "carriers": ("sales", "Delivery Methods"),
    "payment": ("sales", "Payment Methods"),
    "multishipping": ("sales", "Multishipping Settings"),
    "dev": ("advanced", "Developer"),
    "admin": ("advanced", "Admin"),
    "system": ("advanced", "System"),
    "advanced": ("advanced", "Advanced"),
}
SCOPE_ATTRIBUTES = (("showInDefault", "Default"), ("showInWebsite", "Website"), ("showInStore", "Store View"))
MENU_ROOT_LABELS = {
    "Magento_Backend::stores": "Stores",
    "Magento_Catalog::catalog": "Catalog",
    "Magento_Sales::sales": "Sales",
    "Magento_Customer::customer": "Customers",
    "Magento_Backend::marketing": "Marketing",
    "Magento_Backend::content": "Content",
    "Magento_Reports::report": "Reports",
    "Magento_Backend::system": "System",
}


def load_with_includes(path: Path, module_root: Path) -> list[ElementTree.Element]:
    root = ElementTree.parse(path).getroot()
    elements = [root]
    for include in root.iter("include"):
        target = include.get("path", "").split("::", 1)[-1]
        include_path = module_root / "etc" / "adminhtml" / target
        if include_path.exists():
            elements += load_with_includes(include_path, module_root)
    return elements


def read_defaults(module_root: Path) -> dict[str, str]:
    config_xml = module_root / "etc" / "config.xml"
    if not config_xml.exists():
        return {}
    default = ElementTree.parse(config_xml).getroot().find("default")
    if default is None:
        return {}
    return {
        f"{section.tag}/{group.tag}/{field.tag}": (field.text or "").strip()
        for section in default
        for group in section
        for field in group
        if len(field) == 0
    }


def scopes(element: ElementTree.Element) -> str:
    return ", ".join(label for attribute, label in SCOPE_ATTRIBUTES if element.get(attribute) == "1") or "not shown"


def label_of(element: ElementTree.Element, fallback: str) -> str:
    return (element.findtext("label") or "").strip() or fallback


def section_breadcrumb(section: ElementTree.Element, tab_labels: dict[str, str]) -> str:
    section_id = section.get("id", "")
    known_tab, known_label = CORE_SECTION_LABELS.get(section_id, (None, None))
    tab_id = section.findtext("tab") or known_tab
    tab = tab_labels.get(tab_id or "", f"[tab `{tab_id}` defined elsewhere]" if tab_id else "[tab defined elsewhere]")
    section_label = label_of(section, known_label or f"[section `{section_id}` defined elsewhere]")
    return f"Stores > Configuration > {tab} > {section_label}"


def describe_field(field: ElementTree.Element, path: str, defaults: dict[str, str]) -> list[str]:
    lines = [f"- **{label_of(field, field.get('id', ''))}** (`{path}`)"]
    details = [f"type: {field.get('type', 'text')}", f"scope: {scopes(field)}"]
    if path in defaults:
        details.append(f"default: `{defaults[path]}`")
    for tag in ("source_model", "backend_model", "frontend_model"):
        if field.findtext(tag):
            details.append(f"{tag}: `{field.findtext(tag).strip()}`")
    lines.append(f"  - {'; '.join(details)}")
    depends = field.find("depends")
    if depends is not None:
        conditions = ", ".join(f"{dependency.get('id', dependency.tag) if dependency.tag == 'field' else dependency.tag} = {(dependency.text or '').strip()}" for dependency in depends)
        lines.append(f"  - only shown when: {conditions}")
    for tag in ("comment", "tooltip"):
        text = " ".join((field.findtext(tag) or "").split())
        if text:
            lines.append(f"  - {tag}: {text}")
    return lines


def describe_group(group: ElementTree.Element, prefix: str, breadcrumb: str, defaults: dict[str, str]) -> list[str]:
    group_path = f"{prefix}/{group.get('id')}"
    group_breadcrumb = f"{breadcrumb} > {label_of(group, group.get('id', ''))}"
    lines = [f"\n### {group_breadcrumb}", f"scope: {scopes(group)}"]
    for child in group:
        if child.tag == "field":
            lines += describe_field(child, f"{group_path}/{child.get('id')}", defaults)
        elif child.tag == "group":
            lines += describe_group(child, group_path, group_breadcrumb, defaults)
    return lines


def describe_config(module_root: Path) -> list[str]:
    system_xml = module_root / "etc" / "adminhtml" / "system.xml"
    if not system_xml.exists():
        return ["No etc/adminhtml/system.xml: the module has no admin configuration."]
    documents = load_with_includes(system_xml, module_root)
    tab_labels = dict(CORE_TAB_LABELS)
    for document in documents:
        for tab in document.iter("tab"):
            tab_id = tab.get("id", "")
            tab_labels[tab_id] = label_of(tab, tab_id) if tab_id == "mageos" else f"{label_of(tab, tab_id)} [CUSTOM TAB]"
    defaults = read_defaults(module_root)
    lines = ["## Configuration"]
    for document in documents:
        for section in document.iter("section"):
            breadcrumb = section_breadcrumb(section, tab_labels)
            lines.append(f"\n## {breadcrumb}")
            lines.append(f"section id: `{section.get('id')}`; ACL: `{section.findtext('resource') or 'none'}`")
            for group in section.findall("group"):
                lines += describe_group(group, section.get("id", ""), breadcrumb, defaults)
    return lines


def describe_menu(module_root: Path) -> list[str]:
    menu_xml = module_root / "etc" / "adminhtml" / "menu.xml"
    if not menu_xml.exists():
        return []
    items = {item.get("id"): item for item in ElementTree.parse(menu_xml).getroot().iter("add")}

    def breadcrumb(item_id: str | None) -> str:
        if item_id in MENU_ROOT_LABELS:
            return MENU_ROOT_LABELS[item_id]
        if item_id not in items:
            return f"[menu `{item_id}` defined elsewhere]"
        item = items[item_id]
        parent = item.get("parent")
        own = item.get("title", item_id or "")
        return f"{breadcrumb(parent)} > {own}" if parent else f"{own} [TOP-LEVEL MENU]"

    lines = ["\n## Admin pages"]
    for item_id, item in items.items():
        action = item.get("action")
        if action:
            lines.append(f"- {breadcrumb(item_id)} (route `{action}`, ACL `{item.get('resource')}`)")
    return lines


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: config_map.py <module-root>")
    repository_root = Path(sys.argv[1]).resolve()
    module_xml_files = sorted(repository_root.rglob("etc/module.xml"), key=lambda path: len(path.parts))
    module_root = module_xml_files[0].parent.parent if module_xml_files else repository_root
    print("\n".join(describe_config(module_root) + describe_menu(module_root)))


if __name__ == "__main__":
    main()
