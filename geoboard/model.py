"""几何钉板数据模型：钉点坐标、页面布局与面积/周长挑战题库。"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

MIN_SIZE = 3
MAX_SIZE = 10
MIN_BOARDS = 1
MAX_BOARDS = 4
MIN_CHALLENGES = 0
MAX_CHALLENGES = 8
MAX_TITLE_LENGTH = 40
MAX_PROMPT_LENGTH = 60

BOARDS_PER_PAGE = 2
CHALLENGES_PER_PAGE = 4

PAGE_WIDTH_MM = 210.0
PAGE_HEIGHT_MM = 297.0
BOARD_SIDE_MM = 112.0
BOARD_MARGIN_MM = 13.0
BOARD_SINGLE_TOP_MM = 88.0
BOARD_FIRST_TOP_MM = 32.0
BOARD_SECOND_TOP_MM = 158.0

SKILLS: Tuple[str, ...] = ("面积", "周长", "图形")

GEOMETRY_EPSILON = 1e-9


class GeoboardError(ValueError):
    """钉板数据、页面布局或运行参数不合法。"""


def _require_int(
    value: object,
    label: str,
    minimum: Optional[int] = None,
    maximum: Optional[int] = None,
) -> int:
    """校验整数输入及可选范围，明确拒绝布尔值。"""
    if isinstance(value, bool) or not isinstance(value, int):
        raise GeoboardError("%s必须是整数" % label)
    if minimum is not None and value < minimum:
        raise GeoboardError("%s不能小于 %d，收到 %d" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise GeoboardError("%s不能大于 %d，收到 %d" % (label, maximum, value))
    return value


def _require_number(value: object, label: str) -> float:
    """校验有限数值输入，拒绝布尔值、字符串与 NaN/无穷大。"""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GeoboardError("%s必须是数字" % label)
    number = float(value)
    if not math.isfinite(number):
        raise GeoboardError("%s必须是有限数字" % label)
    return number


@dataclass(frozen=True)
class Peg:
    """一个钉点：列、行（均从 0 开始）与钉板内的毫米坐标。"""

    column: int
    row: int
    x_mm: float
    y_mm: float

    def __post_init__(self) -> None:
        column = _require_int(self.column, "钉点列号", 0)
        row = _require_int(self.row, "钉点行号", 0)
        x_mm = _require_number(self.x_mm, "钉点横坐标")
        y_mm = _require_number(self.y_mm, "钉点纵坐标")
        object.__setattr__(self, "column", column)
        object.__setattr__(self, "row", row)
        object.__setattr__(self, "x_mm", x_mm)
        object.__setattr__(self, "y_mm", y_mm)


@dataclass(frozen=True)
class Board:
    """一块 N×N 钉板，包含规格、序号、页码与页面中的毫米位置。

    钉点坐标以钉板外框左上角为原点；页面坐标由 ``origin_x_mm`` /
    ``origin_y_mm`` 与钉板内坐标相加得到。
    """

    size: int
    index: int
    page: int
    origin_x_mm: float
    origin_y_mm: float
    side_mm: float = BOARD_SIDE_MM
    margin_mm: float = BOARD_MARGIN_MM

    def __post_init__(self) -> None:
        size = _require_int(self.size, "钉板规格", MIN_SIZE, MAX_SIZE)
        index = _require_int(self.index, "钉板序号", 1)
        page = _require_int(self.page, "页码", 1)
        side = _require_number(self.side_mm, "钉板边长")
        margin = _require_number(self.margin_mm, "钉点边距")
        origin_x = _require_number(self.origin_x_mm, "钉板横坐标")
        origin_y = _require_number(self.origin_y_mm, "钉板纵坐标")
        if side <= 0:
            raise GeoboardError("钉板边长必须大于 0，收到 %g" % side)
        if margin <= 0:
            raise GeoboardError("钉点边距必须大于 0，收到 %g" % margin)
        if side - margin * 2 <= 0:
            raise GeoboardError("钉点边距过大，钉板内部没有可用空间")
        if (
            origin_x < -GEOMETRY_EPSILON
            or origin_x + side > PAGE_WIDTH_MM + GEOMETRY_EPSILON
        ):
            raise GeoboardError("钉板横向位置超出 A4 页面")
        if (
            origin_y < -GEOMETRY_EPSILON
            or origin_y + side > PAGE_HEIGHT_MM + GEOMETRY_EPSILON
        ):
            raise GeoboardError("钉板纵向位置超出 A4 页面")
        object.__setattr__(self, "size", size)
        object.__setattr__(self, "index", index)
        object.__setattr__(self, "page", page)
        object.__setattr__(self, "side_mm", side)
        object.__setattr__(self, "margin_mm", margin)
        object.__setattr__(self, "origin_x_mm", origin_x)
        object.__setattr__(self, "origin_y_mm", origin_y)

    @property
    def spacing_mm(self) -> float:
        """相邻两个钉点之间的毫米距离。"""
        return (self.side_mm - self.margin_mm * 2) / (self.size - 1)

    @property
    def label(self) -> str:
        """钉板下方显示的规格文字。"""
        return "钉点数 %d×%d" % (self.size, self.size)

    @property
    def pegs(self) -> Tuple[Peg, ...]:
        """按行优先顺序返回全部钉点，共 ``size × size`` 个。"""
        spacing = self.spacing_mm
        pegs: List[Peg] = []
        for row in range(self.size):
            y_mm = self.margin_mm + row * spacing
            for column in range(self.size):
                x_mm = self.margin_mm + column * spacing
                pegs.append(Peg(column, row, x_mm, y_mm))
        return tuple(pegs)

    def peg_at(self, column: int, row: int) -> Peg:
        """取第 column 列、第 row 行的钉点，越界时抛 GeoboardError。"""
        column = _require_int(column, "钉点列号", 0)
        row = _require_int(row, "钉点行号", 0)
        if column >= self.size:
            raise GeoboardError(
                "钉点列号超出范围：%d（有效范围 0~%d）" % (column, self.size - 1)
            )
        if row >= self.size:
            raise GeoboardError(
                "钉点行号超出范围：%d（有效范围 0~%d）" % (row, self.size - 1)
            )
        spacing = self.spacing_mm
        return Peg(
            column,
            row,
            self.margin_mm + column * spacing,
            self.margin_mm + row * spacing,
        )

    def peg_page_position(self, column: int, row: int) -> Tuple[float, float]:
        """返回钉点在整页中的毫米坐标（左上角为原点）。"""
        peg = self.peg_at(column, row)
        return (self.origin_x_mm + peg.x_mm, self.origin_y_mm + peg.y_mm)


def board_page_count(count: int) -> int:
    """钉板需要的页数：每页最多 2 块。"""
    total = _require_int(count, "钉板数量", MIN_BOARDS, MAX_BOARDS)
    return (total + BOARDS_PER_PAGE - 1) // BOARDS_PER_PAGE


def challenge_page_count(count: int) -> int:
    """挑战卡需要的页数：每页 4 张。"""
    total = _require_int(count, "挑战卡数量", MIN_CHALLENGES, MAX_CHALLENGES)
    if total == 0:
        return 0
    return (total + CHALLENGES_PER_PAGE - 1) // CHALLENGES_PER_PAGE


def page_count(boards: int, challenges: int) -> int:
    """整份文档的总页数：钉板页在前，挑战卡页在后。"""
    return board_page_count(boards) + challenge_page_count(challenges)


def build_boards(size: int = 5, count: int = 2) -> Tuple[Board, ...]:
    """按 A4 纵向排版生成钉板；每页最多两块，最后一块单独居中。"""
    board_size = _require_int(size, "钉板规格", MIN_SIZE, MAX_SIZE)
    total = _require_int(count, "钉板数量", MIN_BOARDS, MAX_BOARDS)
    origin_x = (PAGE_WIDTH_MM - BOARD_SIDE_MM) / 2.0
    boards: List[Board] = []
    for index in range(1, total + 1):
        page = (index - 1) // BOARDS_PER_PAGE + 1
        slot = (index - 1) % BOARDS_PER_PAGE
        first_on_page = (page - 1) * BOARDS_PER_PAGE + 1
        remaining = total - (first_on_page - 1)
        if remaining >= BOARDS_PER_PAGE:
            origin_y = BOARD_FIRST_TOP_MM if slot == 0 else BOARD_SECOND_TOP_MM
        else:
            origin_y = BOARD_SINGLE_TOP_MM
        boards.append(
            Board(
                size=board_size,
                index=index,
                page=page,
                origin_x_mm=origin_x,
                origin_y_mm=origin_y,
            )
        )
    return tuple(boards)


@dataclass(frozen=True)
class Challenge:
    """一张文字挑战卡：只给题目与难度，不含任何答案。"""

    code: str
    prompt: str
    skill: str
    difficulty: int

    def __post_init__(self) -> None:
        if not isinstance(self.code, str):
            raise GeoboardError("挑战编号必须是文本")
        code = self.code.strip()
        if not code:
            raise GeoboardError("挑战编号不能为空")
        if len(code) > 8:
            raise GeoboardError("挑战编号最多 8 个字符")
        if not isinstance(self.prompt, str):
            raise GeoboardError("挑战题目必须是文本")
        prompt = self.prompt.strip()
        if not prompt:
            raise GeoboardError("挑战题目不能为空")
        if len(prompt) > MAX_PROMPT_LENGTH:
            raise GeoboardError(
                "挑战题目最多 %d 个字符：%s" % (MAX_PROMPT_LENGTH, prompt)
            )
        if self.skill not in SKILLS:
            raise GeoboardError("挑战类别必须是：%s" % "、".join(SKILLS))
        difficulty = _require_int(self.difficulty, "难度", 1, 3)
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "prompt", prompt)
        object.__setattr__(self, "difficulty", difficulty)


CHALLENGES: Tuple[Challenge, ...] = (
    Challenge("C01", "画一个面积为 2 格的正方形。", "面积", 1),
    Challenge("C02", "画一个面积为 3 格的三角形。", "面积", 1),
    Challenge("C03", "画一个面积为 4 格的长方形，要求不是正方形。", "面积", 1),
    Challenge("C04", "画一个面积为 6 格的平行四边形。", "面积", 2),
    Challenge("C05", "画一个面积为 1 格且不是正方形的图形。", "面积", 2),
    Challenge("C06", "画一个面积为 4 格的三角形。", "面积", 2),
    Challenge("C07", "画一个面积为 8 格的梯形。", "面积", 3),
    Challenge("C08", "画一个面积为 5 格的四边形。", "面积", 3),
    Challenge("C09", "画一个周长是 8 格的四边形。", "周长", 1),
    Challenge("C10", "画一个周长是 12 格的正方形。", "周长", 1),
    Challenge("C11", "画一个周长是 10 格的长方形。", "周长", 2),
    Challenge("C12", "画一个周长是 12 格的长方形。", "周长", 2),
    Challenge("C13", "画一个周长是 14 格的四边形。", "周长", 3),
    Challenge("C14", "画一个有两个直角的四边形。", "图形", 1),
    Challenge("C15", "画一个四条边都相等的四边形。", "图形", 2),
    Challenge("C16", "画一个只有一组对边平行的四边形。", "图形", 2),
)


def select_challenges(count: int, seed: int = 42) -> Tuple[Challenge, ...]:
    """按种子打乱题库并取前 count 张，同一种子结果一致。"""
    amount = _require_int(count, "挑战卡数量", MIN_CHALLENGES, len(CHALLENGES))
    random_seed = _require_int(seed, "随机种子")
    shuffled = list(CHALLENGES)
    random.Random(random_seed).shuffle(shuffled)
    return tuple(shuffled[:amount])


@dataclass(frozen=True)
class Options:
    """一次生成任务的全部参数。"""

    size: int = 5
    boards: int = 2
    challenges: int = 4
    seed: int = 42
    title: str = "几何钉板"

    def __post_init__(self) -> None:
        size = _require_int(self.size, "钉板规格", MIN_SIZE, MAX_SIZE)
        boards = _require_int(self.boards, "钉板数量", MIN_BOARDS, MAX_BOARDS)
        cards = _require_int(
            self.challenges, "挑战卡数量", MIN_CHALLENGES, MAX_CHALLENGES
        )
        random_seed = _require_int(self.seed, "随机种子")
        if not isinstance(self.title, str):
            raise GeoboardError("标题必须是文本")
        title = self.title.strip()
        if not title:
            raise GeoboardError("标题不能为空")
        if len(title) > MAX_TITLE_LENGTH:
            raise GeoboardError("标题最多 %d 个字符" % MAX_TITLE_LENGTH)
        object.__setattr__(self, "size", size)
        object.__setattr__(self, "boards", boards)
        object.__setattr__(self, "challenges", cards)
        object.__setattr__(self, "seed", random_seed)
        object.__setattr__(self, "title", title)

    @property
    def page_count(self) -> int:
        """本任务的总页数。"""
        return page_count(self.boards, self.challenges)
