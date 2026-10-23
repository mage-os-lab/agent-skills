# Documentation

The README is for a merchant or agency developer who just installed the
module and wants it working. "composer require + module:enable" is where the
README starts, not where it ends. The useful part is: "Go to Stores >
Configuration > Sales > Checkout > Gift Wrapping, set Enabled to Yes, fill in
Price to show the option on the cart page."

## Criteria

- **README.md** with, in this order:
  1. One-paragraph description: what problem it solves, for whom.
  2. Compatibility: Mage-OS and Magento Open Source version range, PHP range,
     Luma / Hyvä / headless (GraphQL) support. Say "not tested" rather than
     guessing.
  3. Installation (composer, enable, setup:upgrade).
  4. **Configuration**: every setting, with the exact admin path, what it
     does, its default, and its scope. Grouped like the admin groups them.
  5. **Getting started**: a short walkthrough from fresh install to seeing
     the feature work, with screenshots of the admin config and the
     result in the frontend or admin.
  6. Where the feature shows up: which pages, grids, emails, API endpoints.
  7. Troubleshooting: the two or three things that actually go wrong
     (cache, cron not running, missing API key).
  8. Links: `docs/` for detail, CHANGELOG, SECURITY.md, license.
- **docs/** for anything longer: developer extension points (events,
  plugins, interfaces), API/GraphQL reference, detailed configuration.
- **CHANGELOG.md** in Keep a Changelog format, versions following semver:
  breaking changes (renames, removed config, raised PHP floor) are major.
- **SECURITY.md** (see security.md).
- No marketing language, no links to paid extensions.

## Deriving the configuration section

Don't write admin paths from memory. Generate them from the module's XML:

```bash
python3 <skill-dir>/scripts/config_map.py <module-root>
```

It reads `etc/adminhtml/system.xml` (including `<include>` partials),
`etc/config.xml` defaults, `etc/adminhtml/menu.xml` and `etc/acl.xml` and
prints a Markdown outline: the breadcrumb (Stores > Configuration > Tab >
Section > Group > Field), field type, source model, default, scope, and
`depends` conditions. Labels for core tabs and common core sections are
known; for anything defined in another module it prints the ID and marks it,
and you look up the label in that module's system.xml (in `vendor/`) if
available.

Turn the outline into prose. A table per group works well:

```markdown
### Stores > Configuration > Sales > Checkout > Gift Wrapping

| Setting | Default | Scope | What it does |
|---------|---------|-------|--------------|
| Enabled | No | Website | Shows the gift wrap option in the cart. |
| Price | 2.50 | Website | Added to the order total when chosen. Only shown when Enabled is Yes. |
```

Then read the code that consumes each config path (grep for the path or the
config provider class) to describe what the setting really does, including
side effects ("also adds a line to the order confirmation email"). The XML
comment is often outdated; the code is the truth.

## Screenshots

Screenshots go in `docs/images/` and are referenced from the README with
relative paths. `docs/` is export-ignored, so they don't ship in the composer
package; GitHub and Packagist still render them.

If the maintainer gave access to a running store with the module enabled
(step 1 of the skill), capture them with Playwright. Use whatever way of
running Playwright fits the maintainer's setup (their project may already
have it; otherwise `npx playwright` works). `assets/screenshots.spec.ts` is a
starting point: it logs into the admin, opens each config section, expands
the module's groups and takes a screenshot; add frontend pages where the
feature is visible.

- Credentials come from environment variables (`MAGENTO_ADMIN_USER`,
  `MAGENTO_ADMIN_PASSWORD`, `MAGENTO_BASE_URL`), never hard-coded or
  committed. The admin may have 2FA; if so, ask the maintainer how they want
  to handle it (a test user, or disabling `Magento_TwoFactorAuth` on their
  dev store) rather than working around it yourself.
- Use a clean store: no real customer data in screenshots.
- Take screenshots at a fixed viewport (1440x900) and crop to the relevant
  element so they stay readable on GitHub.
- Look at every screenshot you capture before referencing it. A login page
  or an error page captured by mistake is worse than no screenshot.

If no store is available, leave clearly marked placeholders and tell the
maintainer which screenshots to take:

```markdown
![Gift Wrapping configuration](docs/images/config-gift-wrapping.png)
<!-- TODO screenshot: Stores > Configuration > Sales > Checkout > Gift Wrapping, group expanded -->
```

## Fixing

1. Run `config_map.py`, read consumer code, draft the Configuration section.
2. Draft the rest of the README from the code (controllers, layout, plugins,
   GraphQL schema) and the existing README. Keep accurate content the
   maintainer wrote; rewrite only what's wrong or missing.
3. Capture screenshots or leave placeholders.
4. Create or update CHANGELOG.md with an "Unreleased" section listing the
   changes made in this session.
5. Ask the maintainer to read the Getting started section critically: it's
   the part most likely to contain a wrong assumption about how the feature
   behaves.

## Questions to ask

**README** (auto-fixable, but the maintainer should know the scope):

> **The README is two lines and doesn't say where the settings are.** A
> merchant who just installed the module can't get it working from it. I'd
> write it from the code: every setting with its exact admin path, default
> and scope, a getting-started walkthrough, and troubleshooting.
>
> 1. Write the full README, plus CHANGELOG.md (Recommended)
> 2. Only the Configuration section for now
> 3. Skip for now

**Screenshots** (decision `documentation.screenshots`):

> **Screenshots make the README much easier to follow.** I can capture them
> with Playwright if you have a store running with the module enabled.
>
> 1. Yes, here's the admin URL and credentials as environment variables (Recommended)
> 2. Leave marked placeholders, I'll take them myself
> 3. No screenshots
