"""Hold every question bank in app/data to validate_rosco.

Same rules the tests apply, but reachable from the `tools` service, which
mounts app/data read-write — so a bank being drafted can be checked before
it is baked into the image.

    docker compose run --rm --no-deps tools python -m scripts.check_banks
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.content import load_file, normalize, validate_rosco  # noqa: E402


def main() -> int:
    problems_found = 0
    for path in sorted(pathlib.Path("app/data").rglob("*.json")):
        roscos = load_file(path)
        for rosco in roscos:
            for problem in validate_rosco(rosco):
                problems_found += 1
                print(f"{path.name}: {problem}")
        # Not a rule of the game, but a fairness one: the two roscos of a
        # category should not share answers.
        if len(roscos) >= 2:
            answers = [set(normalize(q.answer) for q in r.questions) for r in roscos]
            shared = answers[0] & answers[1]
            if shared:
                problems_found += 1
                print(f"{path.name}: answers shared by both roscos: {sorted(shared)}")
        print(f"{path.name}: {len(roscos)} roscos, "
              f"{sum(len(r.questions) for r in roscos)} preguntas")
    print("TODO OK" if not problems_found else f"{problems_found} PROBLEMA(S)")
    return 1 if problems_found else 0


if __name__ == "__main__":
    raise SystemExit(main())
