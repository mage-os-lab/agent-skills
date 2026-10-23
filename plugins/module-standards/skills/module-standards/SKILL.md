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

The workflow is always: **audit first, walk the maintainer through each
improvement with a recommendation, fix what they agree to, then verify.**
Never start rewriting before the maintainer has seen the scorecard: some
findings (a namespace rename, a license change) are decisions for the
maintainer, not for you. Your job is to make those decisions easy.

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
written at the end of step 5), the audit script reports it under
`previous_run`: the area statuses, `decisions_due` (decisions to bring up
again in step 3), `decisions_waiting` (not yet; mention each in one line)
and `declined_blocking_acceptance`. Report progress since then. When
`needs_migration` is true, the file predates structured decisions: turn
its free-text `notes` about declined items into `decisions` entries in
step 5.

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

**Declined, blocks acceptance into the Mage-OS org:** <each entry in
`previous_run.declined_blocking_acceptance`, with its date and reason; omit
this line when there are none>

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

## 3. Walk the maintainer through each improvement

A scorecard says what's wrong; it doesn't help a maintainer decide what to
do about it. Many don't know what PHPStan level 8 buys them or why a
top-level admin menu is a problem. So don't end with "which areas do you
want to tackle?". Turn the findings into concrete questions, each with a
recommended answer, and take the maintainer by the hand from the first
improvement to the last.

Every question:

- **States where they are and where they should be**, with the number when
  there is one: "PHPStan runs at level 2; the Mage-OS standard is level 8."
- **Says what they gain** in one sentence, in merchant or maintainer terms:
  "Level 8 catches calls on values that can be null, the most common cause
  of fatal errors in production."
- **Says what it costs** when that isn't trivial: "Level 8 reports 43
  errors right now; I'd fix them level by level." Take numbers from the
  audit script (`static_analysis`, `tests`, `identity.suggested_*`) and
  from the tools you ran, never estimates.
- **Offers 2 to 4 concrete options**, the recommended one first and marked
  "(Recommended)". Options are actions, not just yes/no: include the
  gentler path for released packages where the reference files allow one,
  and always a way to skip for now.

For example:

```markdown
**PHPStan runs at level 2; the Mage-OS standard is level 8.** Level 8 catches
wrong argument types and calls on possibly-null values before merchants hit
them. It reports 43 errors right now. Shall I raise the level?

1. Raise to 8, fixing errors level by level (Recommended)
2. Raise as far as it stays clean today, baseline the rest
3. Skip for now
```

```markdown
**The package is `acme/module-foo`; Mage-OS modules are `mage-os/module-foo`.**
This is required before the module can move into the Mage-OS org. Because
v1.4.0 is released, existing installs need a `replace` entry to keep working.

1. Rename, with a `replace` entry and an upgrade note in the CHANGELOG (Recommended)
2. Keep the current name for now (blocks acceptance into the Mage-OS org)
```

Each reference file ends with a "Questions to ask" section with the
standard question for its area. Start from those so the wording stays the
same from run to run; fill in the real numbers and names.

**Open with how they want to work**, unless the request was read-only.
Some maintainers want to weigh every change; others want you to get on
with it:

```markdown
**I found 14 improvements: 9 I can just do, 5 that need your decision.**
How do you want to go through them?

1. Do everything I can do on my own in the recommended order, and only
   stop for the 5 decisions (Recommended)
2. Go area by area, asking before each one
3. Only the Required areas for now
```

With option 1, still stop for every needs-decision item and for any new
choice a fix turns up (step 4); only the auto-fixable work runs without a
question. Report what you did after each area so the maintainer can follow
along.

How to run this step:

- **Use a structured question tool when the agent has one** (in Claude
  Code: `AskUserQuestion`, recommended option first with "(Recommended)" in
  its label). Otherwise ask in plain text with numbered options and wait
  for the answer. Never take silence as a yes.
- **Follow the proposed order, a few questions at a time.** At most four
  per round, Required areas before Quality, so the maintainer isn't
  buried. Fix what they said yes to, then ask the next round. Everything
  you ask counts toward the four: the opening "how do you want to work"
  question, and practical ones such as how PHP runs or whether there is a
  store for screenshots. Ask a practical question only in the round that
  needs its answer.
