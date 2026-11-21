"""model 模块单元测试：钉点坐标、分页、题库与参数边界。"""

from __future__ import annotations

import unittest

from geoboard.model import (
    BOARD_FIRST_TOP_MM,
    BOARD_MARGIN_MM,
    BOARD_SECOND_TOP_MM,
    BOARD_SIDE_MM,
    BOARD_SINGLE_TOP_MM,
    CHALLENGES,
    MAX_BOARDS,
    MAX_CHALLENGES,
    MAX_SIZE,
    MIN_BOARDS,
    MIN_CHALLENGES,
    MIN_SIZE,
    Board,
    Challenge,
    GeoboardError,
    Options,
    Peg,
    board_page_count,
    build_boards,
    challenge_page_count,
    page_count,
    select_challenges,
)


class PegTest(unittest.TestCase):
    def test_fields(self) -> None:
        peg = Peg(2, 3, 13.0, 56.0)
        self.assertEqual((peg.column, peg.row), (2, 3))
        self.assertEqual((peg.x_mm, peg.y_mm), (13.0, 56.0))

    def test_negative_column_rejected(self) -> None:
        with self.assertRaises(GeoboardError):
            Peg(-1, 0, 0.0, 0.0)

    def test_negative_row_rejected(self) -> None:
        with self.assertRaises(GeoboardError):
            Peg(0, -1, 0.0, 0.0)

    def test_bool_rejected(self) -> None:
        with self.assertRaises(GeoboardError):
            Peg(True, 0, 0.0, 0.0)  # type: ignore[arg-type]

    def test_invalid_coordinate(self) -> None:
        with self.assertRaises(GeoboardError):
            Peg(0, 0, "13", 0.0)  # type: ignore[arg-type]


