"""命令行入口：生成可打印的几何钉板与面积/周长挑战卡。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Callable, Optional, Sequence

from .model import (
    MAX_BOARDS,
    MAX_CHALLENGES,
    MAX_SIZE,
    MIN_BOARDS,
    MIN_CHALLENGES,
    MIN_SIZE,
    GeoboardError,
    Options,
)
from .render import render_html


class _ChineseParser(argparse.ArgumentParser):
    """把 argparse 的错误提示改为中文，并统一退出码 2。"""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        print("错误: %s" % _translate_error(message), file=sys.stderr)
        raise SystemExit(2)


def _translate_error(message: str) -> str:
    """去掉 argparse 的英文参数前缀，并翻译常见错误。"""
    text = re.sub(r"^argument [^:]+: ", "", message)
    text = text.replace("expected one argument", "缺少参数值")
    if text.startswith("unrecognized arguments: "):
        text = "无法识别的参数：" + text[len("unrecognized arguments: "):]
    if text.startswith("the following arguments are required: "):
        text = "缺少必填参数：" + text[len("the following arguments are required: "):]
    return text


def _integer_in_range(
    flag: str, minimum: int, maximum: int
) -> Callable[[str], int]:
    """构造带中文错误信息的整数参数解析器。"""

    def parse(text: str) -> int:
        try:
            value = int(text)
        except (TypeError, ValueError):
            raise argparse.ArgumentTypeError(
                "%s 必须是整数，收到 %r" % (flag, text)
            )
        if value < minimum or value > maximum:
            raise argparse.ArgumentTypeError(
                "%s 必须在 %d~%d 之间，收到 %d"
                % (flag, minimum, maximum, value)
            )
        return value

    return parse


def _integer(flag: str) -> Callable[[str], int]:
    """构造只要求整数的参数解析器。"""

    def parse(text: str) -> int:
        try:
            return int(text)
        except (TypeError, ValueError):
            raise argparse.ArgumentTypeError(
                "%s 必须是整数，收到 %r" % (flag, text)
            )

    return parse


def build_parser() -> argparse.ArgumentParser:
    """创建命令行解析器。"""
    parser = _ChineseParser(
        prog="geoboard",
        description="几何钉板：生成 A4 可打印点阵钉板与面积/周长挑战卡",
    )
    parser.add_argument("--version", action="version", version="geoboard 0.1.0")
    parser.add_argument(
        "--size",
        type=_integer_in_range("--size", MIN_SIZE, MAX_SIZE),
        default=5,
        help="每边钉点数 N，生成 N×N 点阵（%d~%d，默认 5）"
        % (MIN_SIZE, MAX_SIZE),
    )
    parser.add_argument(
        "--boards",
        type=_integer_in_range("--boards", MIN_BOARDS, MAX_BOARDS),
        default=2,
        help="生成几块钉板（%d~%d，默认 2；每页最多 2 块，自动分页）"
        % (MIN_BOARDS, MAX_BOARDS),
    )
    parser.add_argument(
        "--challenges",
        type=_integer_in_range(
            "--challenges", MIN_CHALLENGES, MAX_CHALLENGES
        ),
        default=4,
        help="生成几张挑战卡（%d~%d，默认 4；0 表示不生成）"
        % (MIN_CHALLENGES, MAX_CHALLENGES),
    )
    parser.add_argument(
        "--seed",
        type=_integer("--seed"),
        default=42,
        help="随机种子，控制挑战卡顺序（默认 42）",
    )
    parser.add_argument(
        "--title",
        default="几何钉板",
        help="页面标题（默认「几何钉板」）",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="几何钉板.html",
        help="输出 HTML 路径（默认「几何钉板.html」）",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    """执行命令行，返回退出码：0 成功、1 文件 IO、2 参数或数据错误。"""
    args = build_parser().parse_args(argv)
    try:
        options = Options(
            size=args.size,
            boards=args.boards,
            challenges=args.challenges,
            seed=args.seed,
            title=args.title,
        )
        page = render_html(options)
    except GeoboardError as exc:
        print("错误: %s" % exc, file=sys.stderr)
        return 2

    try:
        Path(args.output).write_text(page, encoding="utf-8")
    except OSError as exc:
        print("错误: 写入文件失败: %s" % exc, file=sys.stderr)
        return 1

    print(
        "已生成 %s：%d 块 %d×%d 钉板，%d 张挑战卡，共 %d 页"
        % (
            args.output,
            options.boards,
            options.size,
            options.size,
            options.challenges,
            options.page_count,
        )
    )
    print("打印设置：A4 纵向 · 边距无 · 缩放 100%")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
