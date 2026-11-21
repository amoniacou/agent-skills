---
worth: yes
added: 2026-11-17
---
# split the amoniac plugin into five plugins

The `amoniac` plugin is large. The user wants it easier to keep, with a version for each part, so that colleagues can install only a part. Do it after `docs/plans/2026-11-17-review-full-cycle-in-herdr.md`.

The user selected five plugins in this repository, each with an entry in `.claude-plugin/marketplace.json`:

| Plugin | Contents |
|---|---|
| `amoniac-rules` | `principles`, `naming`, `testing`, `go-best-practices`, `helmcheck` |
| `amoniac-guards` | the hooks `block-*`, `go-lookups`, `remind-skills`, `required-skills` |
| `amoniac-planning` | `brainstorm`, `plan`, `review-plan`, `backlog`, `oversight`, `complete-plan` |
| `amoniac-review` | `review`, `setup-review`, the hook `allow-debate-commands` |
| `amoniac-spawn` | `spawn-session` |

Facts found before the decision:

- The plugin name is the prefix of a skill name. `amoniac:naming` becomes `amoniac-rules:naming`. The repository has approximately 140 `amoniac:` references.
- `.agents/required-skills.json` in other projects of the user has `amoniac:` names. Open question: edit those files, or let the hook accept the old names for a time.
- `required-skills.py` finds a `SKILL.md` through its own `PLUGIN_ROOT`. `debate.py` puts the text of the rules skills into the review prompt. After the split, these skills are in a different plugin folder. The installed layout is `cache/<marketplace>/<plugin>/<version>/`. The development layout is the repository folder.
- `review` needs the rules for the prompt. `oversight` starts `spawn-session`. README must name these dependencies.
