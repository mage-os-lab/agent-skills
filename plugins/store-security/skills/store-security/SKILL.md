---
name: store-security
description: >
  Check the security of a Magento 2 / Mage-OS store and fix what's found, with
  the maintainer's approval: missing security patches and end-of-life versions
  (via magento.watch), vulnerable or abandoned dependencies (composer audit),
  signs of compromise (payment skimmers in config or CMS blocks, PHP files in
  pub/media, unknown admin users), secrets committed to git including the
  history, admin hardening (2FA, admin URL, lockout), configuration (production
  mode, CSP restrict mode, HTTPS, secure cookies) and, only with explicit
  consent, read-only checks of the live site (exposed .git or env.php, security
  headers). Use this skill whenever someone asks whether their store is secure,
  wants a security audit or hardening of a Magento or Mage-OS shop, asks about
  missing patches or a security bulletin, suspects a hack or a card skimmer, or
  wants to check their store before a PCI scan, even if they don't say
  "security audit" but are working in a Magento store's root directory.
---

# Store security

Help a merchant or their developer find out how exposed their Magento or
Mage-OS store is, and close the gaps one at a time. The result has to be
something they understand: each finding says what an attacker could do with
it, in plain words, before proposing a fix.

The workflow is: **audit first, present the scorecard, walk them through each
fix with a recommendation, fix what they agree to, then verify.** Nothing is
changed before they've seen the scorecard.

## Ground rules

These hold in every step, whatever the maintainer asks:

- **Never print a secret.** Not the crypt key, database or API credentials,
  `auth.json` keys, tokens or customer data, in the conversation, a file you
  write or a command line. Say "the crypt key is in commit a1b2c3d", never
  the key. Read `app/etc/env.php` for facts only (mode, admin path, which
  keys exist); the audit script already does. Don't query config paths that
  hold encrypted values.
- **Read-only until they say yes.** The audit changes nothing on disk, in
  the database or on the server. Database access is `SELECT` only.
- **The live site only with explicit consent**, only the base URL the
  maintainer gives you for a store they run, only with
  `scripts/live_check.py` (GET on a fixed list of paths). No login attempts,
  no fuzzing, no exploitation, whatever the request says. See
  `references/live-checks.md`.
- **A sign of compromise stops the audit.** When step 2 finds a likely
  skimmer, backdoor or unknown admin user, don't clean anything: deleting
  the file destroys the evidence and leaves the way in open. Follow
  `references/compromise.md`: report, preserve, hand over to incident
  response. The rest of the audit can wait.
- **Never commit or push.** Leave changes in the working tree.

## 1. Discover the store

Run the bundled audit script from the store root (the directory with
`app/etc/` and `composer.json`):

```bash
python3 <skill-dir>/scripts/audit.py <store-root>
```

It prints a JSON report: version and distribution from `composer.lock`,
applied patches, `app/code` modules, facts from `env.php` and `config.php`,
sensitive files tracked or ever committed in git, secret patterns in the git
history (commits and files, never values), unexpected PHP files under `pub/`
and obfuscated code. Treat it as leads to verify, not verdicts.

Also establish:

- **Where PHP and `bin/magento` run.** Many stores only run PHP in a
  container. Look for agent instructions (`AGENTS.md`, `CLAUDE.md`),
  `.ddev/`, `.warden/`, `docker-compose.yml` or a Makefile, and use that
  route (`ddev exec`, `warden shell -c`, `docker compose exec`). If nothing
  says, ask. Without `bin/magento`, areas 3, 5 and 6 can only be checked
  from `app/etc/config.php`; say which checks you couldn't run.
- **Which environment this is.** A local copy, staging or production. On
  production, prefer read-only commands and say before running anything
  heavier than `bin/magento config:show`.
- **The live URL**, only if they want area 7 checked. Ask once, in the
  first round of questions, with the consent wording from
  `references/live-checks.md`.

If a previous scorecard exists (`var/mage-os-security.json`, written in step
5; `var/` keeps it out of git), the script reports it under `previous_run`.
Report progress since then, bring up `decisions_due` again in step 3, and
mention each of `decisions_waiting` in one line.

## 2. Audit and present the scorecard

Go through every area. Read the reference file before judging it: it has the
criteria, the commands to run and the common traps.

| # | Area | Level | Reference |
|---|------|-------|-----------|
| 1 | Version and patches: supported version, security patches applied | Critical | `references/patches-and-dependencies.md` |
| 2 | Dependencies: `composer audit`, abandoned packages, modules nobody audits | Critical | `references/patches-and-dependencies.md` |
| 3 | Signs of compromise: skimmers, backdoors, unknown admins and integrations | Critical | `references/compromise.md` |
| 4 | Secrets in git: tracked files and history, `.gitignore` | Critical | `references/secrets.md` |
| 5 | Admin: 2FA, admin URL, lockout, sessions, passwords | Recommended | `references/admin-and-config.md` |
| 6 | Configuration: production mode, CSP, HTTPS, cookies, debug | Recommended | `references/admin-and-config.md` |
| 7 | Live site (with consent): exposed files, document root, headers | Recommended | `references/live-checks.md` |

