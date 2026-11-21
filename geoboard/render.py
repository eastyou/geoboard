"""把几何钉板渲染成自包含、可打印的 A4 纵向 HTML。"""

from __future__ import annotations

import html
from typing import List, Sequence, Tuple

from .model import (
    Challenge,
    GeoboardError,
    Options,
    Board,
    build_boards,
    select_challenges,
)

CARD_ACCENTS: Tuple[str, ...] = (
    "#3d8b8b",
    "#c48b3b",
    "#7a6fb0",
    "#4f86b8",
)


def _num(value: float) -> str:
    """把毫米数格式化为紧凑文本，最多保留两位小数。"""
    text = "%.2f" % value
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _escape(value: str) -> str:
    """转义用户可见文本，避免破坏 HTML 结构。"""
    return html.escape(value)


def render_board_svg(board: Board) -> str:
    """生成一块钉板的毫米级 SVG：实线外框 + 实心钉点。"""
    if not isinstance(board, Board):
        raise GeoboardError("board 必须是 Board 对象")
    side = board.side_mm
    radius = max(1.2, min(1.9, board.spacing_mm * 0.09))
    circles: List[str] = []
    for peg in board.pegs:
        circles.append(
            '<circle cx="%s" cy="%s" r="%s"/>'
            % (_num(peg.x_mm), _num(peg.y_mm), _num(radius))
        )
    label = board.label
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%smm" height="%smm" '
        'viewBox="0 0 %s %s" role="img" aria-label="%s，共 %d 个钉点">'
        "<title>%s</title>"
        '<rect x="0.35" y="0.35" width="%s" height="%s" fill="#ffffff" '
        'stroke="#1f2937" stroke-width="0.7"/>'
        '<g fill="#0f172a">%s</g>'
        "</svg>"
        % (
            _num(side),
            _num(side),
            _num(side),
            _num(side),
            _escape(label),
            board.size * board.size,
            _escape(label),
            _num(side - 0.7),
            _num(side - 0.7),
            "".join(circles),
        )
    )


def _stars(difficulty: int) -> str:
    """难度星标：实心星表示难度，空心星补齐三颗。"""
    return "★" * difficulty + "☆" * (3 - difficulty)


def _toolbar(options: Options) -> str:
    """仅屏幕显示的顶部信息条。"""
    return (
        '<div class="toolbar"><strong>%s</strong>'
        "<span>%d 块钉板 · %d 张挑战卡 · %d×%d 点阵 · 共 %d 页</span>"
        '<span class="tip">打印：A4 纵向 · 边距无 · 缩放 100%%</span></div>'
        % (
            _escape(options.title),
            options.boards,
            options.challenges,
            options.size,
            options.size,
            options.page_count,
        )
    )


def _page_head(left: str, right: str) -> str:
    return (
        '<header class="page-head"><span class="brand">%s</span>'
        '<span class="page-id">%s</span></header>' % (_escape(left), _escape(right))
    )


def _page_foot(page_number: int, total_pages: int, note: str) -> str:
    return (
        '<footer class="page-foot"><span>第 %d 页 / 共 %d 页</span>'
        "<span>%s</span></footer>"
        % (page_number, total_pages, _escape(note))
    )


def _board_figure(board: Board, total_boards: int) -> str:
    """一块钉板及其下方规格标注，位置来自 Board 的页面坐标。"""
    return (
        '<figure class="board" style="--bx:%smm;--by:%smm">'
        "%s"
        "<figcaption><b>%s</b><span>钉板 %d / %d</span></figcaption>"
        "</figure>"
        % (
            _num(board.origin_x_mm),
            _num(board.origin_y_mm),
            render_board_svg(board),
            _escape(board.label),
            board.index,
            total_boards,
        )
    )


def _board_page(
    options: Options,
    page_number: int,
    total_pages: int,
    boards: Sequence[Board],
    total_boards: int,
) -> str:
    if not boards:
        raise GeoboardError("钉板页必须至少包含一块钉板")
    first = boards[0].index
    last = boards[-1].index
    range_text = (
        "钉板 %d · 共 %d 块" % (first, total_boards)
        if first == last
        else "钉板 %d–%d · 共 %d 块" % (first, last, total_boards)
    )
    figures = "".join(_board_figure(board, total_boards) for board in boards)
    return (
        '<section class="sheet board-page">'
        "%s"
        '<h1 class="page-title">%s</h1>'
        '<p class="page-sub">用橡皮筋或铅笔在钉点之间连线，'
        "画完后数一数图形的面积和周长。</p>"
        '<div class="boards">%s</div>'
        "%s"
        "</section>"
        % (
            _page_head("geoboard", range_text),
            _escape(options.title),
            figures,
            _page_foot(
                page_number,
                total_pages,
                "钉点数 %d×%d · A4 纵向" % (options.size, options.size),
            ),
        )
    )


