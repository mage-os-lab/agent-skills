# Admin and configuration

The admin is where an attacker with a stolen password does the most damage:
they can add a skimmer through a CMS block in two minutes. These settings
make a stolen or guessed password much less useful.

Read values with `bin/magento config:show <path>`. Two traps:

- **Empty output** means the value isn't stored, so the default from the
  declaring module's `etc/config.xml` applies. The defaults are given below.
- **"The path doesn't exist"** means either the module declaring it is
  disabled (2FA paths while `Magento_TwoFactorAuth` is off) or the path has
  no admin field (the CSP modes). Read those in the database instead:
  `SELECT path, scope, scope_id, value FROM core_config_data WHERE path LIKE 'csp/mode/%';`
  and fall back to the default when there's no row.

Stores that dump config to files keep some values in `app/etc/config.php`
or `env.php` (`modules.dumped_config_paths`); those win over the database.

## Admin criteria (Recommended)

- **Two-factor authentication on** (`modules.two_factor_auth`): the
  `Magento_TwoFactorAuth` module enabled, with at least one provider
  configured (`twofactorauth/general/force_providers`). Disabling it is the
  most common shortcut and the most expensive one.
- **Admin URL not guessable** (`env.admin_path_guessable`): not `admin`,
  `backend` or similar. It doesn't stop a determined attacker, but it stops
  the bots that try passwords on `/admin` all day. Better still: the admin
  reachable only from known IPs or a VPN, at the web server.
- **Lockout**: `admin/security/lockout_failures` set (default 6) and
  `admin/security/lockout_threshold` in minutes (default 30).
- **Sessions**: `admin/security/session_lifetime` at most 3600 seconds
  (default 900); `admin/security/admin_account_sharing` 0 (default), so one
  login can't be used from two places at once.
- **Passwords**: `admin/security/password_is_forced` 1 and
  `admin/security/password_lifetime` set (defaults 1 and 90 days).
- **Captcha on the admin login**: `admin/captcha/enable` 1 (default).
- **Form keys**: `admin/security/use_form_key` 1 (CSRF protection). Never 0.

## Configuration criteria (Recommended)

- **Production mode** (`env.mage_mode`): developer mode shows stack traces
  with paths and queries to visitors and is slower.
- **CSP enforced**: `csp/mode/storefront/report_only` and
  `csp/mode/admin/report_only` 0 (default 1, report-only). In report-only
  mode, a skimmer's script loads and is merely reported. Since 2.4.7
  checkout pages enforce CSP by default; the rest of the storefront
  doesn't.
- **HTTPS everywhere**: `web/secure/use_in_frontend` and
  `web/secure/use_in_adminhtml` 1, `web/secure/base_url` on `https://`,
  `web/secure/enable_hsts` 1.
- **Cookies**: `web/cookie/cookie_httponly` 1.
- **No debug output**: `dev/debug/template_hints_storefront` and
  `dev/debug/template_hints_admin` 0.
- **Guest API access off unless needed**: `webapi/webapisecurity/allow_insecure`
  0, so anonymous REST calls can't read store configuration and catalog
  data meant for logged-in clients.
- **Version not advertised**: `Magento_Version` disabled
  (`modules.version_module`), which serves `/magento_version` to anyone
  and helps bots pick stores with known holes.

## Fixing

1. Config values: `bin/magento config:set <path> <value>`, then
   `bin/magento cache:clean config`. If the store dumps config to files, set
   it there instead and say so. `config:set` refuses paths without an admin
   field, like the CSP modes: set those in the `system` section of
   `app/etc/config.php` (`'system' => ['default' => ['csp' => ['mode' =>
   ['storefront' => ['report_only' => 0]]]]]`), or in the `etc/config.xml`
   of a store module, and say which you chose.
2. 2FA: `bin/magento module:enable Magento_TwoFactorAuth`,
   `setup:upgrade`, then configure a provider
   (`bin/magento config:set twofactorauth/general/force_providers google`).
   Every admin user sets it up at next login: tell them before.
3. Admin URL: `bin/magento setup:config:set --backend-frontname=<name>`.
   Bookmarks and any integration calling the admin URL break: needs
   decision. Never write the new name in the scorecard or a commit message.
4. Production mode: `bin/magento deploy:mode:set production`. It compiles
   DI and static content, takes minutes and is a deploy: needs decision on
   a live store.
5. CSP restrict: turn it on in staging first and browse checkout, the cart
   and the pages with third-party widgets; add what's legitimately blocked
   to a `csp_whitelist.xml` in a store module before turning it on in
   production. Needs decision.
6. `Magento_Version`: `bin/magento module:disable Magento_Version`,
   `setup:upgrade`.

## Questions to ask

**2FA off** (decision `admin.two_factor_auth`):

> **Two-factor authentication is disabled.** A single leaked admin password
> is enough to add a skimmer to checkout. Every admin user will set up an
> authenticator app at their next login.
>
> 1. Turn it on, with Google Authenticator as provider (Recommended)
> 2. Skip for now

**Guessable admin URL** (decision `admin.custom_path`): "The admin is at
`/admin`, where bots try passwords all day. Move it to a random path?
Bookmarks will need updating." with "Move it, and restrict it by IP at the
web server too (Recommended)", "Move it only", "Skip for now".

**CSP report-only** (decision `configuration.csp_restrict`): "CSP only
reports blocked scripts on the storefront, so an injected skimmer still
runs. Switch to restrict mode after testing on staging? (Recommended)"

**Small settings** (auto-fixable, one bundled question): lockout, session
lifetime, captcha, template hints, guest API access, `Magento_Version`.
