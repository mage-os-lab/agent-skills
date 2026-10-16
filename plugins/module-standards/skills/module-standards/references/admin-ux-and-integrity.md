# Admin UX, i18n and integrity

A Mage-OS module should feel like part of Magento, not like a product bolted
onto it. Merchants should find its settings where they'd look for them, and
it should never phone home or advertise.

## Admin UX criteria

- **No custom config tabs, with one exception.** Sections go under an
  existing core tab: `general`, `catalog`, `customer`, `sales`, `service`,
  `advanced`. Pick the one that matches what the module affects: a checkout
  tweak goes in `sales`, a product attribute feature in `catalog`, developer
  tooling in `advanced`. The exception is the shared **Mage-OS** tab (tab id
  `mageos`, label "Mage-OS"): Mage-OS modules may place their section there,
  and declaring that tab in system.xml is allowed. Any other `<tab>`
  (vendor-branded or otherwise) fails. When moving a section out of a
  vendor tab, prefer a core tab if the feature clearly belongs to one;
  otherwise `mageos` is fine.
- **Config in one place.** All settings for the module live in one section
  (or in groups under an existing core section, e.g. a payment method under
  `payment`). Settings spread over several sections are hard to document and
  hard to find. Exception: a field that naturally belongs next to core
  settings it modifies.
- **ACL resources match the actions.** Viewing and editing are separate
  resources where it makes sense, and opening a read-only screen doesn't
  require the save permission.
- **Every section has its own ACL resource** in `etc/acl.xml` and references
  it via `<resource>` in system.xml, nested under `Magento_Config::config`.
- **No top-level menu items.** `etc/adminhtml/menu.xml` entries need a
  `parent` that is an existing core menu (`Magento_Backend::stores`,
  `Magento_Catalog::catalog`, `Magento_Sales::sales`,
  `Magento_Customer::customer`, `Magento_Backend::marketing`,
  `Magento_Backend::content`, `Magento_Backend::system`, `Magento_Reports::report`).
  A new top-level item with the vendor's name is the most common violation.
- **Scope flags make sense.** An API key is usually `showInDefault` and
  `showInWebsite`; a frontend text is usually store view level too.
- **Secrets use** `type="obscure"` with
  `backend_model="Magento\Config\Model\Config\Backend\Encrypted"` (see
  security.md).
- **No admin notifications or popups** pushed by the module beyond genuine
  operational messages (e.g. "API credentials invalid").

## i18n criteria

Every piece of text a merchant, admin user or customer can see goes through
Magento's translation layer, so stores in other languages can translate the
module without patching it.

- PHP: `__('Text with %1', $value)` for messages, exceptions shown to users
  (`LocalizedException`), message manager calls (`addSuccessMessage()` and
  friends), grid column labels, option source labels, email subjects.
  Placeholders (`%1`), never string concatenation, so translators see the
  whole sentence.
- Templates: `$escaper->escapeHtml(__('Text'))`.
- XML: `translate="label comment tooltip"` in system.xml, `translate="true"`
  on UI component labels, `translate="title"` in menu.xml and acl.xml.
- JavaScript: `$t('Text')` from `mage/translate`; Knockout templates use
  `i18n` bindings or `<translate>`.
- `i18n/en_US.csv` lists every phrase. Generate it with
  `bin/magento i18n:collect-phrases <module-dir> -o i18n/en_US.csv` when a
  store is available, then review it; otherwise collect phrases from the code.
- Log messages and developer-only exceptions don't need translating.

Fixing is mechanical and auto-fixable: wrap the string, add the phrase to the
CSV. The audit script flags common untranslated message calls under
`untranslated_messages`; templates and JS need reading.

## Integrity criteria

The module must not contain:

- **Callhome code**: requests to the vendor's servers for license checks,
  usage statistics, version pings, "news" feeds. Look for HTTP clients
  (`Magento\Framework\HTTP\Client\Curl`, `GuzzleHttp`, `curl_init`,
  `file_get_contents('http`), `Magento\AdminNotification\Model\Feed`
  subclasses, and cron jobs or admin observers that contact a URL.
- **Advertising and upsells**: banners, "Pro version" fields, links to paid
  extensions in system.xml comments or admin templates, vendor logos in
  config sections.
- **Tracking**: analytics snippets, pixels, or third-party scripts in admin
  or frontend layout that aren't the module's actual feature.
- **License key checks** or obfuscated code (`base64_decode` + `eval`,
  ionCube).

A module that integrates with an external service (payment provider, search
API, AI provider) obviously makes HTTP calls; that's its feature. The test is:
does the request serve the merchant's configured feature, using an endpoint
the merchant configured or expects? If yes, fine. If it sends data to the
module vendor for the vendor's benefit, it must go.

## Fixing

- **Moving a section out of a vendor tab** keeps the section ID, so config
  paths don't change and saved settings survive. Only the `<tab>` reference
  changes. Delete the vendor `<tab>` definition (never the shared `mageos`
  one; other modules use it). This is safe and auto-fixable.
- **Merging scattered sections** changes config paths, which drops saved
  settings unless you add a data patch that copies values from old paths to
  new ones (all scopes, not just default). Mark as "needs decision".
- **Top-level menu**: move items under the matching core parent; update the
  ACL tree to match.
- **Callhome and upsells**: removing them is a behavior change the maintainer
  must approve, but it's required, so present it as a required step, not an
  option. Also remove now-unused config fields, cron entries and their
  `config.xml` defaults.
