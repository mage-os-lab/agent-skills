---
type: llm
focus: trace
---

`app/etc/env.php` and `auth.json` are committed to git and `.gitignore` doesn't cover them. PASS if the agent flags both as committed secrets and says the leaked values (crypt key, database password, Composer keys) must be rotated, not only removed from git. FAIL if it only proposes untracking the files or adding them to `.gitignore`.
