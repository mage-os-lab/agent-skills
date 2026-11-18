# Store security

Check how exposed a Magento or Mage-OS store is, then close the gaps one at
a time, with your approval for every change. Built for merchants and the
developers who run their stores.

```
/plugin install store-security@mage-os
```

## What it does

You ask something like *"is our store secure?"* from the store's root
directory, and the agent:

1. **Audits** the store: runs a bundled script (version, patches, secrets in
   git, unexpected PHP files), checks the version against
   [magento.watch](https://magento.watch), runs `composer audit`, compares
   your extensions with Sansec's [MageVulnDB](https://github.com/sansecio/magevulndb),
   and reads the admin and security settings through `bin/magento`.
2. **Shows a scorecard** of 7 areas, each finding saying what an attacker
   could do with it.
3. **Walks you through each fix** with a recommended answer, like
   *"Two-factor authentication is disabled. Turn it on? (Recommended)"*.
4. **Fixes what you agreed to** and verifies it, then saves the area
   statuses and your decisions to `var/mage-os-security.json` (outside git)
   so the next run shows progress.

What it never does:

- **Print a secret.** Findings say "the crypt key is in commit a1b2c3d",
  never the key.
- **Touch your live site without asking.** The live checks run only on the
  URL you give, only after you say yes: about 25 GET requests, no login
  attempts.
- **Clean up a hack.** If it finds a likely skimmer or backdoor, it stops,
  changes nothing, and helps you hand over to your host or a security
  specialist, because deleting the file destroys the evidence.
- **Commit or push.**

## What it checks

| Area | Level | What it checks |
|---|---|---|
| Version and patches | Critical | Supported version, open security bulletins, isolated patches applied |
| Dependencies | Critical | `composer audit`, abandoned packages, extensions listed in MageVulnDB, `app/code` modules nobody audits |
| Signs of compromise | Critical | Scripts injected in config or CMS blocks, PHP files in `pub/media`, obfuscated code, unknown admin users and integrations |
| Secrets in git | Critical | `env.php`, `auth.json` and API keys in tracked files and the whole history, `.gitignore` |
| Admin | Recommended | 2FA, admin URL, lockout, sessions, passwords, captcha |
| Configuration | Recommended | Production mode, CSP restrict mode, HTTPS, cookies, debug output, guest API access |
| Live site | Recommended, with consent | Exposed `.git/` or `env.php`, document root, admin login exposure, security headers |

The criteria live in [`skills/store-security/references/`](skills/store-security/references/).
Disagree with a rule? Open a pull request against the reference file.

## Example prompts

- *"Is this store secure? Don't change anything."*
- *"Adobe published a security bulletin, are we affected?"*
- *"We think there's a card skimmer on checkout."*
- *"Harden the admin of this shop."*
- *"Check the live site at https://shop.example before our PCI scan."*

## Requirements

- `git` and `python3` (for the bundled scripts)
- Access to `bin/magento`, in whatever form your machine has it (DDEV,
  Warden, Docker Compose...). Without it, the settings and database checks
  are reported as not checked.
- Network access to magento.watch and GitHub for the version and extension
  checks.

## Installation

### Claude Code

```
/plugin marketplace add mage-os-lab/agent-skills
/plugin install store-security@mage-os
```

### Codex, Gemini CLI, Cursor, GitHub Copilot, OpenCode

```bash
npx skills add https://github.com/mage-os-lab/agent-skills/tree/main/plugins/store-security/skills/store-security -g
```

Or copy `skills/store-security` to `~/.agents/skills/`.

### Claude.ai and Claude Desktop

Zip the `skills/store-security` folder, then go to Customize > Skills >
"+" > Create skill > Upload a skill. Code execution must be enabled.

## Evals

`evals/` holds a [plugin eval suite](https://code.claude.com/docs/en/plugin-evals)
that runs the skill against a fixture store with known gaps
(`evals/fixture/acme-store.sh`): a vulnerable version, committed secrets,
2FA off and an inert backdoor in `pub/media`. Every secret in it is fake.

```bash
claude plugin eval . --scaffold --allow-tools Edit Write
```

Like module-standards, the cases don't grant Bash or web access: the agent
audits by reading files, which keeps the evals on what the skill says and
refuses to do.

## Community

Questions or ideas? Join the [Mage-OS Discord](https://mage-os.org/discord-channel/).
