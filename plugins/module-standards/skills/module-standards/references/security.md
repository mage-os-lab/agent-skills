# Security and maintenance hygiene

A module runs inside someone's store with access to customer data and
payments. Security here is two things: the code itself, and the supply
chain around it (dependencies, CI, how vulnerabilities get reported).

Items marked **(required)** block acceptance into Mage-OS; the rest is the
quality bar.

## Code

**Admin access**
- Every admin controller sets `const ADMIN_RESOURCE = 'Vendor_Foo::...'`
  pointing to a resource defined in `etc/acl.xml`. A controller without it
  inherits `Magento_Backend::admin`, meaning any admin user can reach it.
  **(required)**
- Controllers that change state implement `HttpPostActionInterface` (not
  `HttpGetActionInterface`), so Magento's form key validation applies. A GET
  action that deletes or saves is a CSRF hole. **(required)**
- System config sections reference an ACL resource.

**Customer data ownership**
- Frontend controllers that load an entity by ID from the request (order,
  address, wishlist, quote, anything the module stores per customer) check
  that it belongs to the logged-in customer or the current guest session
  before showing or changing it. Changing `id/123` to `id/124` in the URL
  must not reveal someone else's data (IDOR). **(required)**

**Full page cache**
- Blocks that show customer-specific or session-specific data (name, cart,
  prices per customer group, recently viewed, messages) never render into a
  cached page, or the first visitor's data gets served to everyone. Use
  customer sections (`sections.xml` + `customerData`), private content
  loaded via AJAX, or GraphQL. **(required)**
- `cacheable="false"` on a layout block is almost always wrong: one such
  block makes every page using that layout handle uncacheable. In
  `default.xml` that is the whole site; in `catalog_product_view.xml` every
  product page. It is a severe performance problem, and usually a sign the
  block shows private data that should come from customer sections. The
  audit script lists every occurrence with a `verdict`:
  - `severe`: handles shared by cacheable pages (`default`, `catalog_*`,
    `cms_*`, `*_index_index`, ...). Fix it.
  - `acceptable`: pages Magento never caches anyway (checkout, cart,
    customer account, order views, multishipping, payment return and
    callback pages) and adminhtml layouts (no full page cache in the
    admin). Mention it, but no change needed.
  - `review`: the module's own frontend routes. Acceptable only when the
    page is genuinely per-visitor (an account or checkout-like flow);
    otherwise fix it.

**Public forms**
- Frontend forms that create data or send email (contact, questions,
  reviews, newsletter-like signups) validate the form key, and integrate
  with Magento's own CAPTCHA / reCAPTCHA (`Magento_ReCaptcha*` form types,
  or the `Magento_Captcha` module) so merchants can switch protection on.
  Without it, a public form becomes a spam relay or a way to fill the
  database.
- Rate limiting or throttling where a form triggers outbound email.

**Redirects**
- Redirects to a URL taken from the request (`referer`, `return_url`,
  `success_url`, base64-encoded `uenc` values) go through
  `Magento\Framework\Url\Validator` / `$this->_redirect->success()` or a
  check that the host belongs to the store. Otherwise the store's domain can
  be used for phishing links (open redirect).

**Admin-entered content**
- HTML that admins enter (WYSIWYG fields, Page Builder content, free-text
  config) and that is rendered on the frontend goes through Magento's
  template filter / `Magento\Cms\Model\Template\FilterProvider` and is
  limited to what the field needs. This matters as soon as the module has
  its own ACL resources: a content editor role must not be able to inject
  script that runs for customers or for higher-privileged admins.

**Web API and GraphQL**
- `etc/webapi.xml` routes with `<resource ref="anonymous"/>` are deliberate
  and only expose public data. `self` routes verify the customer owns the
  entity. **(required)**
- GraphQL resolvers that return customer data check
  `$context->getExtensionAttributes()->getIsCustomer()` and the customer ID.

**Output and input**
- Every dynamic value in `.phtml` goes through `$escaper->escapeHtml()`,
  `escapeHtmlAttr()`, `escapeUrl()` or `escapeJs()`, matching the context.
  `$block->escapeHtml()` is deprecated but still safe. Raw `<?= $var ?>` is
  an XSS risk. PHPCS flags most of these.
- Request input is read via `$this->getRequest()->getParam()` and validated
  or cast; never `$_GET`/`$_POST`/`$_REQUEST`.
- SQL goes through repositories, collections, or `$connection` methods with
  bound parameters (`$connection->quoteInto()`, `select()->where('x = ?', $v)`).
  String-concatenated SQL with request data is an injection. **(required)**
- No `unserialize()` on anything that could come from outside; use
  `Magento\Framework\Serialize\Serializer\Json`. No `eval`, `exec`,
  `shell_exec`, `system`, `passthru`, `proc_open` unless the module's
  feature truly needs it (a CLI tool wrapper), with escaped arguments.
- File paths built from input are validated against a base directory
  (path traversal). Uploads use `Magento\MediaStorage\Model\File\Uploader`
  with an extension allowlist.

**Secrets and data**
- API keys, passwords and tokens in config use `type="obscure"` and
  `backend_model="Magento\Config\Model\Config\Backend\Encrypted"`, and are
  read with `EncryptorInterface::decrypt()`. Mark them in `etc/di.xml` as
  sensitive (`Magento\Config\Model\Config\TypePool`, `sensitive` argument)
  so `app:config:dump` doesn't write them to `config.php`.