class BoardTest(unittest.TestCase):
    def make(self, size: int = 5) -> Board:
        return build_boards(size=size, count=1)[0]

    def test_peg_count(self) -> None:
        self.assertEqual(len(self.make(5).pegs), 25)

    def test_peg_count_all_sizes(self) -> None:
        for size in range(MIN_SIZE, MAX_SIZE + 1):
            board = self.make(size)
            self.assertEqual(len(board.pegs), size * size)

    def test_spacing(self) -> None:
        board = self.make(5)
        self.assertAlmostEqual(board.spacing_mm, 21.5)
        self.assertAlmostEqual(board.spacing_mm, (112.0 - 26.0) / 4)

    def test_first_peg(self) -> None:
        peg = self.make(5).peg_at(0, 0)
        self.assertAlmostEqual(peg.x_mm, BOARD_MARGIN_MM)
        self.assertAlmostEqual(peg.y_mm, BOARD_MARGIN_MM)

    def test_last_peg(self) -> None:
        peg = self.make(5).peg_at(4, 4)
        self.assertAlmostEqual(peg.x_mm, 112.0 - BOARD_MARGIN_MM)
        self.assertAlmostEqual(peg.y_mm, 112.0 - BOARD_MARGIN_MM)

    def test_lattice_inside_margin(self) -> None:
        board = self.make(10)
        for peg in board.pegs:
            self.assertGreaterEqual(peg.x_mm, BOARD_MARGIN_MM - 1e-9)
            self.assertGreaterEqual(peg.y_mm, BOARD_MARGIN_MM - 1e-9)
            self.assertLessEqual(peg.x_mm, board.side_mm - BOARD_MARGIN_MM + 1e-9)
            self.assertLessEqual(peg.y_mm, board.side_mm - BOARD_MARGIN_MM + 1e-9)

    def test_rows_share_x_positions(self) -> None:
        board = self.make(6)
        xs = [peg.x_mm for peg in board.pegs if peg.row == 0]
        for row in range(1, 6):
            row_xs = [peg.x_mm for peg in board.pegs if peg.row == row]
            self.assertEqual(len(row_xs), 6)
            for first, second in zip(xs, row_xs):
                self.assertAlmostEqual(first, second)

    def test_columns_share_y_positions(self) -> None:
        board = self.make(4)
        ys = [peg.y_mm for peg in board.pegs if peg.column == 3]
        self.assertEqual(ys, sorted(ys))
        self.assertEqual(len(set(round(value, 6) for value in ys)), 4)

    def test_pegs_unique(self) -> None:
        board = self.make(8)
        keys = {(peg.column, peg.row) for peg in board.pegs}
        self.assertEqual(len(keys), 64)

    def test_peg_at(self) -> None:
        board = self.make(5)
        peg = board.peg_at(2, 3)
        self.assertEqual((peg.column, peg.row), (2, 3))
        self.assertAlmostEqual(peg.x_mm, 13.0 + 2 * 21.5)
        self.assertAlmostEqual(peg.y_mm, 13.0 + 3 * 21.5)

    def test_peg_at_bounds(self) -> None:
        board = self.make(5)
        with self.assertRaises(GeoboardError):
            board.peg_at(5, 0)
        with self.assertRaises(GeoboardError):
            board.peg_at(0, 5)

    def test_peg_at_negative(self) -> None:
        with self.assertRaises(GeoboardError):
            self.make(5).peg_at(-1, 0)

    def test_peg_at_bool(self) -> None:
        with self.assertRaises(GeoboardError):
            self.make(5).peg_at(True, 0)  # type: ignore[arg-type]

    def test_label(self) -> None:
        self.assertEqual(self.make(3).label, "钉点数 3×3")
        self.assertEqual(self.make(10).label, "钉点数 10×10")

    def test_invalid_size(self) -> None:
        for size in (MIN_SIZE - 1, MAX_SIZE + 1):
            with self.assertRaises(GeoboardError):
                build_boards(size=size, count=1)

    def test_invalid_size_type(self) -> None:
        with self.assertRaises(GeoboardError):
            build_boards(size="5", count=1)  # type: ignore[arg-type]
        with self.assertRaises(GeoboardError):
            build_boards(size=True, count=1)  # type: ignore[arg-type]

    def test_invalid_margin(self) -> None:
        with self.assertRaises(GeoboardError):
            Board(5, 1, 1, 49.0, 32.0, margin_mm=0.0)
        with self.assertRaises(GeoboardError):
            Board(5, 1, 1, 49.0, 32.0, margin_mm=60.0)

    def test_invalid_side(self) -> None:
        with self.assertRaises(GeoboardError):
            Board(5, 1, 1, 49.0, 32.0, side_mm=0.0)

    def test_invalid_origin(self) -> None:
        with self.assertRaises(GeoboardError):
            Board(5, 1, 1, -1.0, 32.0)
        with self.assertRaises(GeoboardError):
            Board(5, 1, 1, 49.0, 200.0)

    def test_invalid_index_and_page(self) -> None:
        with self.assertRaises(GeoboardError):
            Board(5, 0, 1, 49.0, 32.0)
        with self.assertRaises(GeoboardError):
            Board(5, 1, 0, 49.0, 32.0)

    def test_page_position(self) -> None:
        board = build_boards(size=5, count=2)[1]
        x, y = board.peg_page_position(0, 0)
        self.assertAlmostEqual(x, 49.0 + 13.0)
        self.assertAlmostEqual(y, BOARD_SECOND_TOP_MM + 13.0)
        self.assertLess(y + BOARD_SIDE_MM, 297.0)


