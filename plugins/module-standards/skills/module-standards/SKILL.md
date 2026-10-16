---
name: module-standards
description: >
  Audit a Magento 2 / Mage-OS module against the Mage-OS extension standards and
  bring it up to that level, area by area: identity (mage-os/ package, MageOS_
  namespace), license, CI via the check-extension workflow, PHPStan level 8 and
  Magento PHPCS, behavior-focused tests, admin UX (core or shared Mage-OS
  config tabs, no top-level menus), no callhome or upsells, security, and documentation with a
  README that explains exactly where settings live in the admin, including
  screenshots. Use this skill whenever a maintainer wants to get a module "up to
  Mage-OS standards", prepare a module for the mage-os or mage-os-lab GitHub
  org, check whether an extension is "ready" or "good enough" for Mage-OS, add
  quality tooling (PHPStan, PHPCS, GitHub Actions, check-extension) to a
  Magento module, harden a module's security posture, or write proper module
  docs, even if they don't mention Mage-OS by name but are working on a
  Magento 2 module repository.
---

# Mage-OS module standards

Help a module maintainer get their Magento 2 module to the Mage-OS quality bar.
The point is raising the overall quality of extensions under Mage-OS, so the
result has to be something the maintainer understands and can keep up, not a
pile of generated files they never read.

The workflow is always: **audit first, then fix one area at a time with the
maintainer's go-ahead, then verify.** Never start rewriting before the
maintainer has seen the scorecard: some findings (a namespace rename, a
license change) are decisions for the maintainer, not for you.

## 1. Discover the module

Run the bundled audit script from the module root. It collects mechanical
signals (composer metadata, namespace, license, presence of tooling, risky
code patterns) so you don't spend turns grepping by hand:

```bash
python3 <skill-dir>/scripts/audit.py <module-root>
```

It prints a JSON report. Treat its findings as leads, not verdicts: a `curl_`
hit may be a legitimate payment API call, a missing `Test/` directory may be
fine for a module that is pure layout XML. Read the flagged files before
judging.

Also establish:

- **Supported versions**: `require.php` and `magento/framework` (or
  `mage-os/framework`) constraints in composer.json. Everything you add must
  work on the *lowest* version allowed. If there is no constraint, ask.
- **Existing tooling**: what the repo already runs (Makefile, composer
  scripts, CI). Extend what is there instead of replacing it.
