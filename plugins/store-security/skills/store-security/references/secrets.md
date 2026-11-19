# Secrets in git

`app/etc/env.php` holds the database password and the crypt key, which
decrypts every encrypted value in the admin (payment gateway keys, API
tokens). `auth.json` holds the Composer keys for repo.magento.com or private
repositories. Anyone with a copy of the repository, a former agency, a
leaked CI cache, a public fork, has them.

## Criteria (Critical)

- No sensitive file is tracked (`git.tracked_sensitive_files`): `env.php`,
  `auth.json`, `.env`, database dumps, private keys.
- None was ever committed (`git.sensitive_files_in_history`): deleting a
  file in a later commit leaves it in every clone.
- No secret pattern in the history (`git.secret_patterns_in_history`: crypt
  key, database password, repo.magento.com keys, private keys, cloud and
  payment API keys). The report gives commits and files, never values. To
  look at a hit, show the line with the value masked, never in full.
- `.gitignore` covers them (`git.not_ignored`): `app/etc/env.php`,
  `auth.json`, `.env`, `var/`, `generated/`, `pub/media/`, `pub/static/`.
  `app/etc/config.php` *should* be committed: it lists modules, no secrets.

## Fixing

1. **Stop tracking now** (auto-fixable): add the entries from
   `assets/gitignore` to `.gitignore`, then `git rm --cached <file>`. The
   file stays on disk. This doesn't remove it from history.
2. **Rotate what leaked** (needs decision): a secret that reached git is
   compromised, whatever happens to the history next.
   - Database password: change it on the database server, then in `env.php`.
   - Composer keys: regenerate them in the Magento Marketplace account (or
     the private repository) and update `auth.json`.
   - Crypt key: `bin/magento encryption:key:change` (2.4.7 and later; on
     older versions, System > Other Settings > Manage Encryption Key in the
     admin) generates a new key and re-encrypts the values core stores.
     Back up the database first. Values a third-party module encrypts in
     its own tables are not re-encrypted: check those modules still work.
     Then change the keys at the payment providers themselves: whoever had
     the old crypt key could already decrypt them.
   - Any other API key found: revoke it at the provider.
3. **Rewrite history** (needs decision, last): `git filter-repo --invert-paths
   --path app/etc/env.php` (and the others) removes them from every commit,
   but it rewrites all commit IDs: every clone and fork must be re-cloned,
   and it changes nothing for copies already made. Only after rotation, and
   only if the maintainer controls every copy. Never push the result
   yourself.

## Questions to ask

**Committed secrets** (decision `secrets.rotate_crypt_key`):

> **`app/etc/env.php` is in git since commit 4b10cbd, with the crypt key and
> the database password.** Anyone with a copy of the repository can decrypt
> the payment credentials stored in the admin. Removing the file from git
> doesn't change that: the keys must be replaced.
>
> 1. Stop tracking it now and rotate the crypt key, database password and
>    payment keys, in that order (Recommended)
> 2. Stop tracking it now, rotate later
> 3. Skip for now

**History rewrite** (decision `secrets.rewrite_history`), only after
rotation: "Remove env.php and auth.json from the whole history too? Every
clone will need to be re-cloned." with "Leave the history, the keys are
rotated (Recommended)" when the repository has outside copies.
