# ADR-0006: Repurpose this repository as a containerised Pasapalabra web game

# Context

This repository was created from the project template (ADR-0001) and
then used to host a PrestaShop storefront on a self-managed k3s cluster
(ADRs 0002–0005). That work is no longer what the repository is for: the
goal now is a simple web game — Pasapalabra, two players by turns — that
can be deployed as a container on *any* container platform, not on one
specific cluster.

Keeping the previous scaffolding (Ansible roles for k3s, a Helm wrapper
chart, a Cloudflare Tunnel runbook, PrestaShop's compose stack) would
have left the repository carrying infrastructure it no longer owns, and
ADRs describing decisions that no longer bind anything here.

Two properties of the game itself forced a decision: a rosco has correct
answers, and it has clocks. Both are trivially forgeable in a browser.

# Alternatives

a. **Keep the k3s/Helm/PrestaShop scaffolding alongside the game** —
   Descartada: dead scaffolding is worse than none. It implies this repo
   owns a cluster it doesn't, and every reader has to work out which
   half is real.
b. **Ship the game as a static page with the answers in the client** —
   Descartada: the answers and the clocks would be in the player's
   hands, and "don't open devtools" is not a rule a game can enforce.
c. **Full stack with a database and accounts** — Descartada: nothing in
   the requirements needs persistence or identity; a database would be
   an operational cost with no user-visible benefit.
d. **A single stateless container: server-authoritative rules plus a
   no-build-step browser client** — Elegida.

# Decision

The repository is now a Pasapalabra game and nothing else. The k3s
Ansible tree, the Helm chart, the Cloudflare Tunnel runbook, the
PrestaShop compose stack and ADRs 0002–0005 are removed (they remain in
the history of the template repository this project was copied from,
`procomitsolutions/template_proyectos`). The application is one FastAPI
process serving both a JSON API and a static HTML/CSS/JS client,
packaged as a single image with no database and no volume. All rules —
whose turn it is, what counts as a hit, how much time each player has —
are
evaluated on the server, and the correct answers are withheld from the
client until the match ends. Deployment artefacts are limited to
`docker-compose.yml` for local use and plain Kubernetes manifests in
`deploy/k8s/`.

# Rationale

The deployment target is "any container infrastructure", so the app's
only contract should be *run this image and give it a port*. A database
would break that for no requirement anyone stated. Server-side rules
cost nothing here — the game logic is a few hundred lines of pure
Python — and they are the only way the score means anything. Plain
manifests over Helm keeps the deployment readable and portable: there is
one deployable, with no values files to reconcile.

# Consequences

## Positivas

- The image is the whole system: no database to back up, no volume to
  provision, no cluster-specific add-on to install.
- The rules are pure functions over an injected clock, so the entire
  rule set is unit-tested without sleeping or running a server.
- A player cannot read the answers, edit their clock, or score a letter
  from the browser.

## Negativas y riesgos

- Match state is in memory: a restart loses matches in progress, and the
  Deployment is pinned to one replica. Scaling out needs shared state
  first (`docs/known-limitations.md`).
- Every play is a round trip to the server, so the game needs the
  network to be responsive; an offline or laggy client degrades badly.
- The infrastructure knowledge that lived in `infra/` and `deploy/` is
  now only in git history. Re-provisioning a cluster from this repo is
  no longer possible, by design.
