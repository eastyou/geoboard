"""render 模块单元测试：SVG 尺寸、A4 分页、转义与自包含页面。"""

from __future__ import annotations

import re
import unittest

from geoboard.model import (
    BOARD_SIDE_MM,
    CHALLENGES,
    GeoboardError,
    Options,
    build_boards,
    select_challenges,
)
from geoboard.render import render_board_svg, render_html


class SvgTest(unittest.TestCase):
    def test_svg_shell(self) -> None:
        svg = render_board_svg(build_boards(size=5, count=1)[0])
        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.endswith("</svg>"))
        self.assertIn('xmlns="http://www.w3.org/2000/svg"', svg)

    def test_svg_dimensions(self) -> None:
        svg = render_board_svg(build_boards(size=5, count=1)[0])
        self.assertIn('width="112mm"', svg)
        self.assertIn('height="112mm"', svg)
        self.assertIn('viewBox="0 0 112 112"', svg)
        self.assertAlmostEqual(BOARD_SIDE_MM, 112.0)

    def test_circle_count_all_sizes(self) -> None:
        for size in range(3, 11):
            svg = render_board_svg(build_boards(size=size, count=1)[0])
            self.assertEqual(svg.count("<circle"), size * size)

    def test_frame_is_solid(self) -> None:
        svg = render_board_svg(build_boards(size=5, count=1)[0])
        self.assertIn("<rect", svg)
        self.assertIn('stroke="#1f2937"', svg)
        self.assertIn('stroke-width="0.7"', svg)
        self.assertNotIn("stroke-dasharray", svg)

    def test_pegs_inside_frame(self) -> None:
        svg = render_board_svg(build_boards(size=10, count=1)[0])
        values = re.findall(r'<circle cx="([\d.]+)" cy="([\d.]+)"', svg)
        self.assertEqual(len(values), 100)
        for x_text, y_text in values:
            self.assertGreaterEqual(float(x_text), 0.0)
            self.assertGreaterEqual(float(y_text), 0.0)
            self.assertLessEqual(float(x_text), 112.0)
            self.assertLessEqual(float(y_text), 112.0)

    def test_label_in_svg(self) -> None:
        svg = render_board_svg(build_boards(size=4, count=1)[0])
        self.assertIn("钉点数 4×4", svg)
        self.assertIn("共 16 个钉点", svg)

    def test_invalid_board(self) -> None:
        with self.assertRaises(GeoboardError):
            render_board_svg("board")  # type: ignore[arg-type]


class HtmlShellTest(unittest.TestCase):
    def test_document_shell(self) -> None:
        page = render_html(Options())
        self.assertTrue(page.startswith("<!doctype html>"))
        self.assertIn('<html lang="zh-CN">', page)
        self.assertIn('<meta charset="utf-8">', page)
        self.assertIn('<meta name="viewport"', page)
        self.assertTrue(page.endswith("</html>\n"))

    def test_title(self) -> None:
        page = render_html(Options(title="三年级几何"))
        self.assertIn("<title>三年级几何</title>", page)
        self.assertIn("三年级几何", page)

    def test_title_escaped(self) -> None:
        page = render_html(Options(title="<b>钉板&</b>"))
        self.assertIn("&lt;b&gt;钉板&amp;&lt;/b&gt;", page)
        self.assertNotIn("<b>钉板", page)

    def test_no_network_resources(self) -> None:
        page = render_html(Options())
        for marker in ("<script", "<link", "src=", "@import", "url(http"):
            self.assertNotIn(marker, page)

    def test_no_answers(self) -> None:
        page = render_html(Options(challenges=8))
        self.assertNotIn("答案", page)
        self.assertNotIn("解法", page)

    def test_invalid_options(self) -> None:
        with self.assertRaises(GeoboardError):
            render_html("options")  # type: ignore[arg-type]


