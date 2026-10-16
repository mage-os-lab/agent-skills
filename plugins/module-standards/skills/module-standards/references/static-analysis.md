# Static analysis

## Criteria

- **PHPStan at level 8**, configured in `phpstan.neon` (or `.neon.dist`) in
  the module root, with `bitexpert/phpstan-magento` so generated classes
  (`*Factory`, `*Proxy`, extension attributes) resolve. Without that
  extension even level 0 drowns in unknown-class errors.
- **Magento coding standard** (`magento/magento-coding-standard`) passing,
  with a `phpcs.xml.dist` in the root so maintainers run the same rules CI
  runs.
- Exclusions are narrow (a path or a single sniff on a single file) and each
  has a comment explaining why.
- **New package (no git tags)**: level 8 from the start, no baseline. There
  is no legacy to protect, and it only gets harder later.
- **Released package (has tags)**: a baseline (`phpstan-baseline.neon`) is
  acceptable on the way up, on the condition that it only shrinks. New code
  never adds to it.

## Running locally

PHPStan and PHPCS can run against the module standalone; they need the
Magento framework classes on the autoloader, not a working store. That
requires the module's composer.json to have the dev tools and a repository
that serves Magento packages:

```json
"require-dev": {
    "bitexpert/phpstan-magento": "^0.32",
    "magento/magento-coding-standard": "^38",
    "phpstan/extension-installer": "^1.4",
    "phpstan/phpstan": "^2.1",
    "phpunit/phpunit": "^10.5"
},
"repositories": [
    { "type": "composer", "url": "https://mirror.mage-os.org/" }
],
"config": {
    "allow-plugins": {
        "phpstan/extension-installer": true,
        "dealerdirect/phpcodesniffer-composer-installer": true,
        "magento/composer-dependency-version-audit-plugin": false,
        "magento/magento-composer-installer": false
    }
}
```

Check current major versions with `composer show -a <package>` before
copying these; the constraints above are a starting point, not gospel. Make
sure `phpunit/phpunit` matches what the lowest supported Magento version
ships with.

Then `composer install` and run:

```bash
vendor/bin/phpstan analyse
vendor/bin/phpcs
```

If the module is installed inside a store instead (`vendor/` or
`app/code/`), run the store's binaries with the module path as argument.

## Fixing

1. Copy `assets/phpstan.neon` and `assets/phpcs.xml.dist`; adjust paths.
2. **New package**: set level 8 and fix everything. **Released package that
   never ran PHPStan**: climb levels. Start at level 0 and go up one at a
   time, fixing everything before raising. Fixing at level 8 directly
   produces a wall of errors where the real bugs (wrong argument types, calls
   on possibly-null values) are lost among missing array shapes.
3. Fix the code, not the config. Typical fixes: real type declarations
   instead of docblocks, null checks where a repository `get()` result or
   `getData()` can be null, `@var` array shapes on data coming from config,
   `(int)`/`(string)` casts at Magento's loosely typed boundaries
   (`getConfig()` returns `mixed`).
4. Where a fix would change behavior (a null check that now throws instead of
   silently continuing), flag it to the maintainer instead of choosing.
5. For a released package, if level 8 isn't reachable in this session, stop
   at the highest clean level, generate a baseline for the rest at level 8,
   and say how many errors it holds. That's progress, and the number is a target for next time.
6. For PHPCS, run `vendor/bin/phpcbf` first for the mechanical fixes, review
   the diff, then fix the rest by hand. Warnings matter too: check-extension
   reports them, and many are real (e.g. direct `$_GET` use, missing escaping).
