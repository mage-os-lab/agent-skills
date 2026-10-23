# CI

Mage-OS modules use the reusable **check-extension** workflow from
`graycoreio/github-actions-magento2` (planned to move into the Mage-OS
GitHub Actions suite; if that has happened by the time you read this, use
the Mage-OS copy). Docs:
https://github.com/graycoreio/github-actions-magento2/blob/main/docs/workflows/check-extension.md

It installs the module into a real Magento/Mage-OS project across the
supported version matrix and runs:

| Job | What it proves | Default |
|-----|----------------|---------|
| `compile-extension` | `setup:di:compile` works: DI config, constructor types, missing dependencies | on |
| `coding-standard` | Magento PHPCS standard | on |
| `unit-test-extension` | `Test/Unit` passes | on |
| `integration_test` | `Test/Integration` passes against a real database | on |
| `phpstan` | PHPStan using the repo's `phpstan.neon` | **off, opt-in** |

Jobs are toggled in `.github/check-extension.json` (see
`assets/check-extension.json`).

## Criteria

- `.github/workflows/check-extension.yaml` exists, runs on `push` to the main
  branch and on every `pull_request` (no base-branch filter: stacked PRs
  deserve CI too).
- PHPStan is enabled in `.github/check-extension.json`.
- **New package (no git tags)**: the supported-version matrix is the
  contract. Set composer.json constraints to match what it tests and don't
  add a lower floor.
- **Released package (has tags)**: existing users may run older versions
  than the supported-version matrix covers. Propose testing the lowest
  combination composer.json allows (the `*-lowest` jobs in
  `assets/check-extension.yaml`), so the claimed floor is actually verified.
  This is a proposal, not a requirement: the maintainer may prefer to raise
  the floor instead, which is a major version bump.
- `magento_repository` points to `https://repo.mage-os.org/` when testing
  against the Mage-OS project (the default mirror only proxies `magento/*`).
- Workflow hardening (also covered in security.md):
  - Top-level `permissions: contents: read`.
  - Third-party actions pinned to a full commit SHA with the version as a
    comment. Tags can be moved; SHAs can't.
  - No `pull_request_target` with a checkout of the PR head.
- `.github/dependabot.yml` updates both `composer` and `github-actions`
  (see `assets/dependabot.yml`). Dependabot understands SHA-pinned actions and
  bumps the SHA plus the comment.
- `composer audit` runs in CI (see `assets/check-extension.yaml`, job
  `composer-audit`).

## Fixing

1. Copy `assets/check-extension.yaml` to `.github/workflows/` and
   `assets/check-extension.json` to `.github/`. For a new package, delete the
   `compute-lowest-matrix` and `check-extension-lowest` jobs. Replace every
   `__PLACEHOLDER__` token; none may remain.
2. Resolve the current release of each action and pin it. Plain git is
   enough, no GitHub CLI or token needed:
   ```bash
   git ls-remote --tags --sort=-v:refname https://github.com/graycoreio/github-actions-magento2 'v*' | head -4
   ```
   Pick the newest stable tag (skip `-rc`/`-beta`). If a tag has a second
   line ending in `^{}`, it's an annotated tag: use the SHA on that `^{}`
   line, which is the commit. Do the same for `actions/checkout` and
   `shivammathur/setup-php`.
3. For a released package where the maintainer agreed to floor testing, set
   the lowest-version job to the module's actual floor: the oldest Magento
   version its composer.json allows and the lowest PHP version.
   If the floor can't install (dependency conflicts), the constraint in
   composer.json is wrong: raise it there rather than skipping the job.
4. If the module has no integration tests yet, leave the job enabled anyway:
   it passes trivially and starts doing work as soon as tests are added.
   Disabling jobs in the config is for things that genuinely can't run (e.g. a
   module that needs an external service).
5. Replace any older workflows that duplicate these checks (a separate PHPCS
   or PHPUnit workflow). Keep workflows that do something else (releases,
   E2E).
6. Push is up to the maintainer. Tell them CI results are the real proof and
   that the first run may surface compile or install errors that weren't
   visible locally.

## Questions to ask

**Add CI** (auto-fixable):

> **The module has no CI.** check-extension installs it into a real
> Magento/Mage-OS store on every push and pull request and runs compile,
> coding standard, unit, integration and PHPStan checks across the
> supported versions. It's Required, and it makes every later change safe
> to verify.
>
> 1. Add check-extension with PHPStan, `composer audit` and Dependabot (Recommended)
> 2. Skip for now (CI stays failing, which blocks acceptance)

When CI exists but is incomplete, name what's missing: "CI runs, but
PHPStan is off and actions are pinned to tags. Enable PHPStan and pin to
commit SHAs? (Recommended)"

**Version floor** (decision `ci.lowest_version_testing`), released
packages only:

> **composer.json allows Magento 2.4.4 and PHP 8.1, but nothing tests that.**
> Stores on those versions may be running untested code. Either test the
> floor, or raise it to what CI covers (2.4.6, PHP 8.2), which is a major
> version bump.
>
> 1. Add a job that tests the lowest allowed versions (Recommended)
> 2. Raise the floor to the tested versions in the next major
> 3. Leave it for now
