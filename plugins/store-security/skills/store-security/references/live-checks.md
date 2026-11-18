# Live site checks

A file that is safe on disk can still be served to anyone: `.git/` copied to
the web root, `env.php` reachable because the web server's document root is
the store root instead of `pub/`. Only a request to the real site shows it.

## Consent

Run these checks only on a store the maintainer runs, at the base URL they
give you, after they said yes to this question (first round of step 3):

> **Shall I check the live site at the URL you give me?** I'd send about
> 25 read-only GET requests to a fixed list of paths (`/.git/HEAD`,
> `/app/etc/env.php`, `/admin`, ...) and read the response headers. No login
> attempts, nothing sent to forms, no other URLs. A WAF may log them.
>
> 1. Yes, at <URL> (Recommended)
> 2. No, skip the live site

If the URL isn't theirs (a competitor, a client they don't run), or they
ask for more (login attempts, a scanner, other paths), decline that part
and say why. Never point the script at a URL taken from anywhere but their
answer.

## Running

```bash
python3 <skill-dir>/scripts/live_check.py https://store.example [--admin-path <path>]
```

It sends GET requests without following redirects, compares each response
with a random-path "not found" page to rule out stores that answer 200 to
everything, and prints status codes and verdicts, never response bodies.
Pass `--admin-path` only when the maintainer gives the real admin path; it
is reported as `configured_admin_path`, never by name.

Certificates are always verified. A local store with a mkcert certificate
needs its CA: `--cafile <rootCA.pem>` (docker-magento installs it under
`/usr/local/share/ca-certificates/`). When the script reports `reachable:
false`, area 7 is "not checked": give the error, don't guess. On a public
store, a certificate that fails verification is itself a Critical
finding.

## Criteria (Recommended, except exposed files)

- **Nothing in `exposed`** (Critical when not empty): `.git/` lets anyone
  download the whole repository and its history; `app/etc/env.php` served
  as source gives away the database and the crypt key; `composer.lock` and
  `magento_version` tell attackers which holes to try. When
  `app/etc/env.php` or `composer.json` is exposed, the document root is
  almost certainly the store root instead of `pub/`.
- **Admin login not public** (`admin.*.login_form_public`): a login form at
  `/admin` or `/backend` means the bots find it. The configured path being
  public is common; restricting it by IP is the stronger fix.
- **HTTPS enforced** (`plain_http.redirects_to_https`).
- **Security headers** (`security_headers`):
  `Strict-Transport-Security`, `Content-Security-Policy` (report-only is a
  finding, see `admin-and-config.md`), `X-Frame-Options` (Magento sets
  `SAMEORIGIN` by default; missing means a proxy strips it) and
  `X-Content-Type-Options: nosniff`.
- **No version disclosure** (`disclosing_headers`): `Server` or
  `X-Powered-By` with version numbers, and `X-Magento-Cache-Debug` /
  `X-Magento-Tags`, which only show in developer mode.

## Fixing

These are web server settings, outside the repository: write the change
for the maintainer or their host, don't apply it unless the server config
lives in the repository (`nginx.conf.sample` copy, `.ddev`, Docker files).

1. Document root to `pub/`: in nginx, `set $MAGE_ROOT` to the store root
   and include Magento's `nginx.conf.sample`, which serves `pub/`; in
   Apache, point `DocumentRoot` at `pub/`.
2. Block dotfiles and the rest while that's being done:
   `location ~ /\. { deny all; }` in nginx.
3. Headers: HSTS through `web/secure/enable_hsts`, the rest in the web
   server or CDN; `server_tokens off;` and `expose_php = Off` for versions.
4. Admin by IP: an `allow`/`deny` block on the admin path at the web
   server, or the CDN's access rules.

## Questions to ask

**Exposed files** (Critical): "The live site serves `/.git/HEAD` and
`/app/etc/env.php`. Anyone can download the code and the crypt key. Block
them at the web server now and treat the keys as leaked (see
`secrets.md`)? (Recommended)"

**Headers** (bundled): "HSTS and `X-Content-Type-Options` are missing and
the `Server` header shows the nginx version. Shall I write the web server
changes for your host? (Recommended)"
