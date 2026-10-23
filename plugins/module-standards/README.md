# Module standards

Audit a Magento or Mage-OS module against the Mage-OS extension standards,
then bring it up to that level, one area at a time. Built for module
maintainers who want their extension to be something merchants and other
developers can rely on, whether or not it lives in the Mage-OS GitHub org.

```
/plugin install module-standards@mage-os
```

## What it does

You ask something like *"get this module up to Mage-OS standards"*, and the
agent:

1. **Audits** the module: runs a bundled audit script, reads the code, and
   runs PHPStan, PHPCS, the unit tests and `composer audit` for real.
2. **Shows a scorecard** of 10 areas, each finding marked *auto-fixable* or
   *needs decision*, plus any real bugs it ran into along the way.
3. **Walks you through each improvement** with a question and a
   recommended answer, like *"PHPStan is at level 2, the standard is 8.
   Shall I raise it?"*, so you know what each change buys you before you
   say yes. Don't want to weigh every change? Pick "do everything you
   can" and it only stops for the decisions that are yours.
4. **Fixes what you agreed to**, one area at a time. Decisions that are
   yours to make (renames, license changes, removing features) stay yours.
5. **Verifies** by re-running the tools and the audit, and saves the result
   to `.mage-os-standards.json` so the next run shows your progress. Your
   decisions are saved too: say "not now, ask again at 2.0" and the next
   run mentions it in one line instead of asking again.

It never commits or pushes. All changes stay in your working tree for you to
review.

## The standard

| Area | Level | What it checks |
|---|---|---|
| Identity | Required | `mage-os/` package name, `MageOS_` namespace, complete composer metadata |
| License | Required | OSL-3.0, AFL-3.0, MIT or BSD-3-Clause; no GPL; third-party code attributed |
| Integrity | Required | No callhome, upsells, advertising, tracking or license checks |
| Admin UX and i18n | Required | Settings under a core tab or the shared Mage-OS tab, no top-level menus, ACL per section, all visible text translatable |
| CI | Required | The [check-extension](https://github.com/graycoreio/github-actions-magento2/blob/main/docs/workflows/check-extension.md) workflow with PHPStan enabled, actions pinned to commit SHAs, `composer audit`, Dependabot |
| Static analysis | Quality | PHPStan level 8 and the Magento coding standard |
| Tests | Quality | Tests for behavior and correctness, integration tests for Magento wiring |
| Security | Quality, some items Required | ACL and CSRF, customer data ownership, full page cache leaks, escaping, SQL, secrets, outbound requests, CSP, open redirects, public forms, `SECURITY.md` |
| Documentation | Quality | A README that says exactly where every setting lives in the admin, compatibility, getting started, screenshots, CHANGELOG |
| Hygiene | Quality | Lean composer package, declarative schema |

New packages (no git tags yet) get the full bar straight away. Released
packages get a gentler path: PHPStan can climb level by level with a
baseline that only shrinks, and testing against the lowest supported
Magento version is proposed rather than required.

The full criteria live in [`skills/module-standards/references/`](skills/module-standards/references/).
They are the standard, written down. Disagree with a rule? Open a pull
request against the reference file.

## Example prompts

- *"Get this module up to Mage-OS standards."*
- *"We want to move this module into the mage-os org. Is it ready? Don't change anything."*
- *"The README is thin. Write a proper one that explains where every setting lives in the admin."*
- *"Add PHPStan, PHPCS and CI to this module, Mage-OS style."*
- *"Harden the security of this module, it stores API keys."*

## Requirements

- `git` and `python3` (for the bundled scripts)
- PHP and Composer, in whatever form your machine has them. The agent looks
  for DDEV, Warden, Docker Compose or a Makefile and uses that, and falls
  back to the official Composer Docker image when there's no PHP on the host.
- Optional: a running store with the module enabled, for README screenshots
  (see below)

## Screenshots

If you have a store running with the module enabled, the agent can capture
admin screenshots for the README with Playwright. It asks for the store
details and reads credentials from environment variables, never from files
in the repository:

```bash
export MAGENTO_BASE_URL=https://your-store.test
export MAGENTO_ADMIN_PATH=admin
export MAGENTO_ADMIN_USER=...
export MAGENTO_ADMIN_PASSWORD=...
```

Without a store, the README gets clearly marked placeholders that say which
screenshot to take.

## Installation

### Claude Code

```
/plugin marketplace add mage-os-lab/agent-skills
/plugin install module-standards@mage-os
```

To update, run `/plugin marketplace update mage-os`, or turn on auto-update
under `/plugin` > Marketplaces > mage-os.

### Codex, Gemini CLI, Cursor, GitHub Copilot, OpenCode

The skill follows the open [Agent Skills](https://agentskills.io) standard.
The quickest way is the cross-tool installer:

```bash
npx skills add https://github.com/mage-os-lab/agent-skills/tree/main/plugins/module-standards/skills/module-standards -g
```

Or copy the skill folder by hand. All of these tools read
`~/.agents/skills/`, so one copy covers them all:

```bash
git clone https://github.com/mage-os-lab/agent-skills.git
mkdir -p ~/.agents/skills
cp -R agent-skills/plugins/module-standards/skills/module-standards ~/.agents/skills/
```

To install for a single project instead, copy it to `.agents/skills/` in
that project. To update, pull the repository and copy the folder again.

### Claude.ai and Claude Desktop

Zip the `skills/module-standards` folder, then go to Customize > Skills >
"+" > Create skill > Upload a skill. Code execution must be enabled.

## Evals

`evals/` holds a [plugin eval suite](https://code.claude.com/docs/en/plugin-evals)
that runs the skill against a fixture module with known gaps
(`evals/fixture/acme-gift-wrap.sh`). Run it after changing the skill
(needs Claude Code 2.1.269 or later):

```bash
claude plugin eval . --scaffold --allow-tools Edit Write
```

`--scaffold` runs the fixture script; without it the cases run against an
empty workspace. The cases deliberately don't grant Bash, so they run on
machines whose SSH setup the Bash sandbox can't isolate. The agent audits
by reading the code instead of running `audit.py`, which keeps the evals
focused on how the skill talks to the maintainer.

## Community

Questions, ideas, or want to show off what you built? Join the
[Mage-OS Discord](https://mage-os.org/discord-channel/).
