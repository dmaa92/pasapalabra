"""The question bank is content, so the tests here are about its shape:
a wrong letter or a duplicated answer is a game bug, not a typo."""
import unittest

from app.content import (KIND_CONTAINS, KIND_STARTS_WITH, LETTERS, normalize,
                         load_roscos)


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


class TestQuestionBank(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roscos = load_roscos()

    def test_there_are_at_least_two_roscos_so_players_never_share_one(self):
        self.assertGreaterEqual(len(self.roscos), 2)

    def test_rosco_ids_are_unique(self):
        ids = [rosco.id for rosco in self.roscos]
        self.assertCountEqual(ids, set(ids))

    def test_every_rosco_covers_every_letter_in_order(self):
        for rosco in self.roscos:
            with self.subTest(rosco=rosco.id):
                self.assertEqual(tuple(q.letter for q in rosco.questions), LETTERS)

    def test_answers_match_the_letter_they_are_filed_under(self):
        for rosco in self.roscos:
            for question in rosco.questions:
                with self.subTest(rosco=rosco.id, letter=question.letter):
                    answer = question.answer.lower()
                    letter = question.letter.lower()
                    if question.kind == KIND_STARTS_WITH:
                        self.assertTrue(
                            normalize(answer).startswith(normalize(letter)),
                            f"{answer!r} does not start with {letter!r}",
                        )
                    else:
                        self.assertEqual(question.kind, KIND_CONTAINS)
                        self.assertIn(letter, answer)

    def test_every_question_has_a_clue_and_an_answer(self):
        for rosco in self.roscos:
            for question in rosco.questions:
                with self.subTest(rosco=rosco.id, letter=question.letter):
                    self.assertGreater(len(question.clue.strip()), 10)
                    self.assertTrue(question.answer.strip())

    def test_answers_are_not_repeated_inside_a_rosco(self):
        for rosco in self.roscos:
            answers = [normalize(q.answer) for q in rosco.questions]
            with self.subTest(rosco=rosco.id):
                self.assertCountEqual(answers, set(answers))

    def test_the_clue_never_gives_the_answer_away(self):
        for rosco in self.roscos:
            for question in rosco.questions:
                with self.subTest(rosco=rosco.id, letter=question.letter):
                    self.assertNotIn(normalize(question.answer), normalize(question.clue))

    def test_matching_accepts_the_declared_variants(self):
        for rosco in self.roscos:
            for question in rosco.questions:
                with self.subTest(rosco=rosco.id, letter=question.letter):
                    self.assertTrue(question.matches(question.answer.upper()))
                    for variant in question.accepted:
                        self.assertTrue(question.matches(variant))
                    self.assertFalse(question.matches(""))


if __name__ == "__main__":
    unittest.main()
