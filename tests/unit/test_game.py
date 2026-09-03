"""Rules tests. Time is injected, never slept on: every call takes the
monotonic `now` the server would have passed."""
import unittest

from app.content import Question, Rosco
from app.game import (CORRECT, DEFAULT_TIME_SECONDS, FINISH_ROSCO,
                      FINISH_TIMEOUT, MODE_JUDGE, MODE_KEYBOARD, PENDING,
                      WRONG, Game, GameOver, WrongMode)

LETTERS = ("A", "B", "C")


def rosco(identifier):
    return Rosco(
        id=identifier,
        name=identifier,
        questions=tuple(
            Question(letter=letter, kind="empieza", clue=f"pista {letter}",
                     answer=f"{letter.lower()}nswer")
            for letter in LETTERS
        ),
    )


def new_game(seconds=DEFAULT_TIME_SECONDS, now=0.0):
    return Game.create(("Uno", "Dos"), (rosco("r1"), rosco("r2")),
                       now=now, seconds=seconds)


class TestTurnFlow(unittest.TestCase):
    def test_a_new_game_starts_with_the_first_player_on_the_first_letter(self):
        game = new_game()
        self.assertEqual(game.turn, 0)
        self.assertEqual(game.active.question.letter, "A")
        self.assertFalse(game.over)

    def test_a_hit_keeps_the_turn_and_advances_the_letter(self):
        game = new_game()
        result = game.answer("answer", now=1.0)
        self.assertTrue(result["correct"])
        self.assertEqual(game.turn, 0)
        self.assertEqual(game.active.question.letter, "B")

    def test_a_miss_hands_over_the_turn_and_reveals_the_solution(self):
        game = new_game()
        result = game.answer("nope", now=1.0)
        self.assertFalse(result["correct"])
        self.assertEqual(result["solution"], "answer")
        self.assertEqual(game.turn, 1)
        self.assertEqual(game.players[0].letters[0].status, WRONG)

    def test_pasapalabra_hands_over_the_turn_and_keeps_the_letter_pending(self):
        game = new_game()
        game.skip(now=1.0)
        self.assertEqual(game.turn, 1)
        player = game.players[0]
        self.assertEqual(player.letters[0].status, PENDING)
        self.assertEqual(player.question.letter, "B")

    def test_a_skipped_letter_comes_back_around(self):
        game = new_game()
        game.skip(now=1.0)          # player 0 passes on A
        game.skip(now=2.0)          # player 1 passes on A
        game.answer("bnswer", 3.0)  # player 0 hits B
        game.answer("cnswer", 4.0)  # player 0 hits C
        self.assertEqual(game.active.question.letter, "A")

    def test_answers_are_case_and_accent_insensitive(self):
        game = new_game()
        self.assertTrue(game.answer("  ÁNSWER ", now=1.0)["correct"])


class TestClock(unittest.TestCase):
    def test_only_the_active_players_clock_runs(self):
        game = new_game(seconds=100.0)
        game.sync(now=10.0)
        self.assertAlmostEqual(game.players[0].remaining, 90.0)
        self.assertAlmostEqual(game.players[1].remaining, 100.0)

    def test_time_stops_being_charged_after_the_turn_changes(self):
        game = new_game(seconds=100.0)
        game.answer("nope", now=10.0)   # player 0 spends 10s and loses the turn
        game.sync(now=40.0)             # 30s later, all of it player 1's
        self.assertAlmostEqual(game.players[0].remaining, 90.0)
        self.assertAlmostEqual(game.players[1].remaining, 70.0)

    def test_running_out_of_time_finishes_that_player_and_passes_the_turn(self):
        game = new_game(seconds=30.0)
        game.sync(now=31.0)
        player = game.players[0]
        self.assertTrue(player.finished)
        self.assertEqual(player.finish_reason, FINISH_TIMEOUT)
        self.assertEqual(player.remaining, 0.0)
        self.assertEqual(game.turn, 1)
        self.assertFalse(game.over)

    def test_the_survivor_keeps_playing_alone(self):
        game = new_game(seconds=30.0)
        game.sync(now=31.0)             # player 0 times out
        game.answer("nope", now=32.0)   # player 1 misses, but is alone
        self.assertEqual(game.turn, 1)
        self.assertFalse(game.over)

    def test_the_game_ends_when_both_clocks_are_spent(self):
        game = new_game(seconds=30.0)
        game.sync(now=31.0)   # player 0 out
        game.sync(now=62.0)   # player 1 out
        self.assertTrue(game.over)
        with self.assertRaises(GameOver):
            game.answer("answer", now=63.0)