class BuildBoardsTest(unittest.TestCase):
    def test_count(self) -> None:
        for count in range(MIN_BOARDS, MAX_BOARDS + 1):
            self.assertEqual(len(build_boards(size=5, count=count)), count)

    def test_single_board_centered(self) -> None:
        board = build_boards(size=5, count=1)[0]
        self.assertEqual(board.page, 1)
        self.assertAlmostEqual(board.origin_x_mm, 49.0)
        self.assertAlmostEqual(board.origin_y_mm, BOARD_SINGLE_TOP_MM)

    def test_two_boards_one_page(self) -> None:
        boards = build_boards(size=5, count=2)
        self.assertEqual([board.page for board in boards], [1, 1])
        self.assertAlmostEqual(boards[0].origin_y_mm, BOARD_FIRST_TOP_MM)
        self.assertAlmostEqual(boards[1].origin_y_mm, BOARD_SECOND_TOP_MM)

    def test_three_boards_paginate(self) -> None:
        boards = build_boards(size=5, count=3)
        self.assertEqual([board.page for board in boards], [1, 1, 2])
        self.assertAlmostEqual(boards[2].origin_y_mm, BOARD_SINGLE_TOP_MM)

    def test_four_boards_paginate(self) -> None:
        boards = build_boards(size=5, count=4)
        self.assertEqual([board.page for board in boards], [1, 1, 2, 2])
        self.assertEqual([board.index for board in boards], [1, 2, 3, 4])

    def test_boards_do_not_overlap(self) -> None:
        boards = build_boards(size=5, count=2)
        first_bottom = boards[0].origin_y_mm + boards[0].side_mm
        self.assertLess(first_bottom, boards[1].origin_y_mm)

    def test_all_boards_inside_page(self) -> None:
        for board in build_boards(size=5, count=4):
            self.assertGreaterEqual(board.origin_x_mm, 0.0)
            self.assertGreaterEqual(board.origin_y_mm, 0.0)
            self.assertLessEqual(board.origin_x_mm + board.side_mm, 210.0)
            self.assertLessEqual(board.origin_y_mm + board.side_mm, 297.0)

    def test_size_preserved(self) -> None:
        for board in build_boards(size=7, count=4):
            self.assertEqual(board.size, 7)
            self.assertEqual(len(board.pegs), 49)

    def test_invalid_count(self) -> None:
        for count in (0, MAX_BOARDS + 1):
            with self.assertRaises(GeoboardError):
                build_boards(size=5, count=count)

    def test_invalid_count_type(self) -> None:
        with self.assertRaises(GeoboardError):
            build_boards(size=5, count=True)  # type: ignore[arg-type]


class ChallengeBankTest(unittest.TestCase):
    def test_bank_size(self) -> None:
        self.assertGreaterEqual(len(CHALLENGES), 12)

    def test_codes_unique(self) -> None:
        codes = [card.code for card in CHALLENGES]
        self.assertEqual(len(codes), len(set(codes)))

    def test_prompts_unique(self) -> None:
        prompts = [card.prompt for card in CHALLENGES]
        self.assertEqual(len(prompts), len(set(prompts)))

    def test_difficulty_range(self) -> None:
        for card in CHALLENGES:
            self.assertIn(card.difficulty, (1, 2, 3))

    def test_skills(self) -> None:
        skills = {card.skill for card in CHALLENGES}
        self.assertEqual(skills, {"面积", "周长", "图形"})

    def test_area_and_perimeter_exist(self) -> None:
        prompts = "".join(card.prompt for card in CHALLENGES)
        self.assertIn("面积", prompts)
        self.assertIn("周长", prompts)

    def test_no_answers(self) -> None:
        for card in CHALLENGES:
            self.assertNotIn("答案", card.prompt)
            self.assertNotIn("解法", card.prompt)

    def test_prompts_are_questions(self) -> None:
        for card in CHALLENGES:
            self.assertTrue(card.prompt.startswith("画一个"))
            self.assertTrue(card.prompt.endswith("。"))

    def test_all_difficulties_used(self) -> None:
        levels = {card.difficulty for card in CHALLENGES}
        self.assertEqual(levels, {1, 2, 3})

    def test_invalid_challenge(self) -> None:
        with self.assertRaises(GeoboardError):
            Challenge("", "画一个图形。", "面积", 1)
        with self.assertRaises(GeoboardError):
            Challenge("X1", "", "面积", 1)
        with self.assertRaises(GeoboardError):
            Challenge("X1", "画一个图形。", "体积", 1)
        with self.assertRaises(GeoboardError):
            Challenge("X1", "画一个图形。", "面积", 4)


class SelectChallengesTest(unittest.TestCase):
    def test_count(self) -> None:
        for count in range(0, 9):
            self.assertEqual(len(select_challenges(count, 42)), count)

    def test_zero(self) -> None:
        self.assertEqual(select_challenges(0, 42), ())

    def test_reproducible(self) -> None:
        first = select_challenges(8, 42)
        second = select_challenges(8, 42)
        self.assertEqual(first, second)

    def test_same_prefix(self) -> None:
        full = select_challenges(len(CHALLENGES), 7)
        self.assertEqual(select_challenges(4, 7), full[:4])

    def test_seed_changes_order(self) -> None:
        first = select_challenges(len(CHALLENGES), 1)
        second = select_challenges(len(CHALLENGES), 2)
        self.assertNotEqual(first, second)

    def test_selects_from_bank(self) -> None:
        selected = select_challenges(8, 42)
        self.assertEqual(len(set(card.code for card in selected)), 8)
        for card in selected:
            self.assertIn(card, CHALLENGES)

    def test_invalid_count(self) -> None:
        for count in (-1, len(CHALLENGES) + 1):
            with self.assertRaises(GeoboardError):
                select_challenges(count, 42)

    def test_invalid_seed(self) -> None:
        with self.assertRaises(GeoboardError):
            select_challenges(4, "42")  # type: ignore[arg-type]


