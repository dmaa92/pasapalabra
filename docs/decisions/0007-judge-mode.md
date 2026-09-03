# ADR-0007: Add a refereed mode with a separate, token-gated judge view

# Context

ADR-0006 shipped one way to play: each player types their answer and the
server compares it against the rosco. That works for two people sharing a
keyboard, but not for the setting this game is actually wanted in — a
competition, where the roscos are projected, the players shout their
answers, and somebody has to rule on them.

That setting has two audiences at once. The room must see the roscos, the
clocks and the clue; it must never see the answers. The judge needs
exactly the opposite: the answers, and the buttons that resolve a letter.
One screen cannot serve both.

# Alternatives

a. **Add a judge panel to the existing board page** — Descartada: the
   page that carries the answers is the page you project. It only works
   if the judge has a monitor nobody else can see, which is the case the
   feature exists to avoid.
b. **Let the client hold the answers and hide them with CSS** —
   Descartada: same failure as ADR-0006's rejected static version. What
   the browser has, the room can read.
c. **Real accounts and roles for judge and audience** — Descartada:
   authentication, user storage and a login flow, for a room where the
   judge is standing next to the operator. Nothing else in this app
   stores anything about a person.
d. **A second view at `/juez`, addressed by a per-match token minted at
   creation** — Elegida.

# Decision

A match is created in one of two modes: `teclado` (unchanged) or `juez`.
In `juez` mode the server mints a random token, returns it exactly once —
in the creation response — and from then on requires it for every
mutating endpoint and for `GET /api/games/{id}/judge`, the only endpoint
that carries the answer sheets. `/` stays the board: it polls the public
state once a second, shows roscos, clocks, score and clue, and cannot
play. `/juez` is the judge's panel: current letter, correct answer, and
the buttons for hit, miss, pasapalabra and "se planta".

Both modes resolve a letter through the same `Game._resolve()`; the mode
only decides who determines the verdict. A typed answer in a refereed
match, or a ruling in a keyboard match, is rejected as a mode error.

# Rationale

The split is the point: whatever the room can see must not include the
answers, so the answers have to live behind a different URL than the one
being projected. A token in that URL is the smallest thing that makes the
split real — it needs no accounts, no storage, and no login, and it dies
with the match. Sharing the rule engine between modes means a change to
the rules can't quietly apply to only one way of playing.

# Consequences

## Positivas

- The projected board is safe to project: no endpoint it calls returns an
  answer, in either mode.
- The judge can use any device on the same network — a phone works — with
  no install and no account.
- Rules stay in one place, tested once, for both modes.

## Negativas y riesgos

- The token is a shared secret for a room, not authentication: anyone who
  gets the link (over someone's shoulder, in a chat, in a proxy log) can
  see the answers and play the match. Documented in
  `docs/known-limitations.md`; a real fix means real accounts.
- The token is shown once. Lose it and the match can only be restarted.
- The board discovers rulings by polling once a second, so it can lag the
  judge's click by up to that long, and every open board adds one request
  per second.
- Judge mode makes the in-memory, single-replica constraint load-bearing:
  two replicas would put the judge and the board on different match
  lists.
