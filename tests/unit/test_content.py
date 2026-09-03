"""The question bank is content, so the tests here are about its shape.

`validate_rosco` is the single statement of what "playable" means: these
tests hold it to its own rules, then hold every shipped rosco to it. The
generator in `scripts/generate_rosco.py` calls the same function, so a
generated bank cannot enter the repository under a laxer standard than
the hand-written one. (That script isn't imported here: it needs the
Anthropic SDK, which only the Dockerfile `tools` stage installs.)
"""
import unittest

from app.content import (DEFAULT_CATEGORY, KIND_CONTAINS, KIND_STARTS_WITH,
                         LETTERS, Question, Rosco, by_category, load_roscos,
                         normalize, slugify, validate_rosco)


def question(letter, answer, clue="Una definición suficientemente larga.",
             kind=KIND_STARTS_WITH):
    return Question(letter=letter, kind=kind, clue=clue, answer=answer)


def default_questions():
    """One valid question per letter. The numeric suffix keeps the answers
    distinct after normalisation, which folds 'ñ' onto 'n'."""
    return [question(letter, f"{letter.lower()}ejemplo{index}")
            for index, letter in enumerate(LETTERS)]


def rosco(questions=None, category="test"):
    """A rosco that validates, unless a test breaks it on purpose."""
    return Rosco(
        id="t1", name="Test", category=category,
        questions=tuple(questions if questions is not None else default_questions()),
    )


class TestNormalize(unittest.TestCase):
    def test_folds_case_accents_and_punctuation(self):
        self.assertEqual(normalize("  Delfín!  "), "delfin")
        self.assertEqual(normalize("RAÍZ"), "raiz")

    def test_folds_enye_so_a_keyboard_without_it_still_works(self):
        self.assertEqual(normalize("año"), normalize("ano"))

    def test_collapses_inner_whitespace(self):
        self.assertEqual(normalize("oso   polar"), "oso polar")

    def test_empty_input_normalizes_to_empty(self):
        self.assertEqual(normalize("   "), "")

    def test_slugify_makes_a_url_and_filename_safe_category(self):
        self.assertEqual(slugify("Cine Español"), "cine-espanol")
        self.assertEqual(slugify("  historia   antigua "), "historia-antigua")


class TestValidator(unittest.TestCase):
    def test_a_well_formed_rosco_has_no_problems(self):
        self.assertEqual(validate_rosco(rosco()), [])

    def test_a_missing_or_reordered_letter_is_a_problem(self):
        short = rosco(default_questions()[:-1])
        self.assertTrue(any("letters must be" in p for p in validate_rosco(short)))

    def test_an_answer_that_does_not_start_with_its_letter_is_a_problem(self):
        questions = default_questions()
        questions[0] = question("A", "zorro")
        problems = validate_rosco(rosco(questions))
        self.assertTrue(any("does not start with" in p for p in problems))

    def test_a_contains_answer_must_really_contain_the_letter(self):
        questions = default_questions()
        questions[13] = question("Ñ", "casa", kind=KIND_CONTAINS)
        problems = validate_rosco(rosco(questions))
        self.assertTrue(any("does not contain" in p for p in problems))

    def test_a_repeated_answer_is_a_problem(self):
        questions = default_questions()
        questions[1] = question("B", "aejemplo0")
        problems = validate_rosco(rosco(questions))
        self.assertTrue(any("repeats the answer" in p for p in problems))

    def test_a_clue_that_gives_the_answer_away_is_a_problem(self):
        questions = default_questions()
        questions[0] = question("A", "naranja", clue="Fruto de color anaranjado y jugoso.")
        problems = validate_rosco(rosco(questions))
        self.assertTrue(any("gives" in p for p in problems))

    def test_a_too_short_clue_is_a_problem(self):
        questions = default_questions()
        questions[0] = question("A", "aejemplo0", clue="Corta.")
        problems = validate_rosco(rosco(questions))
        self.assertTrue(any("too short" in p for p in problems))

    def test_an_unknown_kind_is_a_problem(self):
        questions = default_questions()
        questions[0] = question("A", "aejemplo0", kind="adivina")
        problems = validate_rosco(rosco(questions))
        self.assertTrue(any("unknown kind" in p for p in problems))


class TestShippedBanks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roscos = load_roscos()

    def test_every_shipped_rosco_is_playable(self):
        for entry in self.roscos:
            with self.subTest(rosco=entry.id):
                self.assertEqual(validate_rosco(entry), [])

    def test_rosco_ids_are_unique(self):
        ids = [entry.id for entry in self.roscos]
        self.assertCountEqual(ids, set(ids))

    def test_every_category_has_two_roscos_so_players_never_share_one(self):
        for category, entries in by_category(self.roscos).items():
            with self.subTest(category=category):
                self.assertGreaterEqual(len(entries), 2)

    def test_the_built_in_bank_is_the_general_category(self):
        self.assertIn(DEFAULT_CATEGORY, by_category(self.roscos))

    def test_matching_accepts_the_declared_variants(self):
        for entry in self.roscos:
            for q in entry.questions:
                with self.subTest(rosco=entry.id, letter=q.letter):
                    self.assertTrue(q.matches(q.answer.upper()))
                    for variant in q.accepted:
                        self.assertTrue(q.matches(variant))
                    self.assertFalse(q.matches(""))

    def test_kinds_are_the_two_the_game_knows(self):
        for entry in self.roscos:
            for q in entry.questions:
                with self.subTest(rosco=entry.id, letter=q.letter):
                    self.assertIn(q.kind, (KIND_STARTS_WITH, KIND_CONTAINS))


if __name__ == "__main__":
    unittest.main()