def _card(card: Challenge, number: int) -> str:
    accent = CARD_ACCENTS[(number - 1) % len(CARD_ACCENTS)]
    return (
        '<article class="card" style="--accent:%s">'
        '<div class="card-top"><span class="no">挑战 %02d</span>'
        '<span class="stars">%s</span></div>'
        '<div class="card-skill">%s</div>'
        '<p class="prompt">%s</p>'
        '<div class="card-foot"><span>在钉板上画出来</span>'
        "<span>%s</span></div>"
        "</article>"
        % (
            accent,
            number,
            _stars(card.difficulty),
            _escape(card.skill),
            _escape(card.prompt),
            _escape(card.code),
        )
    )


def _challenge_page(
    options: Options,
    page_number: int,
    total_pages: int,
    cards: Sequence[Challenge],
    first_number: int,
    total_cards: int,
) -> str:
    if not cards:
        raise GeoboardError("挑战卡页必须至少包含一张挑战卡")
    last_number = first_number + len(cards) - 1
    range_text = (
        "挑战卡 %d · 共 %d 张" % (first_number, total_cards)
        if first_number == last_number
        else "挑战卡 %d–%d · 共 %d 张" % (first_number, last_number, total_cards)
    )
    markup = "".join(
        _card(card, first_number + offset) for offset, card in enumerate(cards)
    )
    return (
        '<section class="sheet card-page">'
        "%s"
        '<h1 class="page-title">面积与周长挑战</h1>'
        '<p class="page-sub">先读题，再在钉板上画出来；'
        "沿虚线剪下卡片，和同伴交换挑战。</p>"
        '<div class="cards">%s</div>'
        "%s"
        "</section>"
        % (
            _page_head("geoboard", range_text),
            markup,
            _page_foot(page_number, total_pages, "虚线剪开 · 每页 4 张"),
        )
    )


def render_html(options: Options) -> str:
    """生成完整、自包含、可打印的 HTML 文档。"""
    if not isinstance(options, Options):
        raise GeoboardError("options 必须是 Options 对象")
    boards = build_boards(options.size, options.boards)
    cards = select_challenges(options.challenges, options.seed)
    total_pages = options.page_count
    sheets: List[str] = []
    page_number = 1
    for start in range(0, len(boards), 2):
        sheets.append(
            _board_page(
                options,
                page_number,
                total_pages,
                boards[start:start + 2],
                len(boards),
            )
        )
        page_number += 1
    for start in range(0, len(cards), 4):
        sheets.append(
            _challenge_page(
                options,
                page_number,
                total_pages,
                cards[start:start + 4],
                start + 1,
                len(cards),
            )
        )
        page_number += 1
    return (
        "<!doctype html>\n"
        '<html lang="zh-CN">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>%s</title>\n<style>%s</style>\n</head>\n<body>\n"
        "%s\n<main>\n%s\n</main>\n</body>\n</html>\n"
        % (_escape(options.title), _STYLE, _toolbar(options), "\n".join(sheets))
    )


