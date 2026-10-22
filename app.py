from __future__ import annotations

import html
import json
import random
from pathlib import Path

import streamlit as st

# -----------------------------------------------------------------------------
# TILE TEN — a small block puzzle built with Python + Streamlit
# -----------------------------------------------------------------------------
BOARD_SIZE = 10
DATA_FILE = Path(__file__).with_name(".tile_ten_data.json")

# A restrained, warm palette. Each piece in a newly dealt set gets a different
# color so the three choices are easy to distinguish.
PALETTE = [
    "#E57958",  # terracotta
    "#6F91D9",  # blue
    "#7DAB83",  # sage
    "#C6A253",  # ochre
    "#A18ACB",  # violet
    "#4FA6A0",  # teal
]

SHAPES = [
    {"name": "한 칸", "cells": [(0, 0)]},
    {"name": "가로 2칸", "cells": [(0, 0), (0, 1)]},
    {"name": "가로 3칸", "cells": [(0, 0), (0, 1), (0, 2)]},
    {"name": "가로 4칸", "cells": [(0, 0), (0, 1), (0, 2), (0, 3)]},
    {"name": "세로 2칸", "cells": [(0, 0), (1, 0)]},
    {"name": "세로 3칸", "cells": [(0, 0), (1, 0), (2, 0)]},
    {"name": "세로 4칸", "cells": [(0, 0), (1, 0), (2, 0), (3, 0)]},
    {"name": "정사각형", "cells": [(0, 0), (0, 1), (1, 0), (1, 1)]},
    {
        "name": "직사각형",
        "cells": [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)],
    },
    {"name": "L 블록", "cells": [(0, 0), (1, 0), (2, 0), (2, 1)]},
    {"name": "반대 L", "cells": [(0, 1), (1, 1), (2, 0), (2, 1)]},
    {"name": "T 블록", "cells": [(0, 0), (0, 1), (0, 2), (1, 1)]},
    {"name": "ㄱ 블록", "cells": [(0, 0), (1, 0), (1, 1)]},
    {"name": "반대 ㄱ", "cells": [(0, 1), (1, 0), (1, 1)]},
    {"name": "지그재그", "cells": [(0, 0), (0, 1), (1, 1), (1, 2)]},
    {"name": "반대 지그재그", "cells": [(0, 1), (0, 2), (1, 0), (1, 1)]},
]


def create_board() -> list[list[str | None]]:
    """Return an empty 10×10 board. Filled cells store their color."""
    return [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]


def generate_blocks() -> list[dict]:
    """Deal three pieces, each with a different color and a fixed orientation."""
    colors = random.sample(PALETTE, 3)
    dealt = []
    for color in colors:
        shape = random.choice(SHAPES)
        dealt.append(
            {
                "name": shape["name"],
                "cells": list(shape["cells"]),
                "color": color,
            }
        )
    return dealt


def block_dimensions(block: dict) -> tuple[int, int]:
    rows = max(r for r, _ in block["cells"]) + 1
    cols = max(c for _, c in block["cells"]) + 1
    return rows, cols


def block_positions(block: dict, top: int, left: int) -> set[tuple[int, int]]:
    """Translate block-local coordinates to board coordinates."""
    return {(top + r, left + c) for r, c in block["cells"]}


def can_place_block(
    board: list[list[str | None]], block: dict, top: int, left: int
) -> bool:
    """Check that every cell is inside the board and currently empty."""
    for r, c in block_positions(block, top, left):
        if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE):
            return False
        if board[r][c] is not None:
            return False
    return True


def place_block(
    board: list[list[str | None]], block: dict, top: int, left: int
) -> list[list[str | None]]:
    """Return a copied board with the piece placed on it."""
    updated = [row[:] for row in board]
    for r, c in block_positions(block, top, left):
        updated[r][c] = block["color"]
    return updated


def clear_completed_lines(
    board: list[list[str | None]],
) -> tuple[list[list[str | None]], int, int, int]:
    """Clear all full rows and columns simultaneously, without gravity.

    Returns (updated_board, total_lines, completed_rows, completed_columns).
    Intersections of a full row and column are cleared only once on the board,
    while both lines count toward the score.
    """
    full_rows = [r for r in range(BOARD_SIZE) if all(board[r][c] is not None for c in range(BOARD_SIZE))]
    full_cols = [
        c
        for c in range(BOARD_SIZE)
        if all(board[r][c] is not None for r in range(BOARD_SIZE))
    ]

    updated = [row[:] for row in board]
    cells_to_clear = {(r, c) for r in full_rows for c in range(BOARD_SIZE)}
    cells_to_clear.update((r, c) for c in full_cols for r in range(BOARD_SIZE))
    for r, c in cells_to_clear:
        updated[r][c] = None

    total_lines = len(full_rows) + len(full_cols)
    return updated, total_lines, len(full_rows), len(full_cols)


