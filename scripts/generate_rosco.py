"""Draft a rosco for a category with Claude, then hold it to the same
rules the shipped questions are held to.

This is an authoring tool, not part of the game: it runs on a developer's
machine, needs an API key, and writes a file that a human is expected to
read before committing. The application never calls it and never needs a
key — see docs/decisions/0008-generated-category-roscos.md.

    make rosco CATEGORIA="cine español"

What the validator can settle is mechanical: the right letters in the
right order, answers that really start with (or contain) their letter,
no repeats, no clue that gives its own answer away. Whether an answer is
*true* is not mechanical. Read the file before you commit it.
"""
from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys

import anthropic

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.content import (GENERATED_DIR, KIND_CONTAINS, KIND_STARTS_WITH,  # noqa: E402
                         LETTERS, MIN_CLUE_LENGTH, Question, Rosco, normalize,
                         slugify, validate_rosco)

MODEL = "claude-opus-5"
MAX_TOKENS = 16000

SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "letter": {"type": "string"},
                    "kind": {"type": "string"},
                    "clue": {"type": "string"},
                    "answer": {"type": "string"},
                    "accepted": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["letter", "kind", "clue", "answer", "accepted"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["questions"],
    "additionalProperties": False,
}

SYSTEM = f"""Escribes preguntas para el rosco de un concurso tipo Pasapalabra, en español.

Reglas que no se negocian:
- Una pregunta por cada letra, exactamente estas y en este orden: {" ".join(LETTERS)}.
- "kind" es "{KIND_STARTS_WITH}" cuando la respuesta empieza por la letra, y
  "{KIND_CONTAINS}" cuando solo la contiene. Usa "{KIND_CONTAINS}" para la Ñ
  siempre, y para la X salvo que exista una palabra común que empiece por ella.
- La respuesta es UNA palabra o expresión, sin artículo delante.
- La definición ("clue") tiene al menos {MIN_CLUE_LENGTH} caracteres, admite una
  sola respuesta razonable, y NUNCA contiene la respuesta ni una palabra de su
  misma raíz (si la respuesta es "naranja", la pista no puede decir
  "anaranjado").
- Sin respuestas repetidas dentro del mismo rosco.
- "accepted" recoge solo variantes ortográficas legítimas de la misma respuesta
  ("bumerang" para "bumerán"); déjalo vacío si no hay ninguna.

Lo más importante: cada respuesta tiene que ser un hecho cierto y comprobable.
Si para una letra no encuentras nada sólido dentro de la categoría, usa una
pregunta de cultura general con esa letra antes que inventarte un dato."""


def draft(client: anthropic.Anthropic, prompt: str) -> list[dict]:
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        thinking={"type": "adaptive"},
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        details = response.stop_details
        raise SystemExit(
            "La API rechazó la petición"
            + (f" ({details.category}): {details.explanation}" if details else "")
        )
    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)["questions"]


def as_rosco(entries: list[dict], rosco_id: str, name: str, category: str) -> Rosco:
    return Rosco(
        id=rosco_id,
        name=name,
        category=category,
        questions=tuple(
            Question(
                letter=entry["letter"].strip().upper(),
                kind=entry["kind"].strip().lower(),
                clue=entry["clue"].strip(),
                answer=entry["answer"].strip(),
                accepted=tuple(entry.get("accepted", ())),
            )
            for entry in entries
        ),
    )