_STYLE = """
  :root { color-scheme: light; }
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; }
  body {
    padding: 8mm 0 12mm;
    background: #e2e8f0;
    color: #0f172a;
    font-family: "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
    overflow-x: hidden;
  }
  .toolbar {
    width: 210mm;
    max-width: 100%;
    margin: 0 auto 6mm;
    padding: 0 4mm;
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 4px 14px;
    color: #334155;
    font-size: 13px;
  }
  .toolbar strong { font-size: 15px; letter-spacing: 1px; }
  .toolbar span { color: #64748b; font-size: 12px; }
  .toolbar .tip { margin-left: auto; color: #475569; }
  .sheet {
    position: relative;
    width: 210mm;
    height: 297mm;
    margin: 0 auto 8mm;
    background: #fff;
    box-shadow: 0 6px 22px rgba(15, 23, 42, 0.14);
    overflow: hidden;
    page-break-after: always;
    break-after: page;
  }
  .sheet:last-child { page-break-after: auto; break-after: auto; }
  .page-head {
    position: absolute;
    top: 9mm;
    left: 12mm;
    right: 12mm;
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    padding-bottom: 2mm;
    border-bottom: 0.25mm solid #cbd5e1;
    color: #64748b;
    font-size: 9pt;
    letter-spacing: 0.6pt;
  }
  .brand { font-weight: 600; color: #334155; letter-spacing: 1.5pt; }
  .page-title {
    position: absolute;
    top: 15mm;
    left: 12mm;
    right: 12mm;
    margin: 0;
    text-align: center;
    font-size: 19pt;
    font-weight: 600;
    letter-spacing: 4pt;
  }
  .page-sub {
    position: absolute;
    top: 26mm;
    left: 12mm;
    right: 12mm;
    margin: 0;
    text-align: center;
    color: #64748b;
    font-size: 9.5pt;
  }
  .boards {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    left: 0;
  }
  .board {
    position: absolute;
    left: var(--bx, 49mm);
    top: var(--by, 32mm);
    width: 112mm;
    margin: 0;
  }
  .board svg { display: block; width: 112mm; max-width: 100%; height: auto; }
  .board figcaption {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-top: 1.5mm;
    color: #334155;
    font-size: 9pt;
  }
  .board figcaption b { font-weight: 600; letter-spacing: 1pt; }
  .board figcaption span { color: #94a3b8; font-size: 8pt; }
  .cards {
    position: absolute;
    top: 36mm;
    left: 12mm;
    right: 12mm;
    bottom: 16mm;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-template-rows: repeat(2, minmax(0, 1fr));
    gap: 5mm;
  }
  .card {
    border: 0.45mm dashed #94a3b8;
    border-radius: 2.5mm;
    padding: 5.5mm 6mm;
    display: flex;
    flex-direction: column;
    min-height: 0;
    break-inside: avoid;
    page-break-inside: avoid;
  }
  .card-top {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    color: #64748b;
    font-size: 9pt;
    letter-spacing: 0.8pt;
  }
  .stars { color: #d97706; letter-spacing: 1.5pt; }
  .card-skill {
    align-self: flex-start;
    margin-top: 3mm;
    padding: 0.8mm 2.4mm;
    border-radius: 1.2mm;
    background: #f1f5f9;
    color: var(--accent, #475569);
    font-size: 9pt;
    font-weight: 600;
    letter-spacing: 1pt;
  }
  .card .prompt {
    margin: 4mm 0 0;
    font-size: 14pt;
    line-height: 1.75;
    letter-spacing: 0.4pt;
  }
  .card-foot {
    margin-top: auto;
    padding-top: 3mm;
    display: flex;
    justify-content: space-between;
    color: #94a3b8;
    font-size: 8pt;
    letter-spacing: 0.6pt;
  }
  .page-foot {
    position: absolute;
    left: 12mm;
    right: 12mm;
    bottom: 8mm;
    display: flex;
    justify-content: space-between;
    padding-top: 2mm;
    border-top: 0.2mm solid #e2e8f0;
    color: #64748b;
    font-size: 8pt;
  }
  @page { size: A4 portrait; margin: 0; }
  @media print {
    body { background: #fff; padding: 0; }
    .toolbar { display: none; }
    .sheet { margin: 0; box-shadow: none; }
    * { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
  @media screen and (max-width: 820px) {
    body { padding: 12px; }
    .toolbar { width: 100%; margin-bottom: 12px; padding: 0; }
    .sheet {
      width: 100%;
      height: auto;
      min-height: 0;
      margin: 0 0 16px;
      padding: 16px;
    }
    .page-head,
    .page-title,
    .page-sub,
    .boards,
    .cards,
    .page-foot { position: static; }
    .page-head { margin-bottom: 10px; }
    .page-title { margin: 8px 0 4px; font-size: 16pt; letter-spacing: 2pt; }
    .page-sub { margin: 0 0 14px; }
    .boards {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 18px;
    }
    .board { position: static; width: 100%; max-width: 112mm; }
    .board svg { width: 100%; }
    .cards {
      display: grid;
      grid-template-columns: 1fr;
      grid-template-rows: none;
      gap: 12px;
    }
    .card { min-height: 150px; }
    .page-foot { margin-top: 16px; }
  }
"""