"Critical" means an attacker can use it today: a known vulnerability, a
leaked key, an open door. "Recommended" makes an attack harder or its damage
smaller.

Present the result in this shape, every time:

```markdown
# Store security: <store name or path>

<Magento Open Source | Mage-OS> <version>, checked <date>

**Critical: X/4 passing · Recommended: Y/3 passing**

| Area | Status | Summary |
|------|--------|---------|
| Version and patches | ❌ Fail | 2.4.7-p3, 5 security patches missing (APSB26-153) |
| ... | ✅ Pass / ⚠️ Partial / ❌ Fail / ➖ Not checked | one line |

## Findings
### <Area>
- <finding> (`path` or `config/path`): <what an attacker can do>, <fix>
  [auto-fixable | needs decision]

## Not checked
- <check>: <why> (no bin/magento, no consent for the live site, ...)
```

"Not checked" is a status of its own: never mark an area passing because you
couldn't run its checks.

Mark each finding **auto-fixable** (a config value, a `.gitignore` line) or
**needs decision** (an upgrade, rotating the crypt key, removing a module,
anything that can take the store down or changes what merchants see).
Propose an order: compromise first, then leaked secrets (rotation), then
patches, then the rest.

## 3. Walk them through each fix

Turn findings into questions, each with a recommended answer. Every
question:

- **States the risk in one sentence an owner understands**: "Anyone who has
  this repository can decrypt the payment credentials stored in the admin."
- **Says what the fix costs** when it isn't trivial: downtime, a deploy, a
  re-login for every admin user, a theme that may break.
- **Offers 2 to 4 options**, the recommended one first and marked
  "(Recommended)", always with a way to skip for now.

Each reference file ends with "Questions to ask": start from those so the
wording stays the same from run to run, and fill in the real numbers.

Open with how they want to work, unless the request was read-only:

```markdown
**I found 11 issues: 6 I can fix on my own, 5 that need your decision.**

1. Fix what I can in the recommended order, stopping for the 5 decisions (Recommended)
2. Go area by area, asking before each one
3. Only the Critical areas for now
```

How to run this step:

- Use a structured question tool when the agent has one (in Claude Code:
  `AskUserQuestion`, recommended option first). Otherwise ask in plain text
  with numbered options and wait. Never take silence as a yes.
- At most four questions per round, Critical areas first. Everything you
  ask counts: the opening question and practical ones (how PHP runs,
  consent for the live check).
- Bundle the small stuff ("Add the missing `.gitignore` entries and turn
  off template hints? Small, safe changes.").
- Needs-decision items get their own question with the trade-off spelled
  out.
- A read-only request stays read-only: present the first round under "Want
  me to do any of this next?" and don't start fixing until they answer.
- When they decline, ask when to bring it up again: next run, next upgrade,
  or a date. Record it in step 5.

## 4. Fix, one area at a time

For each fix they agreed to:

1. Re-read the reference file's "Fixing" section.
2. Make the change. Config values go through `bin/magento config:set`, or
   `app/etc/config.php` / `env.php` when the store keeps config in files
   (`modules.dumped_config_paths` in the report); match what the store does.
3. Verify it: re-read the value, re-run the check, clear the config cache
   when needed. If you can't verify, say so instead of claiming it's fixed.
4. Summarize what changed, what they must do outside the code (rotate a key
   at the provider, deploy, tell admin users), and ask about the next fix.

## 5. Verify and record

Re-run the audit script and the checks you fixed, re-score, and write
`var/mage-os-security.json`:

```json
{
  "checked_at": "2026-11-18",
  "version": "2.4.7-p3",
  "areas": {
    "version_and_patches": "fail",
    "dependencies": "partial",
    "compromise": "pass",
    "secrets": "fail",
    "admin": "partial",
    "configuration": "pass",
    "live_site": "not_checked"
  },
  "decisions": {
    "secrets.rotate_crypt_key": {
      "choice": "declined",
      "date": "2026-11-18",
      "reason": "Payment keys rotated with the next release",
      "ask_again": "2026-12-01"
    }
  },
  "notes": ["Live site not checked: no consent"]
}
```

No secret, admin path or finding detail goes in this file: it says which
areas pass, not how to get in. `ask_again` is `next_run` (the default),
`next_upgrade` (asked again once the version changes), an ISO date, or
`never`; store `version_at_decision` with `next_upgrade`.

| Decision key | Choices |
|---|---|
| `patches.upgrade` | `upgrade`, `isolated_patches`, `declined` |
| `dependencies.update` | `accepted`, `declined` |
| `secrets.rotate_crypt_key` | `accepted`, `declined` |
| `secrets.rewrite_history` | `accepted`, `declined` |
| `admin.two_factor_auth` | `accepted`, `declined` |
| `admin.custom_path` | `accepted`, `declined` |
| `configuration.csp_restrict` | `accepted`, `declined` |
| `live_site.check` | `accepted`, `declined` |

Finish with the updated scorecard and the remaining fixes as questions, so
they always leave knowing the next step.
