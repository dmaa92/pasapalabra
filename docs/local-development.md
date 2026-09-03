# Local Development

## Requirements

Docker (with the Compose plugin) and `make`. Nothing else — there is no
Python, Node or package manager to install on the host: every command
below runs inside the image.

## Run it

```
make up      # build the image and start the app
make wait    # block until the container reports healthy
```

Open http://127.0.0.1:8080/ and play. `APP_PORT` changes the host port:

```
APP_PORT=9000 make up
```

`.env` (gitignored, copy from `.env.example`) is picked up by Compose if
you prefer to set it there.

## Inspect

```
make ps
make logs
docker stats
```

## Run a refereed match

Pick **Juez** in the mode selector. The page you are on becomes the board
(project it) and shows the judge's link:

```
http://127.0.0.1:8080/juez#<id>:<token>
```

Open it in another tab, another window, or — if you want the real
competition setup — on a phone, replacing `127.0.0.1` with the machine's
LAN address. That needs the app bound beyond loopback, which
`docker-compose.yml` deliberately does not do; for a one-off, run the
image directly:

```
docker run --rm -p 8080:8000 --read-only --tmpfs /tmp pasapalabra:dev
```

and reach it at `http://<your-lan-ip>:8080/`. Anything more permanent is
an exposure decision — see `docs/security.md`.

Refreshing the board is safe: the match id is in the URL fragment, so it
picks the match back up. The same is true of the judge panel, token
included.

## Poke the API directly

```
curl -s -X POST localhost:8080/api/games \
  -H 'Content-Type: application/json' \
  -d '{"player_one":"Ana","player_two":"Bea","seconds":200}'

curl -s -X POST localhost:8080/api/games/<id>/answer \
  -H 'Content-Type: application/json' -d '{"text":"abeja"}'

curl -s -X POST localhost:8080/api/games/<id>/pass
curl -s localhost:8080/api/games/<id>
```

A refereed match instead — note that `judge_token` comes back only in
this first response:

```
curl -s -X POST localhost:8080/api/games \
  -H 'Content-Type: application/json' \
  -d '{"player_one":"Ana","player_two":"Bea","mode":"juez"}'

curl -s "localhost:8080/api/games/<id>/judge?token=<token>"

curl -s -X POST "localhost:8080/api/games/<id>/judge?token=<token>" \
  -H 'Content-Type: application/json' -d '{"correct":true}'
```

Without the token those two return 403; `/api/games/<id>` (the board)
works without one and never contains an answer.

FastAPI's generated docs are at http://127.0.0.1:8080/docs.

## Generate a category

```
make rosco CATEGORIA="cine español"
```

Drafts two roscos on that theme with the Claude API, validates them with
the same `validate_rosco` the tests use, asks for a repair of whatever
failed, and writes `app/data/roscos/cine-espanol.json`. Useful flags come
after `ARGS=`:

```
make rosco CATEGORIA="geografía" ARGS="--roscos 4 --attempts 5 --force"
```

It needs `ANTHROPIC_API_KEY` in your `.env`, and runs in the `tools`
image (Dockerfile stage `tools`), which is the only place the Anthropic
SDK is installed. The app image has none of it and never calls out.

Read the generated file before committing it: the validator checks the
shape of a rosco, not whether its answers are true. Restart the app
(`make up`) to pick up a new category — the banks are loaded once at
startup.

## Change the questions

`app/data/roscos.json` is the whole question bank. `make unit` checks
that every rosco covers all 25 letters in order, that each answer really
starts with (or contains) its letter, that answers aren't repeated
inside a rosco, and that a clue never gives its own answer away — so a
bad entry fails a test instead of surfacing mid-game.

## Stop and clean

```
make down    # stop and remove this project's containers
make clean   # also remove volumes — scoped to this project, never a global prune
```

Never substitute a global `docker system prune` for `make clean` on a
shared machine: it affects every other project on that host.
