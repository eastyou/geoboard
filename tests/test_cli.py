"""cli 模块单元测试：参数边界、退出码与生成结果。"""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from typing import List, Tuple

from geoboard.cli import build_parser, main


class CliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.target = self.root / "几何钉板.html"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_cli(self, argv: List[str]) -> Tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def generate(self, extra: List[str]) -> Path:
        code, _, _ = self.run_cli(["-o", str(self.target)] + extra)
        self.assertEqual(code, 0)
        return self.target

    def test_parser_defaults(self) -> None:
        args = build_parser().parse_args([])
        self.assertEqual(
            (args.size, args.boards, args.challenges, args.seed, args.title),
            (5, 2, 4, 42, "几何钉板"),
        )
        self.assertEqual(args.output, "几何钉板.html")

    def test_default_generation(self) -> None:
        code, out, err = self.run_cli(["-o", str(self.target)])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("已生成", out)
        self.assertIn("共 2 页", out)
        page = self.target.read_text(encoding="utf-8")
        self.assertIn("几何钉板", page)
        self.assertEqual(page.count("<section"), 2)
        self.assertEqual(page.count("<svg"), 2)
        self.assertEqual(page.count("<circle"), 50)
        self.assertEqual(page.count("<article"), 4)

    def test_custom_arguments(self) -> None:
        code, _, _ = self.run_cli(
            [
                "--size", "7",
                "--boards", "3",
                "--challenges", "8",
                "--seed", "7",
                "--title", "五年级几何",
                "-o", str(self.target),
            ]
        )
        self.assertEqual(code, 0)
        page = self.target.read_text(encoding="utf-8")
        self.assertIn("五年级几何", page)
        self.assertEqual(page.count("<svg"), 3)
        self.assertEqual(page.count("<circle"), 147)
        self.assertEqual(page.count("<article"), 8)
        self.assertEqual(page.count("<section"), 4)

    def test_size_lower_boundary(self) -> None:
        page = self.generate(["--size", "3", "--boards", "1", "--challenges", "0"])
        text = page.read_text(encoding="utf-8")
        self.assertEqual(text.count("<circle"), 9)
        self.assertIn("钉点数 3×3", text)

    def test_size_upper_boundary(self) -> None:
        page = self.generate(["--size", "10", "--boards", "1", "--challenges", "0"])
        text = page.read_text(encoding="utf-8")
        self.assertEqual(text.count("<circle"), 100)
        self.assertIn("钉点数 10×10", text)

    def test_size_too_small(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli(["--size", "2", "-o", str(self.target)])
        self.assertEqual(ctx.exception.code, 2)
        self.assertFalse(self.target.exists())

    def test_size_too_large(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli(["--size", "11", "-o", str(self.target)])
        self.assertEqual(ctx.exception.code, 2)

    def test_size_not_integer(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli(["--size", "abc", "-o", str(self.target)])
        self.assertEqual(ctx.exception.code, 2)

    def test_size_message_chinese(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit):
                main(["--size", "2", "-o", str(self.target)])
        message = err.getvalue()
        self.assertIn("错误", message)
        self.assertIn("--size", message)
        self.assertNotIn("argument", message)

    def test_boards_low(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli(["--boards", "0", "-o", str(self.target)])
        self.assertEqual(ctx.exception.code, 2)
        self.assertFalse(self.target.exists())

    def test_boards_high(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli(["--boards", "5", "-o", str(self.target)])
        self.assertEqual(ctx.exception.code, 2)

    def test_challenges_low(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli(["--challenges", "-1", "-o", str(self.target)])
        self.assertEqual(ctx.exception.code, 2)

    def test_challenges_high(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli(["--challenges", "9", "-o", str(self.target)])
        self.assertEqual(ctx.exception.code, 2)

    def test_seed_not_integer(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli(["--seed", "1.5", "-o", str(self.target)])
        self.assertEqual(ctx.exception.code, 2)

    def test_seed_reproducible(self) -> None:
        first = self.root / "first.html"
        second = self.root / "second.html"
        self.run_cli(["--challenges", "8", "--seed", "42", "-o", str(first)])
        self.run_cli(["--challenges", "8", "--seed", "42", "-o", str(second)])
        self.assertEqual(
            first.read_text(encoding="utf-8"), second.read_text(encoding="utf-8")
        )

    def test_seed_changes_output(self) -> None:
        first = self.root / "first.html"
        second = self.root / "second.html"
        self.run_cli(["--challenges", "8", "--seed", "1", "-o", str(first)])
        self.run_cli(["--challenges", "8", "--seed", "2", "-o", str(second)])
        self.assertNotEqual(
            first.read_text(encoding="utf-8"), second.read_text(encoding="utf-8")
        )

    def test_zero_challenges(self) -> None:
        page = self.generate(["--challenges", "0"])
        text = page.read_text(encoding="utf-8")
        self.assertNotIn("<article", text)
        self.assertNotIn("面积与周长挑战", text)
        self.assertEqual(text.count("<section"), 1)

    def test_title_escaped(self) -> None:
        page = self.generate(["--title", "<钉板&>"])
        text = page.read_text(encoding="utf-8")
        self.assertIn("&lt;钉板&amp;&gt;", text)
        self.assertNotIn("<钉板&>", text)

    def test_empty_title(self) -> None:
        code, _, err = self.run_cli(["--title", "   ", "-o", str(self.target)])
        self.assertEqual(code, 2)
        self.assertIn("标题", err)
        self.assertFalse(self.target.exists())

    def test_write_failure(self) -> None:
        blocker = self.root / "blocker"
        blocker.write_text("x", encoding="utf-8")
        code, _, err = self.run_cli(["-o", str(blocker / "out.html")])
        self.assertEqual(code, 1)
        self.assertIn("写入文件失败", err)
        self.assertIn("错误", err)

    def test_nested_existing_directory(self) -> None:
        nested = self.root / "输出"
        nested.mkdir()
        code, _, _ = self.run_cli(["-o", str(nested / "钉板.html")])
        self.assertEqual(code, 0)
        self.assertTrue((nested / "钉板.html").exists())

    def test_help(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(io.StringIO()):
                main(["--help"])
        self.assertEqual(ctx.exception.code, 0)

    def test_version(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            with contextlib.redirect_stdout(io.StringIO()):
                main(["--version"])
        self.assertEqual(ctx.exception.code, 0)

    def test_unknown_argument(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli(["--bogus", "-o", str(self.target)])
        self.assertEqual(ctx.exception.code, 2)

    def test_missing_output_value(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            self.run_cli(["-o"])
        self.assertEqual(ctx.exception.code, 2)

    def test_missing_output_message_chinese(self) -> None:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit):
                main(["-o"])
        self.assertIn("缺少参数值", err.getvalue())
        self.assertNotIn("expected", err.getvalue())

    def test_maximum_output(self) -> None:
        page = self.generate(
            [
                "--size", "10",
                "--boards", "4",
                "--challenges", "8",
                "--seed", "123",
            ]
        )
        text = page.read_text(encoding="utf-8")
        self.assertEqual(text.count("<section"), 4)
        self.assertEqual(text.count("<svg"), 4)
        self.assertEqual(text.count("<circle"), 400)
        self.assertEqual(text.count("<article"), 8)

    def test_single_board(self) -> None:
        page = self.generate(["--boards", "1", "--challenges", "0"])
        text = page.read_text(encoding="utf-8")
        self.assertEqual(text.count("<section"), 1)
        self.assertEqual(text.count("<svg"), 1)

    def test_three_boards(self) -> None:
        page = self.generate(["--boards", "3", "--challenges", "0"])
        text = page.read_text(encoding="utf-8")
        self.assertEqual(text.count("<section"), 2)
        self.assertEqual(text.count("<svg"), 3)
        self.assertIn("钉板 3 · 共 3 块", text)

    def test_output_is_utf8(self) -> None:
        page = self.generate(["--challenges", "0"])
        text = page.read_text(encoding="utf-8")
        self.assertIn("几何钉板", text)
        self.assertIn("钉点数", text)

    def test_output_summary(self) -> None:
        code, out, _ = self.run_cli(
            ["--size", "6", "--boards", "3", "--challenges", "5",
             "-o", str(self.target)]
        )
        self.assertEqual(code, 0)
        self.assertIn("3 块 6×6 钉板", out)
        self.assertIn("5 张挑战卡", out)
        self.assertIn("共 4 页", out)


if __name__ == "__main__":
    unittest.main()
