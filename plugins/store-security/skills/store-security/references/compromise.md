# Signs of compromise

On Magento, a break-in usually ends in a payment skimmer: JavaScript that
copies card details on checkout and sends them elsewhere. The usual places
are a few config fields and CMS blocks, because they render on every page
and survive deploys. Backdoors (a PHP file that runs whatever it's sent) and
extra admin accounts keep the attacker in after a patch.

## Criteria (Critical)

**Injected scripts**, read with `SELECT` only (through `bin/magento`'s
database, `n98-magerun2 db:query`, or the store's MySQL client):

```sql
SELECT path, scope, scope_id, value FROM core_config_data
  WHERE path IN ('design/head/includes', 'design/footer/absolute_footer');
SELECT block_id, identifier, is_active FROM cms_block
 WHERE content REGEXP '<script|javascript:|onerror=|atob\\(|eval\\(';
SELECT page_id, identifier, is_active FROM cms_page
 WHERE content REGEXP '<script|javascript:|onerror=|atob\\(|eval\\(';
```

Any `<script>` loading from a domain the store doesn't know, or inline code
with `atob`, `eval`, `String.fromCharCode` or a WebSocket, is a likely
skimmer. Ask the maintainer whether they recognize each external domain
(tag managers and analytics are common and fine) before calling it one.

**Backdoors**
- No PHP file under `pub/media` or `pub/static`
  (`unexpected_php.media_or_static_php`): Magento never puts one there.
- No PHP file at the root of `pub/` beyond `index.php`, `get.php`,
  `static.php`, `health_check.php` and `cron.php`
  (`unexpected_php.pub_root_php`).
- No obfuscated code (`obfuscated_code`: `eval(base64_decode(...))`,
  `$_POST['x'](...)`, ...). Read each hit: some old extensions obfuscate
  their license check, which is a vendor problem, not a break-in.
- Core files match their package: `composer status -v` lists modified
  files in `vendor/` (works for packages installed from source; for dist
  installs, compare against a fresh `composer install` in a copy).

**Unknown access**
- Every admin user is known to the maintainer:
  `SELECT username, is_active, created, logdate FROM admin_user;` (no
  password or email column). An account nobody recognizes, or one created
  recently with no ticket behind it, is a sign of compromise.
- Every integration and API token is known:
  `SELECT name, status, created_at FROM integration;`

A dedicated scanner sees far more patterns than these checks: Sansec
eComscan (commercial) or Adobe's Security Scan Tool (free with an Adobe
account). Recommend one when anything above looks wrong.

## When something is found

Stop the audit and say plainly what was found and where, without opening
the attacker's payload beyond what's needed to describe it. Then:

1. **Don't delete or "clean" anything.** The file, the config value and the
   logs are evidence; removing them also hides how the attacker got in,
   so they come back.
2. **Preserve**: suggest a copy of the code (`tar` of the store root),
   a database dump and the web server logs, kept off the server.
3. **Hand over** to incident response: the hosting provider's security
   team or a Magento security specialist. Card data may be involved, so the
   payment provider must be told; that's the merchant's obligation, not
   yours to judge.
4. Once they're in charge, the rest of this audit (patches, secrets
   rotation) is part of the recovery: offer to finish it.

## Questions to ask

**Likely skimmer or backdoor** (no decision key: always this question):

> **`pub/media/catalog/product/cache/thumb.php` is a PHP file with
> obfuscated code in a folder where Magento never puts PHP.** It is very
> likely a backdoor. I haven't touched it. Cleaning it now would destroy
> the evidence and leave the way in open.
>
> 1. Stop here; I'll write a short incident summary for your host or
>    security specialist (Recommended)
> 2. It's known and harmless (say what it is), continue the audit

**Unknown admin user**: "The admin user `support2` was created on
2026-11-02 and logged in yesterday. Do you know who uses it?" with "I don't
know it: treat as compromise (Recommended)" and "It's ours, continue".
