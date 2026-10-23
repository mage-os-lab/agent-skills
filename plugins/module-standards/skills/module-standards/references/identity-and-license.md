# Identity and license

## Criteria

**Package and namespace**
- composer.json `name` is `mage-os/module-<name>` (lowercase, hyphenated).
  Not `mage-os-lab/...`: the lab is a GitHub org for incubation, not a
  package vendor.
- PHP namespace is `MageOS\<ModuleName>`, Magento module name is
  `MageOS_<ModuleName>` in `etc/module.xml` and `registration.php`.
- `type` is `magento2-module`.
- `description` is a real sentence about what the module does for a merchant.
- `autoload` has `files: ["registration.php"]` and a PSR-4 mapping that
  matches the namespace.
- No `version` field in composer.json: versions come from git tags. A
  hard-coded version drifts and breaks Packagist.
- `require` lists what the code actually uses (`magento/framework`,
  `magento/module-catalog`, ...) with constraints that match the versions CI
  tests. Missing requirements show up as compile failures in check-extension;
  over-broad ones (`*`) hide incompatibilities.
- `require.php` is set and matches the lowest PHP version CI tests.
- `etc/module.xml` `<sequence>` lists the modules this one depends on at
  load time.

**License**
- One of OSL-3.0, AFL-3.0, MIT or BSD-3-Clause. OSL/AFL are preferred because
  they match Magento core; MIT is fine. GPL (any version) cannot be accepted:
  it is incompatible with OSL-licensed Magento code.
- A `LICENSE` (or `LICENSE.txt`) file whose text matches the composer.json
  `license` SPDX identifier.
- No file headers that contradict the license ("All Rights Reserved",
  "proprietary", a different license name). Grep templates, JS and CSS too,
  not just PHP.
- Third-party code copied into the module (vendored libraries, snippets from
  Stack Overflow, JS libraries in `view/*/web`) is attributed: original
  license kept next to the code and mentioned in the README or a `NOTICE`
  file. Check `view/*/web/js` for minified libraries without headers.
- Dependencies pulled in through composer have compatible licenses. Run
  `composer licenses --no-dev` if a vendor dir is available and flag GPL or
  unknown licenses.

## Fixing

**Renaming to mage-os / MageOS_ is a breaking change** for anyone already
running the module. Always mark it "needs decision" and explain the impact
before touching it. What changes:

- ACL resource IDs (`Acme_Foo::config` becomes `MageOS_Foo::config`): admin
  roles that had access lose it until re-granted.
- `setup_module` row: the old module name stays in the table; the new one is
  treated as a fresh install, so data patches run again. Make sure patches
  are idempotent, or add a data patch that checks for the old module's
  records.
- Layout handles, template references (`Acme_Foo::path.phtml`), RequireJS
  paths (`Acme_Foo/js/...`), email template IDs, cron group names, and
  `db_schema_whitelist.json` all embed the module name.
- Database table names and config paths (`section/group/field`) do **not**
  contain the module name and should stay unchanged, so merchants keep their
  settings. Don't rename these as part of a namespace move.

Do the rename with a scripted search-and-replace over PHP, XML, phtml, JS,
CSS/LESS and JSON, then grep for leftovers of the old vendor in any case
(`acme`, `Acme`, `ACME`). Add to composer.json:

```json
"replace": { "acme/module-foo": "*" }
```

so a store can't end up with both packages installed. This requires a major
version bump and a CHANGELOG entry with migration notes (re-grant ACL, clear
generated code and static content).

**License**: changing the license needs consent from every copyright holder.
If the module has outside contributors, flag it and stop; that's a
conversation, not a code change. If the maintainer is the sole author, copy
the full license text into `LICENSE` and update the composer.json identifier.
Don't paste license headers into every file unless the module already does
that.

## Questions to ask

Use `identity.suggested_package_name` and `identity.suggested_module_name`
from the audit script.

**Rename** (decision `identity.rename`), released package:

> **The package is `acme/module-foo`; Mage-OS modules are `mage-os/module-foo`
> with the `MageOS_Foo` module name.** Required before the module can move
> into the Mage-OS org. v1.4.0 is released, so this is a 2.0: admin roles
> need re-granting, and a `replace` entry keeps both packages from being
> installed together. Config paths and saved settings stay as they are.
>
> 1. Rename in a 2.0, with `replace` and upgrade notes in the CHANGELOG (Recommended)
> 2. Not now, ask again at the next major release
> 3. Keep the current name (blocks acceptance into the Mage-OS org)

For a new package (no tags), drop the migration part: "Nobody depends on
it yet, so renaming is free now and painful later."

**License** (decision `license.change`), only when the current one isn't
accepted:

> **The module is licensed GPL-3.0; Mage-OS accepts OSL-3.0, AFL-3.0, MIT
> or BSD-3-Clause.** GPL conflicts with Magento's OSL license. Changing it
> needs consent from every copyright holder; git shows 3 outside
> contributors.
>
> 1. Switch to OSL-3.0, after you've confirmed consent with the contributors (Recommended)
> 2. Switch to MIT, same condition
> 3. Keep GPL-3.0 (blocks acceptance into the Mage-OS org)

**Composer metadata** is auto-fixable: bundle missing `description`,
`require` entries, a stray `version` field and `<sequence>` into one
"Tidy up composer.json and module.xml? (Recommended)" question.