- No credentials, private keys or `.env` files committed. Check history too:
  `git log -p -S 'api_key' --all` and similar. A secret in history must be
  rotated, not just deleted.
- Logs don't contain secrets or full personal data (card numbers, full
  addresses, tokens). Check `->debug(`/`->info(` calls that dump request or
  response payloads.

**Outbound requests**
- URLs that come from config or admin input and are fetched server-side
  (provider base URLs, webhook targets, feed sources) are restricted to
  `http`/`https`. cURL happily follows `file://`, `gopher://` or `dict://`,
  turning a config field into local file reads or internal network access
  (SSRF), often with the module's API key attached.
- HTTP clients don't follow redirects to other hosts while sending
  credentials.

**Secrets in memory and forms**
- On PHP 8.2+, parameters carrying decrypted secrets (API keys, auth
  headers, passwords) get `#[\SensitiveParameter]`, so they're redacted from
  stack traces and error logs.
- Password and API key inputs in admin forms and templates use
  `autocomplete="new-password"`. `autocomplete="off"` is ignored by browsers
  on password fields, so the admin's saved login password can get autofilled
  into an API key field and sent to a third party.

**Frontend**
- External scripts, styles, images, fonts or API endpoints the module loads
  are whitelisted in `etc/csp_whitelist.xml`. Without it the module breaks
  in strict CSP mode (default for checkout since 2.4.7), and maintainers
  "fix" that by disabling CSP.
- Inline scripts use `SecureHtmlRenderer` (`$secureRenderer->renderTag()`)
  so they get a nonce.

## Supply chain

- `composer audit` passes; CI runs it (`assets/check-extension.yaml`).
- Dependencies are few and justified. Every extra package is attack surface
  and a version conflict waiting to happen; flag packages that are used for
  one small helper.
- `.github/dependabot.yml` covers `composer` and `github-actions`.
- GitHub Actions: `permissions: contents: read` at the top, actions pinned to
  commit SHAs, no `pull_request_target` checking out PR code, no secrets used
  in jobs that run for PRs from forks.
- `SECURITY.md` exists and names a working reporting route. Copy
  `assets/SECURITY.md` and replace `__SECURITY_EMAIL__` with the address
  for the target; the placeholder may not remain.
  - **Mage-OS module**: reports go to **security@mage-os.org**, so they
    reach the Mage-OS security contact even when a maintainer is
    unresponsive. An existing SECURITY.md that points elsewhere gets
    security@mage-os.org added as the primary address.
  - **Own extension**: reports go to the vendor's own security address. Ask
    for it if the repo doesn't reveal one (composer.json `support.security`
    or `support.email`, an existing SECURITY.md, the vendor website); never
    put security@mage-os.org in a third-party module. Also fill
    composer.json `support.security` with the same address.
  - For both, suggest the maintainer enables GitHub private vulnerability
    reporting under Settings > Code security as a second route; you can't
    do that from the repo files.

## Package hygiene

- `.gitattributes` with `export-ignore` for `.github/`, `docs/` and
  `.mage-os-standards.json` (see `assets/gitattributes`), so composer dist
  archives don't carry screenshots and CI config into every store. Keep
  `Test/` and the tool configs in the package: stores and the Mage-OS
  distribution may run module tests from `vendor/`. (check-extension itself
  installs from a mirrored path repository, so export-ignore doesn't affect
  it either way.)
- Declarative schema (`etc/db_schema.xml` plus `db_schema_whitelist.json`)
  instead of `InstallSchema`/`UpgradeSchema` scripts, so uninstalling and
  rolling back work. Data patches implement `PatchRevertableInterface` where
  a revert makes sense.

## Fixing

- Most code items are local, auto-fixable edits (add `ADMIN_RESOURCE`,
  escape output, bind parameters). Do them, list each one in the summary
  with file and line.
- Switching a GET controller to POST changes how the admin calls it; update
  the button/form/JS that calls it in the same change and mention it.
- Making a config field encrypted changes how existing values are read: an
  existing plaintext value would be "decrypted" into garbage. Add a data
  patch that encrypts existing values, and mark this "needs decision".
- If you find what looks like an exploitable vulnerability in a released
  version, tell the maintainer directly and plainly, recommend a security
  release, and don't describe the exploit in commit messages or the
  CHANGELOG beyond "security fix" until a fixed version is out.

## Questions to ask

**Code fixes** (auto-fixable, one question listing them):

> **I found 3 security issues:** an admin controller without an ACL check
> (`Controller/Adminhtml/Index/Index.php`), unescaped output in
> `view/frontend/templates/wrap.phtml:12`, and no `SECURITY.md`. All small
> local fixes.
>
> 1. Fix all three (Recommended)
> 2. Show me each fix first
> 3. Skip for now

A likely exploitable vulnerability gets its own question, put plainly, with
a security release as the recommendation.

**Encrypting a stored secret** (decision `security.encrypt_config_values`):

> **The API key is stored in plain text.** Anyone with database access or a
> config dump can read it. Encrypting it needs a data patch that encrypts
> values stores already saved, or the module would read them as garbage.
>
> 1. Encrypt it, with a data patch for existing values (Recommended)
> 2. Not now, ask again next run

**Hygiene** (auto-fixable): "Add `.gitattributes` so CI config and docs
stay out of the composer package, and Dependabot for composer and GitHub
Actions? (Recommended)"
