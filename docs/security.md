# Security

This project treats all external input — anything crossing a network
boundary it doesn't control — as untrusted by default.

## What this app actually handles

No accounts, no passwords, no payments, no personal data, no database.
The only input a user provides is a display name (≤24 characters) and an
answer (≤80 characters), and neither outlives the match or the process.
That keeps the risk surface small — it does not make it zero.

## The judge token

A refereed match (`juez` mode, ADR-0007) mints a random token, returns it
once in the creation response, and requires it for every mutating
endpoint and for the only endpoint that carries the answers. Two things
follow, and both are deliberate:

- It is a **secret for a room, not authentication**. It identifies the
  device holding the link, not a person; anyone who obtains the link can
  see the answers and play the match. Comparison is constant-time and the
  token dies with the match, but neither of those makes it an identity.
- The board view is unauthenticated on purpose — it is meant to be
  projected — so *everything* the board endpoint returns must be safe for
  a room to see. Never add an answer, a token, or anything private to
  `_state()`; the judge's extra data belongs in the judge endpoint.

## Rules that apply to every change here

- **Never commit a secret.** Nothing in this repo needs one today; if
  that changes, it goes in a gitignored `.env` locally and a platform
  Secret on the target — never in a committed file. See the deny-list in
  `.claude/settings.json`.
- **Pin every version.** Base image, Python dependencies, action
  versions. A pin is what makes "why did this break?" answerable later.
- **Least privilege by default.** The container runs as a non-root user,
  read-only, with all capabilities dropped and
  `no-new-privileges` — in `docker-compose.yml` and in `deploy/k8s/`.
  Keep it that way; the app has no reason to need more.
- **Explicit resource limits on every container.** Memory, CPU and PIDs
  are set in both. An unbounded container on a shared host can starve
  everything else running there.
- **Bound anything a client can grow.** Match state is capped
  (`MAX_GAMES`) and request fields have explicit length and range
  limits, so a loop of requests can't exhaust memory.
- **Don't widen exposure by default.** Compose binds to `127.0.0.1`
  only, and the Kubernetes Service is a ClusterIP. Exposing this to a
  LAN or the internet is a deliberate, documented decision.

## Concern categories

Relevant to this project today:

- Untrusted input handling (answers, names, path parameters)
- Resource exhaustion / denial of service via unbounded state
- Information disclosure (answers must not reach the client early)
- Container privilege and isolation

Not applicable while the constraints in `docs/product.md` hold, and to
be revisited if they change: authentication/authorization, session
isolation between users, persistence of untrusted data, secret handling.

## Decisions

- `docs/decisions/0006-pasapalabra-web-game.md` — the game runs
  server-side precisely so answers and clocks are not client-controlled.
- `docs/decisions/0007-judge-mode.md` — the judge's answers live behind a
  separate, token-gated URL so the projected board can stay safe to
  project.

## Reporting

Do not post vulnerability details in a public Issue or PR. See
`SECURITY.md` for the reporting contact.