- **Bundle the small stuff.** Trivial auto-fixable items go in one question
  ("Add Dependabot, `SECURITY.md` and `.gitattributes` export rules? Small,
  safe additions.") instead of one question each.
- **Needs-decision items always get their own question**, with the
  trade-off spelled out, including what declining means ("blocks
  acceptance into the Mage-OS org", "settings stay under a top-level menu
  merchants have to hunt for").
- **Bugs found get a question too**: "I found 2 bugs unrelated to the
  standard. Fix them first? (Recommended)"
- **A read-only request stays read-only.** When the maintainer said "just
  audit" or "don't change anything", still present the first round of
  questions (at most four, as above) with the same numbered options, under
  a "Want me to do any of this next?" heading, and say in one line which
  areas the next rounds cover. Don't shorten them to yes/no. Don't start
  fixing until they answer.
- **Respect earlier decisions.** Ask again only what's in
  `previous_run.decisions_due`, and build on what was said last time: "Last
  time you chose to climb PHPStan level by level and stopped at 4. Shall I
  take it to 5?" Decisions in `decisions_waiting` get one line in the
  scorecard ("Rename: declined 2026-09-01, revisit at 2.0"), not a
  question. The exception is a request that contradicts a waiting decision,
  such as moving into the Mage-OS org while the rename is on hold: point out
  the conflict and ask again.
- **When the maintainer declines, ask when to bring it up again**: next
  run, the next major release, or a date ("in 3 months"). Record the answer
  in `decisions` (step 5). A Required item can be declined but not
  silenced: it stays in the scorecard as blocking acceptance into the
  Mage-OS org, whatever they picked.

## 4. Fix, one area at a time

For each improvement the maintainer said yes to:

1. Re-read the reference file's "Fixing" section.
2. Make the changes. Copy templates from `assets/` and adapt them; never
   leave placeholder values in.
3. Run what can be run locally (PHPStan, PHPCS, PHPUnit, `composer validate`,
   `composer audit`). If a tool can't run in this environment, say so instead
   of claiming it passes.
4. When a fix turns up a new choice (a null check that would throw instead
   of silently continuing, a config path existing stores rely on), stop and
   ask it the same way as step 3: current state, the options, your
   recommendation.
5. Summarize what changed and what the maintainer should look at. Unless
   they chose to have you do everything at once, ask about the next
   improvement in the same form: "CI is in place and green.
   Next: PHPStan is at level 2, the standard is 8. Shall I raise it?
   (Recommended)"

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

## 5. Verify and record

When the chosen areas are done, re-run the audit script and re-score. Write
`.mage-os-standards.json` to the module root with the per-area status, the
maintainer's decisions and the date, so a later run can show progress:

```json
{
  "checked_at": "2026-10-15",
  "skill_version": 2,
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
  "decisions": {
    "identity.rename": {
      "choice": "declined",
      "date": "2026-10-15",
      "reason": "Agencies pin acme/module-foo; rename with 2.0",
      "ask_again": "next_major",
      "version_at_decision": "1.4.0"
    },
    "static_analysis.phpstan_level": {
      "choice": "baseline",
      "date": "2026-10-15",
      "ask_again": "next_run",
      "level": 6,
      "baseline_errors": 14
    }
  },
  "notes": ["Integration tests not run locally: no store available"]
}
```

Record a decision whenever the maintainer answers a needs-decision question
or picks a path other than the plain recommendation, using these keys:

| Key | Choices | Declining blocks org acceptance |
|-----|---------|----|
| `identity.rename` | `accepted`, `declined` | yes |
| `license.change` | `accepted`, `declined` | yes |
| `integrity.removal` | `accepted`, `declined` | yes |
| `admin_ux.merge_sections` | `accepted`, `declined` | yes |
| `ci.lowest_version_testing` | `test_floor`, `raise_floor`, `declined` | no |
| `static_analysis.phpstan_level` | `level_8`, `climb`, `baseline`, `declined` | no |
| `tests.behavior_tests` | `accepted`, `declined` | no |
| `security.encrypt_config_values` | `accepted`, `declined` | no |
| `documentation.screenshots` | `playwright`, `placeholders`, `declined` | no |

- `ask_again` is `next_run` (the default), `next_major`, an ISO date, or
  `never`. Store `version_at_decision` (`git.latest_version`) with
  `next_major`, so the script can tell when a new major is out.
- Path decisions carry the numbers the next run compares against: `level`
  and `baseline_errors` for PHPStan, so it can say "the baseline went from
  14 to 9 errors".
- Update a decision when the maintainer revisits it; remove it once the
  item passes.
- `notes` is for anything else worth knowing next time, not for decisions.

Add `.mage-os-standards.json` to the module's `.gitattributes` `export-ignore`
list so it doesn't ship to stores. Finish with the updated scorecard, then
offer the remaining improvements as questions in the step 3 form, so the
maintainer always leaves knowing the recommended next step.

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
