# Agent Instructions

This file is the canonical, tool-neutral contract for working in this
repository — human or AI. Tool-specific files (`CLAUDE.md`, `.codex/`, etc.)
must not restate these rules; they include this file and add, at most, a
pointer to tool-specific configuration.

## Source of truth

1. The GitHub Issue (or discussion) driving the change is the spec.
2. This file, then `docs/`, then `docs/decisions/` (ADRs).
3. The existing code, read before it is changed.

Do not invent a product, architecture, or security decision that isn't
documented. If one is missing, say so as a blocker — do not guess and
proceed.

## Workflow

- Branch off an Issue; keep each branch, commit, and diff scoped to that
  Issue's stated intent.
- No direct pushes to the default branch — open a pull request.
- Prefer the simplest implementation that satisfies the acceptance
  criteria. Do not add abstractions, config flags, or "future-proofing"
  the Issue didn't ask for.
- Justify any new dependency in the PR description: what it replaces,
  why it's needed.
- Run `make validate` and the relevant `make` test targets before opening
  a PR (see `docs/testing.md`).
- Update `docs/` in the same PR whenever behavior or architecture changes.

## Security

- Read `docs/security.md` before changing how the app handles input,
  what it sends to the browser, or how the container is privileged.
- Never commit secrets, tokens, keys, or credentials — see
  `docs/security.md` and the deny-list in `.claude/settings.json`.
- Treat all external input (user input, third-party APIs, webhooks) as
  untrusted.
- Never weaken authentication, authorization, or isolation to make a test
  pass or unblock a deadline. Raise it as a blocker instead.
- Never take a destructive action against real infrastructure (production
  data, deployed clusters, DNS) without explicit, documented
  authorization from a human.

## Definition of Done

A change is done when:

- It satisfies the Issue's stated acceptance criteria — nothing more,
  nothing less.
- Relevant tests exist and pass (`make unit`, `make validate`, plus any
  scenario-specific target the change touches).
- It introduces no observable regression.
- `docs/` reflects the new behavior, architecture, or constraint.
- It is ready for human review as a pull request.

## Project constraints

- **Lifecycle stage: prototype.** The application is a Pasapalabra game
  for two players by turns, packaged as a single stateless container
  image (`docs/decisions/0006-pasapalabra-web-game.md`). It runs locally
  via `docker-compose` on `127.0.0.1:8080` and can be deployed to any
  container platform (`deploy/k8s/`). It is not deployed or exposed
  anywhere today.
- **Server-authoritative by design.** Turn order, scoring, clocks and
  the correct answers live on the server, and answers are withheld from
  the client until a match ends. Moving any of that into the browser to
  simplify something is a decision that needs to be argued in an ADR,
  not an implementation detail.
- **Two modes, one rule engine.** `teclado` (players type) and `juez`
  (a judge rules, `docs/decisions/0007-judge-mode.md`) resolve a letter
  through the same code path — only the verdict's source differs. Add a
  rule to both or to neither.
- **The board is projected.** Anything `_state()` returns is assumed to
  be on a screen a room can see. Answers and tokens go only through the
  token-gated judge endpoint; never widen the board payload.
- **One image, no backing services.** No database, no volume, no
  required environment variable to start. Adding a dependency the app
  cannot start without changes the deployment contract — justify it in
  the PR before adding it.
- **Out of scope for now:** accounts, persistence across restarts,
  online play between two browsers, and public exposure. Treat a request
  to open a port beyond loopback, add an Ingress or tunnel, or store
  anything about a player as a decision that needs explicit, documented
  authorization first — not something to infer from "make it work."