class TestFinishing(unittest.TestCase):
    def _close_rosco(self, game, player_index, start):
        """Answer every letter of the given player correctly."""
        now = start
        while not game.players[player_index].finished:
            self.assertEqual(game.turn, player_index)
            answer = game.active.question.answer
            now += 1.0
            game.answer(answer, now=now)
        return now

    def test_closing_the_rosco_finishes_that_player_and_passes_the_turn(self):
        game = new_game()
        self._close_rosco(game, 0, start=0.0)
        player = game.players[0]
        self.assertTrue(player.finished)
        self.assertEqual(player.finish_reason, FINISH_ROSCO)
        self.assertEqual(player.count(CORRECT), len(LETTERS))
        self.assertEqual(game.turn, 1)
        self.assertFalse(game.over)

    def test_resigning_closes_the_rosco_early(self):
        game = new_game()
        game.resign(now=1.0)
        self.assertTrue(game.players[0].finished)
        self.assertEqual(game.players[0].finish_reason, FINISH_ROSCO)
        self.assertEqual(game.turn, 1)

    def test_the_player_with_more_hits_wins(self):
        game = new_game()
        game.answer("answer", now=1.0)   # 0 hits A
        game.answer("nope", now=2.0)     # 0 misses B, turn to 1
        game.resign(now=3.0)             # 1 stops with nothing
        game.resign(now=4.0)             # 0 stops too
        self.assertTrue(game.over)
        self.assertEqual(game.winner, 0)

    def test_a_tie_on_hits_is_broken_by_fewer_misses(self):
        game = new_game()
        game.answer("answer", now=1.0)   # 0 hits A
        game.answer("nope", now=2.0)     # 0 misses B, turn to 1
        game.answer("answer", now=3.0)   # 1 hits A
        game.resign(now=4.0)             # 1 stops: 1 hit, 0 misses
        game.resign(now=5.0)             # 0 stops: 1 hit, 1 miss
        self.assertEqual(game.winner, 1)

    def test_an_identical_scoreline_is_a_draw(self):
        game = new_game()
        game.answer("answer", now=1.0)
        game.resign(now=2.0)
        game.answer("answer", now=3.0)
        game.resign(now=4.0)
        self.assertTrue(game.over)
        self.assertIsNone(game.winner)


class TestModes(unittest.TestCase):
    def judged_game(self, seconds=DEFAULT_TIME_SECONDS):
        return Game.create(("Uno", "Dos"), (rosco("r1"), rosco("r2")),
                           now=0.0, seconds=seconds, mode=MODE_JUDGE,
                           judge_token="secreto")

    def test_matches_are_played_from_the_keyboard_by_default(self):
        self.assertEqual(new_game().mode, MODE_KEYBOARD)

    def test_an_unknown_mode_is_rejected(self):
        with self.assertRaises(ValueError):
            Game.create(("Uno", "Dos"), (rosco("r1"), rosco("r2")),
                        now=0.0, mode="arbitro")

    def test_a_judged_match_does_not_take_typed_answers(self):
        game = self.judged_game()
        with self.assertRaises(WrongMode):
            game.answer("answer", now=1.0)

    def test_a_keyboard_match_does_not_take_rulings(self):
        with self.assertRaises(WrongMode):
            new_game().judge(True, now=1.0)

    def test_the_judge_scoring_a_hit_keeps_the_turn(self):
        game = self.judged_game()
        result = game.judge(True, now=1.0)
        self.assertTrue(result["correct"])
        self.assertEqual(result["letter"], "A")
        self.assertIsNone(result["solution"])
        self.assertEqual(game.players[0].letters[0].status, CORRECT)
        self.assertEqual(game.turn, 0)
        self.assertEqual(game.active.question.letter, "B")

    def test_the_judge_scoring_a_miss_hands_over_the_turn(self):
        game = self.judged_game()
        result = game.judge(False, now=1.0)
        self.assertFalse(result["correct"])
        self.assertEqual(result["solution"], "answer")
        self.assertEqual(game.players[0].letters[0].status, WRONG)
        self.assertEqual(game.turn, 1)

    def test_pasapalabra_and_planting_work_the_same_when_judged(self):
        game = self.judged_game()
        game.skip(now=1.0)
        self.assertEqual(game.turn, 1)
        game.resign(now=2.0)
        self.assertTrue(game.players[1].finished)
        self.assertEqual(game.turn, 0)

    def test_clocks_run_the_same_when_judged(self):
        game = self.judged_game(seconds=30.0)
        game.sync(now=31.0)
        self.assertTrue(game.players[0].finished)
        self.assertEqual(game.players[0].finish_reason, FINISH_TIMEOUT)

    def test_a_judged_game_that_is_over_refuses_further_rulings(self):
        game = self.judged_game()
        game.resign(now=1.0)
        game.resign(now=2.0)
        self.assertTrue(game.over)
        with self.assertRaises(GameOver):
            game.judge(True, now=3.0)


if __name__ == "__main__":
    unittest.main()