- **Where PHP and Composer run**: many Magento developers only have PHP
  inside a container. Before running anything, look for how this machine
  runs PHP: agent instructions (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`),
  `.ddev/`, `.warden/`, `docker-compose.yml`, a Makefile, or the same in a
  parent project when the module sits in `app/code/` or `vendor/`. Then use
  that route (`ddev exec`, `warden shell -c`, `docker compose exec`, ...).
  If there's none and the host has no usable `php`/`composer`, the official
  Composer image works for static analysis:
  `docker run --rm -v "$PWD":/app -w /app composer:2 composer install --ignore-platform-reqs`
  (Magento's PHP extensions aren't needed to analyse code). If nothing
  works, ask the maintainer how they run PHP rather than guessing.
- **New or released**: the audit script reports `git.tags`. A package with
  no tags is **new**: apply the full bar straight away (PHPStan level 8, the
  supported-version CI matrix, no baseline). A package with tags has users
  depending on it: renames and config path changes need migration care,
  PHPStan may climb with a shrinking baseline, and you propose testing a
  lower version floor. The reference files spell out both paths.
- **A running store** (for screenshots and smoke testing): ask once whether
  there is a Magento/Mage-OS install with this module enabled, its admin URL
  and how to get credentials. Don't assume any particular local environment;
  maintainers use all kinds of setups.

**Run the real tools, even for a read-only audit.** PHPStan, PHPCS, PHPUnit
and `composer audit` findings are far more convincing than "configured, not
verified". If the module has no `vendor/`, copy it to a temporary directory,
`composer install` there (time-box it to a few minutes), run the tools, and
delete the copy. That way "don't change anything" is still honored.

If a previous scorecard exists (`.mage-os-standards.json` in the module root,
written at the end of step 4), load it and report progress since then.

## 2. Audit and present the scorecard

Go through every area below. For each one, read the matching reference file
before judging it; they contain the actual criteria and the common traps.

| # | Area | Level | Reference |
|---|------|-------|-----------|
| 1 | Identity: package name, namespace, composer metadata | Required | `references/identity-and-license.md` |
| 2 | License and third-party attribution | Required | `references/identity-and-license.md` |
| 3 | Integrity: no callhome, ads, upsells, tracking | Required | `references/admin-ux-and-integrity.md` |
| 4 | Admin UX and i18n: fits the native admin (core tabs or the shared Mage-OS tab), config in one place, all text translatable | Required | `references/admin-ux-and-integrity.md` |
| 5 | CI: check-extension workflow | Required | `references/ci.md` |
| 6 | Static analysis: PHPStan level 8, Magento PHPCS | Quality | `references/static-analysis.md` |
| 7 | Tests: behavior and correctness | Quality | `references/testing.md` |
| 8 | Security | Quality (some items Required) | `references/security.md` |
| 9 | Documentation: README, docs/, CHANGELOG, semver | Quality | `references/documentation.md` |
| 10 | Maintenance hygiene: package contents, Dependabot, schema | Quality | `references/security.md`, `references/ci.md` |

"Required" items are what Mage-OS needs before accepting a module into the
org. "Quality" items are the bar we want every module to reach.

Present the result in this format so maintainers get the same shape every
time:

```markdown
# Mage-OS standards: <package name>

**Required: X/5 passing · Quality: Y/5 passing**

| Area | Status | Summary |
|------|--------|---------|
| Identity | ❌ Fail | Package is `acme/module-foo`, namespace `Acme_Foo` |
| ...  | ✅ Pass / ⚠️ Partial / ❌ Fail / ➖ N/A | one line |

## Findings
### <Area>
- <finding> (`path/to/file.php:42`): <why it matters>, <proposed fix>
  [auto-fixable | needs decision]

## Proposed order
1. <area>: <one line on what you'll do>
...
```

While reading code for the audit, report real bugs you run into even when
they don't belong to a standards area: a DI preference pointing at a class
that doesn't implement the interface, escaping that is a no-op, a feature
setting that nothing reads. Maintainers value these more than any checklist
item. List them in a separate "Bugs found" section.

Mark each finding as **auto-fixable** (you can just do it) or **needs
decision** (rename, license change, removing a feature, moving config paths
that existing stores rely on). Propose an order: tooling first (CI, PHPStan,
PHPCS), because it makes every later change safer to verify; renames before
docs, because docs reference the names; docs last, because they describe the
end state.

Then ask which areas to tackle now. A maintainer may want to do only CI today;
that is fine.

## 3. Fix, one area at a time

For each area the maintainer picks:

1. Re-read the reference file's "Fixing" section.
2. Make the changes. Copy templates from `assets/` and adapt them; never
   leave placeholder values in.
3. Run what can be run locally (PHPStan, PHPCS, PHPUnit, `composer validate`,
   `composer audit`). If a tool can't run in this environment, say so instead
   of claiming it passes.
4. Summarize what changed and what the maintainer should look at, then move
   to the next area only when they say so.

Some ground rules that apply everywhere:

- **Fix code, not configuration.** Don't lower a PHPStan level, add
  `ignoreErrors`, or exclude a PHPCS sniff to get green. If something
  genuinely can't be fixed (a false positive, a framework limitation), add a
  narrow exclusion with a comment explaining why, and list it in the summary.
- **Stay within the module's PHP floor.** No PHP 8.2 syntax in a module that
  allows 8.1.
- **Don't change behavior while tidying.** Static-analysis fixes, renames and
  doc work should not alter what the module does for merchants. If a fix
  would, flag it.
- **Respect the existing style.** Match the module's conventions over your
  preferences.
- **Never commit or push** unless the maintainer asks. Leave changes in the
  working tree.

## 4. Verify and record

When the chosen areas are done, re-run the audit script and re-score. Write
`.mage-os-standards.json` to the module root with the per-area status and the
date, so a later run can show progress:

```json
{
  "checked_at": "2026-10-15",
  "skill_version": 1,
  "areas": {
    "identity": "pass",
    "license": "pass",
    "integrity": "pass",
    "admin_ux": "partial",
    "ci": "pass",
    "static_analysis": "partial",
    "tests": "fail",
    "security": "partial",
    "documentation": "fail",
    "hygiene": "pass"
  },
  "notes": ["PHPStan at level 6, baseline of 14 errors"]
}
```

Add `.mage-os-standards.json` to the module's `.gitattributes` `export-ignore`
list so it doesn't ship to stores. Finish with the updated scorecard and the
next steps that remain.

End every run that changed something with the notes below, each exactly as
a blockquote, after a horizontal rule so they stand apart from the technical
summary. Whenever Discord is mentioned, link it to
https://mage-os.org/discord-channel/ so people who aren't on it yet can join.

Always:

```markdown
---

> 📣 **Want to promote this package or release?** Leave a note about anything
> noteworthy in the **#marketing-content** channel on the
> [Mage-OS Discord](https://mage-os.org/discord-channel/).
```

Also, when the module doesn't live in the mage-os-lab or mage-os GitHub org
yet (the audit script's `git.is_in_mage_os_org` is false or unknown):

```markdown
> 📦 **Need a GitHub repository for this module?** Ask in the **#tech**
> channel on the [Mage-OS Discord](https://mage-os.org/discord-channel/).
```
