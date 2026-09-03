.PHONY: help build up wait down logs ps clean validate unit smoke

# Everything runs through Docker on purpose: the container is the only
# supported way to run this app, so "works on my machine" and "works in
# CI" are the same machine.
RUN = docker compose run --rm --no-deps

help:
	@echo "build     - build the application image"
	@echo "up        - build and start the app"
	@echo "wait      - block until the app reports healthy"
	@echo "down      - stop and remove this project's containers"
	@echo "logs      - tail the app logs"
	@echo "ps        - show running services"
	@echo "clean     - scoped teardown (this project only, no global prune)"
	@echo "validate  - static checks: compose config, Python syntax, question bank"
	@echo "unit      - game-rules and question-bank tests"
	@echo "smoke     - play a turn against the running stack"

build:
	docker compose build

up: build
	docker compose up -d

wait:
	@echo "Waiting for app to report healthy..."
	@for i in $$(seq 1 20); do \
		status=$$(docker compose ps app --format '{{.Health}}' 2>/dev/null); \
		if [ "$$status" = "healthy" ]; then echo "app is healthy."; exit 0; fi; \
		sleep 3; \
	done; \
	echo "Timed out waiting for app to become healthy:"; \
	docker compose ps; \
	exit 1

down:
	docker compose down

logs:
	docker compose logs -f app

ps:
	docker compose ps

clean:
	docker compose down -v --remove-orphans

# compileall and friends run through the `tests` service: the app
# service mounts its root filesystem read-only, and compileall insists on
# writing __pycache__.
validate: build
	docker compose config --quiet
	$(RUN) tests python -m compileall -q app
	$(RUN) tests python -m json.tool app/data/roscos.json > /dev/null
	@find . -name '*.sh' -not -path './.git/*' -exec bash -n {} \;

unit: build
	$(RUN) tests

smoke:
	@port=$${APP_PORT:-8080}; base="http://127.0.0.1:$$port"; \
	echo "Checking $$base/healthz ..."; \
	curl -fsS "$$base/healthz" | grep -q '"status":"ok"'; \
	echo "teclado: creating a game and playing a pasapalabra ..."; \
	id=$$(curl -fsS -X POST "$$base/api/games" -H 'Content-Type: application/json' \
		-d '{"player_one":"smoke","player_two":"test"}' \
		| sed -n 's/.*"id":"\([^"]*\)".*/\1/p'); \
	test -n "$$id" || { echo "no game id returned"; exit 1; }; \
	curl -fsS -X POST "$$base/api/games/$$id/pass" > /dev/null; \
	curl -fsS "$$base/api/games/$$id" | grep -q '"turn":1' || { echo "pasapalabra did not hand over the turn"; exit 1; }; \
	echo "juez: creating a refereed game ..."; \
	game=$$(curl -fsS -X POST "$$base/api/games" -H 'Content-Type: application/json' \
		-d '{"player_one":"smoke","player_two":"test","mode":"juez"}'); \
	id=$$(echo "$$game" | sed -n 's/.*"id":"\([^"]*\)".*/\1/p'); \
	token=$$(echo "$$game" | sed -n 's/.*"judge_token":"\([^"]*\)".*/\1/p'); \
	test -n "$$token" || { echo "no judge token returned"; exit 1; }; \
	if curl -fsS "$$base/api/games/$$id" | grep -q '"answers"'; then \
		echo "the board view leaked the answers"; exit 1; \
	fi; \
	code=$$(curl -s -o /dev/null -w '%{http_code}' "$$base/api/games/$$id/judge"); \
	test "$$code" = "403" || { echo "the judge view answered $$code without a token"; exit 1; }; \
	curl -fsS "$$base/api/games/$$id/judge?token=$$token" | grep -q '"answers"' \
		|| { echo "the judge view is missing the answers"; exit 1; }; \
	curl -fsS -X POST "$$base/api/games/$$id/judge?token=$$token" \
		-H 'Content-Type: application/json' -d '{"correct":true}' \
		| grep -q '"correct":true' || { echo "the judge could not score a hit"; exit 1; }; \
	curl -fsS "$$base/" | grep -q '<title>Pasapalabra</title>'; \
	curl -fsS "$$base/juez" | grep -q 'Panel del juez'; \
	echo "smoke OK"
	@docker compose ps --format '{{.Name}}: {{.Image}}, health={{.Health}}'
