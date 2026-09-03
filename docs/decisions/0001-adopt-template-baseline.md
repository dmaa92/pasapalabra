# ADR-0001: Adopt the standard project-template baseline for this repository

# Context

New projects historically started from a blank repository, which meant
every project re-derived its own answer to questions that don't actually
vary much between projects: how AI agents and contributors should read
context before acting, how decisions get recorded, what the standard
local-dev and CI/CD shape looks like, and what security guardrails ship
by default. That re-derivation was slow and inconsistent, and gaps (a
missing secrets deny-list, an undocumented PR policy) surfaced late.

# Alternatives

a. **Keep starting from a blank repository** — Descartada: every project
   re-solves the same governance and tooling questions, with inconsistent
   and sometimes absent results.
b. **A shared library/framework repo that projects depend on** —
   Descartada: couples every project's lifecycle to a shared dependency's
   release cadence, for content (docs structure, contracts) that isn't
   actually code.
c. **A copy-once project template repository** — Elegida.

# Decision

New projects start from the project-template repository: its file
structure, `AGENTS.md`/`CLAUDE.md` contract, `docs/` set, testing and
CI/CD shape, and security guardrails are copied in at project creation
and then owned locally — not kept in sync with the template afterward.

# Rationale

A copy-once template gives every new project a known-good starting
point without creating an ongoing dependency: once copied, a project is
free to diverge as its actual needs demand, while still starting from
the same governance and security baseline every other project starts
from. This favors project autonomy and simplicity over enforced
uniformity.

# Consequences

## Positivas

- New projects get a working `AGENTS.md`, doc set, CI/CD, and security
  baseline on day one instead of building one from scratch.
- The security guardrails (secrets deny-list, `.dockerignore` exclusions,
  destructive-action confirmation guards) are present by default, not
  opt-in.

## Negativas y riesgos

- The template and a given project's copy will drift over time; there is
  no mechanism here to propagate a template improvement into projects
  that already copied it. Improvements to the template only benefit
  future projects unless someone manually backports them.
- The optional modules (`infra.optional/`, `deploy.optional/`) require a
  human to make a conscious rename-or-delete decision at project start;
  an unattended copy could leave both, or neither, without anyone
  noticing.