def calculate_score(block_cell_count: int, cleared_lines: int, combo: int) -> int:
    """Score a move: one point per placed cell, plus line and streak bonuses."""
    points = block_cell_count
    if cleared_lines:
        points += cleared_lines * 10
        points += max(0, cleared_lines - 1) * 5  # multi-line bonus
        points += max(0, combo - 1) * 5  # consecutive clear bonus
    return points


def check_game_over(board: list[list[str | None]], blocks: list[dict | None]) -> bool:
    """Game over when none of the remaining pieces fits anywhere."""
    available = [block for block in blocks if block is not None]
    if not available:
        return True
    for block in available:
        for r in range(BOARD_SIZE):
            for c in range(BOARD_SIZE):
                if can_place_block(board, block, r, c):
                    return False
    return True


def load_high_score() -> int:
    """Load the local best score; a missing or malformed file starts at zero."""
    try:
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return max(0, int(payload.get("high_score", 0)))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return 0


def save_high_score(value: int) -> None:
    """Persist the best score locally. The game still works if writes are blocked."""
    try:
        DATA_FILE.write_text(
            json.dumps({"high_score": int(value)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        # Some hosted environments use read-only/temporary filesystems.
        pass


def reset_game() -> None:
    """Start a fresh round while preserving the best score."""
    st.session_state.board = create_board()
    st.session_state.current_blocks = generate_blocks()
    st.session_state.selected_block = None
    st.session_state.score = 0
    st.session_state.combo = 0
    st.session_state.game_over = False
    st.session_state.last_message = ""


def render_piece(block: dict | None) -> str:
    """Build a small HTML preview of a piece for the selection cards."""
    if block is None:
        return '<div class="piece-empty">사용 완료</div>'

    rows, cols = block_dimensions(block)
    occupied = set(block["cells"])
    cells_html = []
    for r in range(rows):
        for c in range(cols):
            if (r, c) in occupied:
                cells_html.append(
                    f'<span class="mini-cell" style="background:{block["color"]}"></span>'
                )
            else:
                cells_html.append('<span class="mini-cell mini-cell-blank"></span>')
    return (
        f'<div class="piece-preview" style="grid-template-columns:repeat({cols}, 15px);">'
        + "".join(cells_html)
        + "</div>"
    )


def render_board(
    board: list[list[str | None]],
    preview: set[tuple[int, int]],
    preview_valid: bool,
    preview_color: str | None,
) -> str:
    """Render the 10×10 playfield with filled cells and an optional placement preview."""
    cells_html = []
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            coord = (r, c)
            if coord in preview and not preview_valid:
                css_class = "tile invalid"
                style = ""
            elif board[r][c] is not None:
                css_class = "tile filled"
                style = f' style="--tile-color:{board[r][c]}"'
            elif coord in preview and preview_valid:
                css_class = "tile preview"
                style = f' style="--tile-color:{preview_color}"'
            else:
                css_class = "tile empty"
                style = ""
            cells_html.append(f'<div class="{css_class}"{style}></div>')

    return (
        '<div class="board-frame"><div class="game-board">'
        + "".join(cells_html)
        + "</div></div>"
    )


# -----------------------------------------------------------------------------
# Streamlit page and styling
# -----------------------------------------------------------------------------
st.set_page_config(page_title="TILE TEN | 블록 퍼즐", page_icon=None, layout="centered")

st.markdown(
    """
    <style>
      :root {
        --paper: #F3F1EB;
        --card: #FFFEFA;
        --ink: #242A2E;
        --muted: #777C78;
        --line: #DDDCD3;
        --accent: #2F6857;
        --accent-soft: #E2EBE5;
      }
      html, body, [data-testid="stAppViewContainer"] {
        background: var(--paper);
        color: var(--ink);
      }
      [data-testid="stHeader"] { background: transparent; }
      [data-testid="stMainBlockContainer"] {
        max-width: 900px;
        padding-top: 2rem;
        padding-bottom: 3rem;
      }
      #MainMenu, footer { visibility: hidden; }
      .hero-kicker {
        color: var(--accent); font-size: 0.73rem; font-weight: 800;
        letter-spacing: 0.16em; text-transform: uppercase; margin-bottom: 0.45rem;
      }
      .hero-title {
        color: var(--ink); font-size: clamp(2.15rem, 5vw, 3.1rem);
        line-height: 1.02; font-weight: 850; letter-spacing: -0.065em;
        margin: 0; 
      }
      .hero-subtitle { color: #747873; font-size: 0.96rem; margin-top: 0.65rem; }
      .stats-row {
        display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px;
        margin: 1.35rem 0 1rem;
      }
      .stat-card {
        padding: 13px 16px 14px; border: 1px solid var(--line);
        background: rgba(255,254,250,0.86); border-radius: 15px;
      }
      .stat-label { font-size: 0.66rem; font-weight: 800; letter-spacing: 0.12em; color: #7C807A; }
      .stat-value { font-size: 1.55rem; line-height: 1.15; font-weight: 780; letter-spacing: -0.04em; margin-top: 5px; color: var(--ink); }
      .stat-value small { color: #81857F; font-size: 0.76rem; font-weight: 600; letter-spacing: 0; }
      .section-label {
        font-size: 0.72rem; letter-spacing: 0.12em; color: #737872;
        font-weight: 800; margin: 1.45rem 0 0.55rem;
      }
      .play-hint { color: #6F756F; font-size: 0.86rem; margin: 0.15rem 0 0.8rem; }
      .board-frame {
        width: min(100%, 540px); margin: 0.75rem auto 1rem;
        padding: 9px; background: #242B30; border-radius: 19px;
        box-shadow: 0 12px 28px rgba(28, 35, 36, 0.10);
      }
      .game-board {
        display: grid; grid-template-columns: repeat(10, minmax(0, 1fr));
        gap: clamp(3px, 0.75vw, 5px); width: 100%; aspect-ratio: 1 / 1;
      }
      .tile { min-width: 0; min-height: 0; aspect-ratio: 1 / 1; border-radius: 4px; box-sizing: border-box; }
      .tile.empty { background: #3B4449; border: 1px solid #465056; }
      .tile.filled {
        background: var(--tile-color); border: 1px solid rgba(255,255,255,0.18);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.18);
      }
      .tile.preview {
        background: var(--tile-color); opacity: 0.83;
        outline: 2px solid #FFFEFA; outline-offset: -3px;
      }
      .tile.invalid { background: #D65F51; border: 1px solid #F4D0CA; opacity: 0.93; }
      .piece-preview {
        display: grid; grid-auto-rows: 15px; gap: 4px; justify-content: center;
        align-content: center; min-height: 62px; margin: 0.15rem 0 0.5rem;
      }
      .mini-cell { display: block; width: 15px; height: 15px; border-radius: 3px; }
      .mini-cell-blank { background: transparent; }
      .piece-empty { display:flex; align-items:center; justify-content:center; min-height:62px; color:#92958F; font-size:.78rem; }
      .piece-name { text-align:center; color:var(--ink); font-weight:750; font-size:.84rem; margin-bottom:.55rem; }
      .piece-index { text-align:center; color:#8B8F88; font-size:.65rem; font-weight:800; letter-spacing:.13em; }
      .notice {
        background: #E7EDE7; border: 1px solid #D5E1D7; color: #315D4C;
        padding: 10px 13px; border-radius: 11px; font-size: 0.86rem; margin: 0.65rem 0;
      }
      .notice-warn { background:#F7E8E2; border-color:#EBD0C8; color:#9B493B; }
      .gameover-card {
        border:1px solid var(--line); background:var(--card); border-radius:20px;
        padding:2.1rem 1.4rem; text-align:center; margin:1.35rem 0;
      }
      .gameover-kicker { color:#B75D46; font-weight:850; font-size:.74rem; letter-spacing:.16em; }
      .gameover-title { color:var(--ink); font-size:2.2rem; font-weight:850; letter-spacing:-.05em; margin:.35rem 0 .4rem; }
      .gameover-score { color:#6F756F; font-size:.95rem; }
      .gameover-score strong { color:var(--ink); font-size:1.3rem; }
      .fine-print { color:#858982; font-size:.75rem; text-align:center; margin-top:.8rem; }
      .stButton > button {
        border-radius: 10px; min-height: 2.65rem; font-weight: 720;
        border: 1px solid #D5D8D0; background: #FFFEFA; color: #29302E;
        transition: transform .12s ease, border-color .12s ease;
      }
      .stButton > button:hover { border-color: #8AA99A; color: #285A49; transform: translateY(-1px); }
      .stButton > button[kind="primary"] { background: var(--accent); color: white; border-color: var(--accent); }
      .stButton > button[kind="primary"]:hover { background: #265846; border-color: #265846; color: white; }
      .stButton > button:disabled { opacity: .38; transform:none; }
      [data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #DDDCD3 !important; border-radius: 15px !important;
        background: rgba(255,254,250,0.72);
      }
      div[data-baseweb="select"] > div { border-radius: 10px; background: #FFFEFA; border-color:#D5D8D0; }
      div[data-testid="stSelectbox"] label { color:#656B65; font-size:.8rem; font-weight:650; }
      @media (max-width: 600px) {
        [data-testid="stMainBlockContainer"] { padding: 1.1rem 0.85rem 2rem; }
        .stats-row { gap: 6px; }
        .stat-card { padding: 10px 9px 11px; border-radius: 12px; }
        .stat-label { font-size:.58rem; letter-spacing:.07em; }
        .stat-value { font-size:1.25rem; }
        .board-frame { padding:6px; border-radius:13px; }
        .tile { border-radius:3px; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# Load persisted best score once per Streamlit session.
if "high_score" not in st.session_state:
    st.session_state.high_score = load_high_score()
if "board" not in st.session_state:
    reset_game()
if "row_choice" not in st.session_state:
    st.session_state.row_choice = 1
if "col_choice" not in st.session_state:
    st.session_state.col_choice = 1

# Header
header_left, header_right = st.columns([4.4, 1.15], vertical_alignment="center")
with header_left:
    st.markdown(
        '<div class="hero-kicker">A SMALL PUZZLE, ONE MOVE AT A TIME</div>'
        '<div class="hero-title">TILE TEN</div>'
        '<div class="hero-subtitle">블록을 놓고, 빈틈없이 한 줄을 지우세요.</div>',
        unsafe_allow_html=True,
    )
with header_right:
    if st.button("새 게임", key="new_game_top", use_container_width=True):
        reset_game()
        st.rerun()

st.markdown(
    f"""
    <div class="stats-row">
      <div class="stat-card"><div class="stat-label">CURRENT SCORE</div><div class="stat-value">{st.session_state.score:,}</div></div>
      <div class="stat-card"><div class="stat-label">BEST SCORE</div><div class="stat-value">{st.session_state.high_score:,}</div></div>
      <div class="stat-card"><div class="stat-label">CLEAR STREAK</div><div class="stat-value">{st.session_state.combo}<small> 연속</small></div></div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.game_over:
    st.markdown(
        f"""
        <div class="gameover-card">
          <div class="gameover-kicker">ROUND COMPLETE</div>
          <div class="gameover-title">GAME OVER</div>
          <div class="gameover-score">이번 점수 &nbsp; <strong>{st.session_state.score:,}</strong></div>
          <div class="gameover-score" style="margin-top:.35rem">최고 점수 &nbsp; <strong>{st.session_state.high_score:,}</strong></div>
          <p style="color:#7D827B;font-size:.88rem;margin-top:1.1rem">놓을 수 있는 블록이 없습니다. 새 판에서 다시 도전해 보세요.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("다시 시작하기", type="primary", use_container_width=True, key="restart_game_over"):
        reset_game()
        st.rerun()
    st.stop()

st.markdown('<div class="section-label">01 / 배치 위치</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="play-hint">블록의 왼쪽 위 모서리가 놓일 칸을 선택하세요. 회전은 할 수 없습니다.</div>',
    unsafe_allow_html=True,
)
position_left, position_right = st.columns(2)
with position_left:
    st.selectbox(
        "시작 행",
        options=list(range(1, BOARD_SIZE + 1)),
        key="row_choice",
        format_func=lambda value: f"{value}행",
    )
with position_right:
    st.selectbox(
        "시작 열",
        options=list(range(1, BOARD_SIZE + 1)),
        key="col_choice",
        format_func=lambda value: f"{value}열",
    )

selected_index = st.session_state.selected_block
selected_piece = None
if selected_index is not None and 0 <= selected_index < len(st.session_state.current_blocks):
    selected_piece = st.session_state.current_blocks[selected_index]
    if selected_piece is None:
        st.session_state.selected_block = None
        selected_piece = None

board = st.session_state.board
anchor_row = st.session_state.row_choice - 1
anchor_col = st.session_state.col_choice - 1
preview_cells: set[tuple[int, int]] = set()
preview_valid = False
preview_color = None

if selected_piece is not None:
    preview_cells = block_positions(selected_piece, anchor_row, anchor_col)
    preview_valid = can_place_block(board, selected_piece, anchor_row, anchor_col)
    preview_color = selected_piece["color"]
    if preview_valid:
        st.markdown(
            f'<div class="notice">배치 미리보기 · {len(selected_piece["cells"])}칸 · {st.session_state.row_choice}행 {st.session_state.col_choice}열에서 시작</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="notice notice-warn">이 위치에는 놓을 수 없습니다. 보드 안의 빈 공간을 선택하세요.</div>',
            unsafe_allow_html=True,
        )
else:
    st.markdown(
        '<div class="notice">아래에서 블록 하나를 선택하면 보드에 배치 미리보기가 나타납니다.</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    render_board(board, preview_cells, preview_valid, preview_color),
    unsafe_allow_html=True,
)

st.markdown('<div class="section-label">02 / 사용할 블록</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="play-hint">블록을 선택한 뒤 위에서 위치를 정하고 배치하세요. 한 번 사용한 블록은 사라집니다.</div>',
    unsafe_allow_html=True,
)

piece_columns = st.columns(3)
for index, (column, block) in enumerate(zip(piece_columns, st.session_state.current_blocks)):
    with column:
        with st.container(border=True):
            st.markdown(f'<div class="piece-index">PIECE 0{index + 1}</div>', unsafe_allow_html=True)
            st.markdown(render_piece(block), unsafe_allow_html=True)
            block_name = block["name"] if block is not None else "사용 완료"
            st.markdown(f'<div class="piece-name">{html.escape(block_name)}</div>', unsafe_allow_html=True)
            is_selected = st.session_state.selected_block == index and block is not None
            if st.button(
                "선택됨" if is_selected else "블록 선택",
                key=f"select_piece_{index}",
                type="primary" if is_selected else "secondary",
                disabled=block is None,
                use_container_width=True,
            ):
                st.session_state.selected_block = index
                st.rerun()

place_left, place_center, place_right = st.columns([1, 1.5, 1])
with place_center:
    if st.button(
        "블록 배치",
        key="place_block",
        type="primary",
        use_container_width=True,
        disabled=(selected_piece is None or not preview_valid),
    ):
        # Re-check the move on the server before changing the board.
        if selected_piece is not None and can_place_block(
            st.session_state.board, selected_piece, anchor_row, anchor_col
        ):
            updated_board = place_block(
                st.session_state.board, selected_piece, anchor_row, anchor_col
            )
            updated_board, cleared_lines, cleared_rows, cleared_cols = clear_completed_lines(updated_board)

            next_combo = st.session_state.combo + 1 if cleared_lines else 0
            gained = calculate_score(len(selected_piece["cells"]), cleared_lines, next_combo)

            st.session_state.board = updated_board
            st.session_state.score += gained
            st.session_state.combo = next_combo

            if cleared_lines:
                detail_parts = []
                if cleared_rows:
                    detail_parts.append(f"가로 {cleared_rows}")
                if cleared_cols:
                    detail_parts.append(f"세로 {cleared_cols}")
                detail = " · ".join(detail_parts)
                extra = " 여러 줄 보너스가 적용됐습니다." if cleared_lines > 1 else ""
                streak = " 연속 제거 보너스가 적용됐습니다." if next_combo > 1 else ""
                st.session_state.last_message = (
                    f"{cleared_lines}줄 제거 ({detail}) · +{gained}점.{extra}{streak}"
                )
            else:
                st.session_state.last_message = f"블록을 배치했습니다. +{gained}점."

            st.session_state.current_blocks[st.session_state.selected_block] = None
            st.session_state.selected_block = None

            # Deal the next three pieces only after all current pieces are used.
            if all(piece is None for piece in st.session_state.current_blocks):
                st.session_state.current_blocks = generate_blocks()

            if st.session_state.score > st.session_state.high_score:
                st.session_state.high_score = st.session_state.score
                save_high_score(st.session_state.high_score)

            st.session_state.game_over = check_game_over(
                st.session_state.board, st.session_state.current_blocks
            )
        st.rerun()

if st.session_state.last_message:
    st.markdown(
        f'<div class="notice">{html.escape(st.session_state.last_message)}</div>',
        unsafe_allow_html=True,
    )

st.markdown(
    '<div class="fine-print">블록 칸마다 1점 · 한 줄 제거 10점 · 여러 줄과 연속 제거는 추가 점수</div>',
    unsafe_allow_html=True,
)