class PageCountTest(unittest.TestCase):
    def test_board_pages(self) -> None:
        self.assertEqual(board_page_count(1), 1)
        self.assertEqual(board_page_count(2), 1)
        self.assertEqual(board_page_count(3), 2)
        self.assertEqual(board_page_count(4), 2)

    def test_challenge_pages(self) -> None:
        self.assertEqual(challenge_page_count(0), 0)
        self.assertEqual(challenge_page_count(1), 1)
        self.assertEqual(challenge_page_count(4), 1)
        self.assertEqual(challenge_page_count(5), 2)
        self.assertEqual(challenge_page_count(8), 2)

    def test_total(self) -> None:
        self.assertEqual(page_count(1, 0), 1)
        self.assertEqual(page_count(2, 4), 2)
        self.assertEqual(page_count(3, 4), 3)
        self.assertEqual(page_count(4, 8), 4)

    def test_invalid(self) -> None:
        with self.assertRaises(GeoboardError):
            board_page_count(0)
        with self.assertRaises(GeoboardError):
            challenge_page_count(MAX_CHALLENGES + 1)
        with self.assertRaises(GeoboardError):
            page_count(0, 0)


class OptionsTest(unittest.TestCase):
    def test_defaults(self) -> None:
        options = Options()
        self.assertEqual(
            (options.size, options.boards, options.challenges, options.seed),
            (5, 2, 4, 42),
        )
        self.assertEqual(options.title, "几何钉板")
        self.assertEqual(options.page_count, 2)

    def test_size_bounds(self) -> None:
        for size in (MIN_SIZE, MAX_SIZE):
            self.assertEqual(Options(size=size).size, size)

    def test_invalid_size(self) -> None:
        for size in (MIN_SIZE - 1, MAX_SIZE + 1):
            with self.assertRaises(GeoboardError):
                Options(size=size)

    def test_boards_bounds(self) -> None:
        for count in (MIN_BOARDS, MAX_BOARDS):
            self.assertEqual(Options(boards=count).boards, count)

    def test_invalid_boards(self) -> None:
        for count in (MIN_BOARDS - 1, MAX_BOARDS + 1):
            with self.assertRaises(GeoboardError):
                Options(boards=count)

    def test_challenges_bounds(self) -> None:
        for count in (MIN_CHALLENGES, MAX_CHALLENGES):
            self.assertEqual(Options(challenges=count).challenges, count)

    def test_invalid_challenges(self) -> None:
        for count in (MIN_CHALLENGES - 1, MAX_CHALLENGES + 1):
            with self.assertRaises(GeoboardError):
                Options(challenges=count)

    def test_title_stripped(self) -> None:
        self.assertEqual(Options(title="  几何钉板  ").title, "几何钉板")

    def test_empty_title(self) -> None:
        with self.assertRaises(GeoboardError):
            Options(title="   ")

    def test_title_too_long(self) -> None:
        with self.assertRaises(GeoboardError):
            Options(title="钉" * 41)

    def test_title_type(self) -> None:
        with self.assertRaises(GeoboardError):
            Options(title=123)  # type: ignore[arg-type]

    def test_seed_type(self) -> None:
        with self.assertRaises(GeoboardError):
            Options(seed="42")  # type: ignore[arg-type]
        with self.assertRaises(GeoboardError):
            Options(seed=True)  # type: ignore[arg-type]

    def test_page_count_matrix(self) -> None:
        self.assertEqual(Options(boards=1, challenges=0).page_count, 1)
        self.assertEqual(Options(boards=3, challenges=1).page_count, 3)
        self.assertEqual(Options(boards=4, challenges=8).page_count, 4)


if __name__ == "__main__":
    unittest.main()
