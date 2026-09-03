# ADR-0008: Generate category question banks offline, never during a match

# Context

The shipped bank is two hand-written general-knowledge roscos (ADR-0006,
and the replacement bank after it). Writing 25 questions by hand is slow,
and a competition wants themed roscos — cinema, geography, a school
syllabus — that nobody wants to write from scratch every time.

A model can draft them. Where it runs is the decision, and it is not a
free choice: the questions carry answers that a judge reads out as
authoritative in front of a room, and the application today needs no
secret, no network egress and no environment variable to start
(`AGENTS.md`, ADR-0006).

Two failure modes matter. A generated answer can be plainly wrong — a
model will state a false date with the same confidence as a true one —
and a generated rosco can be *malformed*: a word that doesn't start with
its letter, a repeat, a clue that contains its own answer.

# Alternatives

a. **The app calls the API when a match is created, with the category
   the user typed** — Descartada: puts an API key inside the deployed
   container, adds network egress, latency and per-match cost, and makes
   the app fail to start without a key. Worse, it puts unreviewed
   answers on the judge's screen mid-competition, where a wrong one
   becomes an argument in the room with no way back.
b. **Ask an assistant for questions in a chat and paste the JSON in by
   hand** — Descartada: no validation, no repair loop, and the shape
   errors (wrong letter, duplicate, leaking clue) are exactly the ones a
   human reviewer skims past.
c. **An authoring script a person runs, whose output is validated
   mechanically and then read by a human before it is committed** —
   Elegida.

# Decision

`scripts/generate_rosco.py` drafts a category's roscos with the Claude
API (`claude-opus-5`, structured JSON output), checks every draft with
`app.content.validate_rosco` — the same function the tests hold the
hand-written bank to — asks the model to repair only the entries that
failed, and writes `app/data/roscos/<category>.json` for a human to read
and commit. It is run as `make rosco CATEGORIA="cine español"`.

It lives in a separate Dockerfile stage (`tools`) that carries the
Anthropic SDK and reads `ANTHROPIC_API_KEY` from the developer's `.env`.
The deployed image is the `runtime` stage: no SDK, no key, no egress. At
match time the application only reads JSON files that are already in the
repository.

In the client this is offered as a third option in the mode selector,
"por categoría". It is not a third set of rules: it chooses where the
questions come from, and the player then picks whether that match is
resolved from the keyboard or by a judge. On the wire the two axes stay
separate — `mode` is still `teclado`/`juez`, plus a `category`.

# Rationale

Generation is an authoring step, so it belongs with authoring, not in
the request path. That keeps the deployment contract from ADR-0006
intact — one image, no backing services, no secret — and it puts a human
between a generated claim and a room full of people, which is the only
control that actually catches a false answer. The mechanical rules are
worth automating precisely because they are the ones a human reviewer
misses; truth is worth *not* automating, because no validator can settle
it.

Reusing `validate_rosco` rather than writing a second checker in the
script is what stops generated content entering under a laxer standard
than the questions written by hand.

# Consequences

## Positivas

- The application is unchanged in kind: still one stateless image with no
  key and no network dependency.
- A bad draft fails in the terminal, before review, not in a match.
- Adding a category is a `make` target and a pull request, so every
  question that reaches a player has been read by someone.

## Negativas y riesgos

- Generated answers are **not** fact-checked by anything in this repo.
  The file records `"reviewed_by_a_human": false`; nothing enforces that
  it ever becomes true. A reviewer who skims is the whole of the defence.
- Adding a category needs an API key and a person, so a user of a
  deployed instance cannot invent a category — by design, but it is a
  real limitation of the feature as asked for.
- The script costs money per run and can fail to converge; it gives up
  after `--attempts` repair rounds rather than shipping a broken rosco.
