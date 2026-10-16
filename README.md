<p align="center">
  <a href="https://mage-os.org"><img src=".github/assets/mage-os-logo.png" alt="Mage-OS" width="120"></a>
</p>

<h1 align="center">Mage-OS agent skills</h1>

AI agent skills for Magento and Mage-OS: modules, stores, themes and
everything in between. Works with Claude Code, Codex, Gemini CLI, Cursor,
GitHub Copilot, OpenCode and other tools that support the open
[Agent Skills](https://agentskills.io) standard.

## Skills

| Skill | What it does |
|---|---|
| [**module-standards**](plugins/module-standards/README.md) | Audits a Magento or Mage-OS module against the Mage-OS extension standards (CI, PHPStan, PHPCS, tests, admin UX, security, documentation) and brings it up to that level, one area at a time. |

More skills are on the way. Have an idea for one? See
[Contributing](#contributing).

## Wishlist

Skills we'd love to see. Want to build one? Say so in the
[Mage-OS Discord](https://mage-os.org/discord-channel/) so work doesn't
overlap, then open a pull request.

| Skill | What it would do |
|---|---|
| **mageos-migration** | Move a store from Magento Open Source to Mage-OS: composer changes, a compatibility report for installed extensions, patches and a test plan. |
| **store-upgrade** | Plan and carry out a Magento or Mage-OS version upgrade: risky extensions, overridden templates, conflicting plugins and preferences, and a test checklist. |
| **extension-vetting** | Assess a third-party extension before installing it: code quality, callhome code, security, and conflicts with the extensions already installed. |
| **store-performance** | Find what slows a store down: full page cache blockers, indexer and cron setup, Redis and OpenSearch configuration, heavy layout handles. |
| **store-security** | Check a store's security: missing patches, `composer audit` across all dependencies, admin hardening, exposed files, CSP mode, secrets committed to git. |

## Installation

### Claude Code

Add this repository as a plugin marketplace once:

```
/plugin marketplace add mage-os-lab/agent-skills
```

Then install the skills you want:

```
/plugin install module-standards@mage-os
```

Update with `/plugin marketplace update mage-os`, or turn on auto-update
under `/plugin` > Marketplaces > mage-os.

### Other tools

Every skill lives in `plugins/<name>/skills/<name>/` and works in any tool
that supports Agent Skills. Install one with the cross-tool installer:

```bash
npx skills add https://github.com/mage-os-lab/agent-skills/tree/main/plugins/<name>/skills/<name> -g
```

or copy the folder to `~/.agents/skills/`, which Codex, Gemini CLI, Cursor,
GitHub Copilot and OpenCode all read. Each skill's README has the exact
commands, including how to upload it to Claude.ai.

## Contributing

Contributions are welcome, from fixing a typo in a rule to adding a whole
new skill.

- **Change a rule.** The standards a skill applies are written down in its
  `references/` folder. Open a pull request against the file; the
  discussion happens there.
- **Add a skill.** Follow the structure of an existing skill in
  `plugins/`, add the plugin to `.claude-plugin/marketplace.json`, and add a
  row to the Skills table.
  Keep skills tool-neutral: plain instructions, no features that only one
  agent supports.
- **Test it.** Run the skill on a few real modules or stores before opening
  the pull request, and mention what you tried.

Not sure where to start? Ask in the
[Mage-OS Discord](https://mage-os.org/discord-channel/).

## License

Dual licensed under the [Open Software License 3.0](LICENSE.txt) and the
[Academic Free License 3.0](LICENSE_AFL.txt), the same licenses as Magento
and Mage-OS.