def generate_one(
    client: anthropic.Anthropic,
    category: str,
    rosco_id: str,
    name: str,
    taken: set[str],
    attempts: int,
) -> Rosco:
    """Draft a rosco and repair it until it validates, or give up."""
    avoid = ""
    if taken:
        avoid = ("\nNo uses ninguna de estas respuestas, ya están en otro rosco "
                 "de la misma categoría: " + ", ".join(sorted(taken)) + ".")
    entries = draft(client, f"Escribe el rosco completo de la categoría: {category}.{avoid}")
    by_letter = {entry["letter"].strip().upper(): entry for entry in entries}

    for attempt in range(1, attempts + 1):
        rosco = as_rosco(
            [by_letter[letter] for letter in LETTERS if letter in by_letter],
            rosco_id, name, category,
        )
        problems = validate_rosco(rosco)
        clashes = [
            f"{rosco_id}:{q.letter}: {q.answer!r} ya está usada en otro rosco"
            for q in rosco.questions if normalize(q.answer) in taken
        ]
        missing = [letter for letter in LETTERS if letter not in by_letter]
        problems = problems + clashes + [f"falta la letra {l}" for l in missing]
        if not problems:
            return rosco

        print(f"  intento {attempt}: {len(problems)} problema(s), pidiendo arreglo")
        for problem in problems:
            print(f"    - {problem}")
        if attempt == attempts:
            break

        broken = sorted({p.split(":")[1] for p in problems if ":" in p} | set(missing))
        fix = draft(client, (
            f"Categoría: {category}.{avoid}\n"
            f"Estas entradas del rosco no cumplen las reglas:\n"
            + "\n".join(f"- {p}" for p in problems)
            + f"\n\nDevuelve SOLO entradas nuevas para estas letras: {' '.join(broken)}. "
              "Cambia la respuesta o la pista según haga falta."
        ))
        for entry in fix:
            by_letter[entry["letter"].strip().upper()] = entry

    raise SystemExit(
        f"No se pudo generar un rosco válido para «{category}» en {attempts} intentos."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--category", required=True, help='p. ej. "cine español"')
    parser.add_argument("--roscos", type=int, default=2,
                        help="cuántos roscos (2 es el mínimo para jugar)")
    parser.add_argument("--attempts", type=int, default=3,
                        help="intentos de arreglo por rosco antes de rendirse")
    parser.add_argument("--out", type=pathlib.Path, default=None)
    parser.add_argument("--force", action="store_true",
                        help="sobrescribe el fichero si ya existe")
    args = parser.parse_args()

    category = args.category.strip()
    slug = slugify(category)
    if not slug:
        raise SystemExit("La categoría no puede estar vacía.")
    out = args.out or GENERATED_DIR / f"{slug}.json"
    if out.exists() and not args.force:
        raise SystemExit(f"{out} ya existe. Usa --force si quieres reemplazarlo.")

    client = anthropic.Anthropic()

    taken: set[str] = set()
    roscos = []
    try:
        for number in range(1, args.roscos + 1):
            name = f"{category} {number}"
            print(f"Generando «{name}»...")
            rosco = generate_one(client, category, f"{slug}-{number}", name,
                                 taken, args.attempts)
            taken.update(normalize(q.answer) for q in rosco.questions)
            roscos.append(rosco)
    except (anthropic.AuthenticationError, TypeError) as exc:
        # The SDK raises a bare TypeError on the first request when it
        # could not resolve any credential at all.
        raise SystemExit(
            "No hay credenciales válidas para la API. Define ANTHROPIC_API_KEY\n"
            "en tu .env local (gitignored): la clave se queda en tu máquina y\n"
            f"nunca entra en la imagen que se despliega.\n  {exc}"
        )
    except anthropic.RateLimitError:
        raise SystemExit("La API está limitando la tasa de peticiones. Reinténtalo.")
    except anthropic.APIConnectionError as exc:
        raise SystemExit(f"No se pudo conectar con la API: {exc}")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "category": category,
        "generated": {
            "model": MODEL,
            "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
            "reviewed_by_a_human": False,
        },
        "roscos": [
            {
                "id": rosco.id,
                "name": rosco.name,
                "questions": [
                    {
                        "letter": q.letter,
                        "kind": q.kind,
                        "clue": q.clue,
                        "answer": q.answer,
                        **({"accepted": list(q.accepted)} if q.accepted else {}),
                    }
                    for q in rosco.questions
                ],
            }
            for rosco in roscos
        ],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\nEscrito {out} ({len(roscos)} roscos, {len(roscos) * len(LETTERS)} preguntas).")
    print("Pasa la vista por las respuestas antes de commitear: la validación")
    print("comprueba la forma, no que los datos sean ciertos.")


if __name__ == "__main__":
    main()
