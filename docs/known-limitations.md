# Known Limitations

A running register of accepted gaps — things known to be incomplete or
imperfect, kept on purpose rather than silently. When a limitation is
resolved, mark it resolved with a date instead of deleting the entry;
the history of what was once true is useful.

| Date added | Limitation | Status |
|---|---|---|
| 2026-09-03 | Match state is in-memory only: a restart drops every match in progress, and the app cannot run more than one replica (a second one would serve requests from an empty match list). `deploy/k8s/deployment.yaml` pins `replicas: 1` because of this. Sharing state is a decision nobody has made — see `docs/product.md`. | Open |
| 2026-09-03 | Only two roscos ship (`app/data/roscos.json`), so players who play repeatedly will see the same questions. Adding more is content work, not a code change. | Open |
| 2026-09-03 | Answer matching is exact after normalisation (case, accents, punctuation, `ñ`→`n`): a typo or a legitimate synonym that isn't in `accepted` counts as a miss. There is no fuzzy matching and no human override. | Open |
| 2026-09-03 | Both players share one browser, so nothing stops a player from reading the opponent's clue on screen. The design assumes a single shared screen and players who take turns honestly. | Open |
| 2026-09-03 | No HTTPS and no authentication of any kind. Fine for `127.0.0.1` and for a cluster-internal ClusterIP; anything more exposed needs a real decision first. | Open |
| 2026-09-03 | `docker-compose.yml` has no HTTP timeout/rate limit in front of the app. The state cap (`MAX_GAMES`) bounds memory, but a determined client can still keep the process busy. Acceptable for a loopback-only prototype. | Open |
| 2026-09-03 | The k3s/Ansible control plane, the Helm chart and the PrestaShop storefront that this repository previously carried were removed when it was repurposed (ADR-0006), along with ADRs 0002–0005 that described them. They live on in the template repository this project was copied from (`procomitsolutions/template_proyectos`), not in this repository's history, which starts with the game. | Resolved (deliberate removal, 2026-09-03) |
| 2026-09-03 | The judge token (ADR-0007) is a per-match shared secret, not authentication: anyone who gets the link can see the answers and play the match, and it travels as a URL fragment and a query parameter, so it can end up in a proxy or access log. Acceptable for a room where the judge is standing next to the operator; a real fix means real accounts. | Open |
| 2026-09-03 | The judge token is returned exactly once, in the match-creation response. If the link is lost there is no way to recover it — the match has to be restarted. | Open |
| 2026-09-03 | The board discovers the judge's rulings by polling once a second, so it can lag a click by up to that long, and every open board adds one request per second. No websockets, deliberately. | Open |
| 2026-09-03 | A ruling cannot be undone: a misclick on *correcto*/*fallo* costs that letter for good. | Open |
| 2026-09-03 | Generated category banks (`make rosco`, ADR-0008) are validated mechanically — letters, duplicates, clues that leak their answer — but **nothing checks that an answer is true**. The file records `"reviewed_by_a_human": false` and nothing ever flips it; a reviewer who skims is the whole of the defence, and in judge mode a wrong answer is read out as authoritative. | Open |
| 2026-09-03 | Adding a category needs an API key and a person with the repository: a user of a deployed instance cannot create one. Deliberate (ADR-0008), but it means "por categoría" only offers what someone generated and committed beforehand. | Open |
| 2026-09-03 | `make rosco` costs money per run and can fail to converge; it gives up after `--attempts` repair rounds rather than writing a broken rosco. There is no cost cap in the script. | Open |
| 2026-09-04 | The twenty category banks shipped on 2026-09-04 were written in-session by the model rather than by `scripts/generate_rosco.py` (this machine has no `ANTHROPIC_API_KEY`). They pass `validate_rosco` like any other bank, and like any other generated bank their facts are unverified: every file still says `"reviewed_by_a_human": false`. | Open |
| 2026-09-04 | "Pasapalabra Original V1–V10" are ten general-knowledge roscos written in the style of the television programme, not transcriptions of roscos actually broadcast. | Open |
| 2026-09-04 | A category still ships exactly two roscos, so two matches in the same category repeat the questions with the roles swapped. Fine for a one-off competition, thin for a long tournament. | Open |