class BoardPageTest(unittest.TestCase):
    def test_default_page_count(self) -> None:
        page = render_html(Options())
        self.assertEqual(page.count("<section"), 2)
        self.assertEqual(page.count("<svg"), 2)
        self.assertEqual(page.count("<circle"), 50)

    def test_board_count(self) -> None:
        for count in range(1, 5):
            page = render_html(Options(boards=count, challenges=0))
            self.assertEqual(page.count("<svg"), count)
            self.assertEqual(
                page.count("<section"), (count + 1) // 2
            )

    def test_three_boards_two_pages(self) -> None:
        page = render_html(Options(boards=3, challenges=0))
        self.assertEqual(page.count("<section"), 2)
        self.assertIn("钉板 3 · 共 3 块", page)

    def test_board_positions(self) -> None:
        page = render_html(Options(boards=2, challenges=0))
        self.assertIn("--bx:49mm;--by:32mm", page)
        self.assertIn("--bx:49mm;--by:158mm", page)

    def test_single_board_centered(self) -> None:
        page = render_html(Options(boards=1, challenges=0))
        self.assertIn("--bx:49mm;--by:88mm", page)

    def test_board_labels(self) -> None:
        page = render_html(Options(size=6, boards=2, challenges=0))
        self.assertIn("钉点数 6×6", page)
        self.assertIn("钉板 1 / 2", page)
        self.assertIn("钉板 2 / 2", page)

    def test_page_numbers(self) -> None:
        page = render_html(Options())
        self.assertIn("第 1 页 / 共 2 页", page)
        self.assertIn("第 2 页 / 共 2 页", page)

    def test_board_range_header(self) -> None:
        page = render_html(Options(boards=3, challenges=0))
        self.assertIn("钉板 1–2 · 共 3 块", page)
        self.assertIn("钉板 3 · 共 3 块", page)


class ChallengePageTest(unittest.TestCase):
    def test_card_count(self) -> None:
        for count in range(0, 9):
            page = render_html(Options(boards=1, challenges=count))
            self.assertEqual(page.count("<article"), count)

    def test_four_cards_per_page(self) -> None:
        page = render_html(Options(boards=1, challenges=8))
        self.assertEqual(page.count("<section"), 3)
        self.assertEqual(page.count("<article"), 8)
        self.assertIn("挑战卡 1–4 · 共 8 张", page)
        self.assertIn("挑战卡 5–8 · 共 8 张", page)

    def test_single_card_range(self) -> None:
        page = render_html(Options(boards=1, challenges=1))
        self.assertIn("挑战卡 1 · 共 1 张", page)
        self.assertIn("挑战 01", page)

    def test_zero_challenges(self) -> None:
        page = render_html(Options(boards=2, challenges=0))
        self.assertNotIn("面积与周长挑战", page)
        self.assertNotIn("<article", page)
        self.assertEqual(page.count("<section"), 1)

    def test_card_content(self) -> None:
        options = Options(boards=1, challenges=4, seed=42)
        page = render_html(options)
        for card in select_challenges(4, 42):
            self.assertIn(card.prompt, page)
            self.assertIn(card.skill, page)
            self.assertIn(card.code, page)

    def test_stars(self) -> None:
        page = render_html(Options(boards=1, challenges=8))
        self.assertIn("★", page)
        self.assertIn("☆", page)

    def test_dashed_cut_border(self) -> None:
        page = render_html(Options())
        self.assertIn("border: 0.45mm dashed", page)
        self.assertIn("虚线剪开", page)

    def test_seed_reproducible(self) -> None:
        first = render_html(Options(challenges=8, seed=42))
        second = render_html(Options(challenges=8, seed=42))
        self.assertEqual(first, second)

    def test_seed_changes_order(self) -> None:
        first = render_html(Options(boards=1, challenges=8, seed=1))
        second = render_html(Options(boards=1, challenges=8, seed=2))
        self.assertNotEqual(first, second)

    def test_bank_prompts_not_all_used(self) -> None:
        page = render_html(Options(boards=1, challenges=1, seed=42))
        with_card = [card for card in CHALLENGES if card.prompt in page]
        self.assertEqual(len(with_card), 1)


class PrintStyleTest(unittest.TestCase):
    def test_a4_portrait(self) -> None:
        page = render_html(Options())
        self.assertIn("@page { size: A4 portrait; margin: 0; }", page)
        self.assertIn(".sheet", page)
        self.assertIn("width: 210mm", page)
        self.assertIn("height: 297mm", page)

    def test_print_rules(self) -> None:
        page = render_html(Options())
        self.assertIn("@media print", page)
        self.assertIn("print-color-adjust: exact", page)
        self.assertIn("page-break-after: always", page)

    def test_responsive_rules(self) -> None:
        page = render_html(Options())
        self.assertIn("@media screen and (max-width: 820px)", page)
        self.assertIn("overflow-x: hidden", page)
        self.assertIn("max-width: 100%", page)

    def test_toolbar(self) -> None:
        page = render_html(Options(boards=2, challenges=4))
        self.assertIn("2 块钉板 · 4 张挑战卡 · 5×5 点阵 · 共 2 页", page)
        self.assertIn("A4 纵向", page)


if __name__ == "__main__":
    unittest.main()
