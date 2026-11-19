# Version, patches and dependencies

Most Magento break-ins use a vulnerability that already had a fix. Being one
security release behind is the single biggest risk a store can carry.

## Criteria

**Version and patches (Critical)**
- The installed version (`version.version`, `version.distribution` in the
  audit report) is still supported and has no open security bulletin.
  magento.watch has both, per version:
  ```bash
  curl -s https://magento.watch/api/v1/magento-community/versions   # or mage-os/versions
  curl -s https://magento.watch/api/v1/security-bulletins
  ```
  `data[<version>]` (keys include the patch level, `2.4.7-p3`) gives
  `isEOLVersion`, `eolDate`, `isSecureVersion` and `securitySummary`
  (`status`, `requiredPatches`, `upgradeRequired`). Each bulletin gives
  `severity`, `cves`, `fixedIn` per distribution and `isolatedPatches` with
  the versions they apply to (`appliesTo`).
- Adobe sometimes ships a fix as an **isolated patch** on top of a release,
  not as a new `-pN`. A store on a listed version is fixed only if the patch
  is applied: look for it in `composer_patches` (cweagans/composer-patches),
  or with `vendor/bin/magento-patches status` when
  `version.quality_patches_installed` is true. If you can't tell, report
  "not verified", never "patched".
- Mage-OS ships its fixes in its own releases: check `mage-os/versions` and
  the bulletin's `fixedIn.mage-os`.
- If magento.watch doesn't answer, or doesn't list the installed version
  yet (new releases take a while: Mage-OS 4.0.0 was missing when this was
  written), say so and check by hand: Adobe Security Bulletins, or the
  Mage-OS release notes (https://github.com/mage-os/mageos-magento2/releases).
  Never conclude "up to date" without a source.

**Dependencies (Critical)**
- `composer audit --locked --no-dev` reports no advisory. It reads
  `composer.lock` only, installs nothing, and covers every package with a
  published advisory, extensions included.
- No abandoned package among the store's own requirements
  (`version.abandoned_direct_requirements`): nobody will fix its next
  vulnerability. Abandoned packages pulled in by the core or an extension
  (`abandoned_through_core_or_extensions`, also listed by `composer
  audit`) are not the merchant's to fix: mention the count in one line,
  not as a finding.
- Third-party modules are checked against Sansec's MageVulnDB, which lists
  extensions with known holes that often never got a CVE:
  ```bash
  curl -s https://raw.githubusercontent.com/sansecio/magevulndb/master/magento2-vulnerable-extensions.csv
  ```
  Columns: `Name` (module name, as in `modules.enabled_third_party_modules`),
  `Fixed in`, `Relevant URI`, `Reference`, `Update URL`. Compare `Fixed in`
  with the installed version (`composer.lock`, or the module's
  `composer.json` / `etc/module.xml` for `app/code`).
- Modules in `app/code` (`app_code_modules`) aren't covered by any of the
  above. List them as "not audited" and, for the ones the store owns,
  suggest the `module-standards` skill's security area.

## Fixing

1. **Upgrade within the release line** (2.4.7-p3 to the latest 2.4.7-pN):
   `composer require magento/product-community-edition=<version> --no-update`
   then `composer update "magento/*" -W` (or `mage-os/*`). On a copy or
   staging first, then `bin/magento setup:upgrade`, `setup:di:compile`,
   `setup:static-content:deploy` and a test order. Never run it straight on
   production: it is a deploy.
2. **Isolated patch** when the bulletin offers one for this version and an
   upgrade isn't possible now: add it to `extra.patches` (or the patches
   file) for `magento/magento2-base` or the module it targets, from the URL
   in the bulletin, and `composer install`.
3. **End of life**: no patch will come. The fix is a version upgrade, a
   project of its own: say so, and suggest the `store-upgrade` skill once it
   exists.
4. **Vulnerable dependency**: `composer update <package> -W` to the fixed
   version; if the fix needs a new major, it's a needs-decision upgrade.
5. **Abandoned or vulnerable module with no fix**: removing it is a
   needs-decision item (`composer remove`, `setup:upgrade`, check what
   used it).

## Questions to ask

**Missing security patches** (decision `patches.upgrade`):

> **The store runs Magento 2.4.7-p3, which has 5 open security fixes,
> including one that lets anyone run code on the server without logging in
> (APSB26-153, CVSS 10).** Attackers scan for unpatched stores within days
> of a bulletin.
>
> 1. Upgrade to 2.4.7-p10 on staging, then production (Recommended)
> 2. Apply the isolated patch now, upgrade later
> 3. Skip for now

**Vulnerable dependencies** (decision `dependencies.update`): "composer
audit reports 3 advisories, 1 high, in `acme/legacy-slider` and 2 others.
Update them to the fixed versions? (Recommended)"
