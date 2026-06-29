from __future__ import annotations

import copy

from game import (GameState, Move, PIECE_SETS, CATHEDRAL_NAME,
                  EMPTY, WHITE, BLACK, CATHEDRAL, WHITE_TERRITORY, BLACK_TERRITORY)

# (r, g, b) background colors per cell value -> shaded squares.
COLORS = {
    EMPTY:           (40, 44, 52),
    WHITE:           (230, 222, 200),
    BLACK:           (60, 70, 95),
    CATHEDRAL:       (190, 150, 60),
    WHITE_TERRITORY: (120, 116, 104),
    BLACK_TERRITORY: (45, 52, 70),
}
GLYPH = {EMPTY: "  ", WHITE: "WW", BLACK: "BB", CATHEDRAL: "CC",
         WHITE_TERRITORY: "··", BLACK_TERRITORY: "··"}

RESET = "\x1b[0m"


def _cell(value: int) -> str:
    r, g, b = COLORS[value]
    fg = "38;2;20;20;20" if value in (WHITE, CATHEDRAL, WHITE_TERRITORY) else "38;2;220;220;220"
    return f"\x1b[48;2;{r};{g};{b};{fg}m{GLYPH[value]}{RESET}"


def draw(state: GameState) -> None:
    print("\n    " + "".join(f"{c:^2}" for c in range(10)))
    for r, row in enumerate(state.board):
        print(f" {r:>2} " + "".join(_cell(v) for v in row))
    side = "WHITE" if state.to_move == WHITE else "BLACK"
    avail = sum(k for k in state.remaining[state.to_move].values())
    print(f"\n  to move: {side}   ({avail} buildings left)")


# Case-insensitive name lookup, including the Cathedral.
_NAMES = {n.lower(): n for n in PIECE_SETS[WHITE]}
_NAMES[CATHEDRAL_NAME.lower()] = CATHEDRAL_NAME


def show_piece(state: GameState, name: str) -> None:
    piece = state.piece(state.to_move, name)
    print(f"\n{piece.name}: {len(piece.orientations)} orientation(s)")
    for i, cells in enumerate(piece.orientations):
        print(f"  [{i}]")
        for line in piece.render(cells).splitlines():
            print("    " + line)


HELP = """
commands:
  <Name> <orient> <row> <col>   place a piece for the side to move
  show <Name>                    print a piece's orientations + indices
  pieces                         list remaining pieces for the side to move
  moves [Name]                   count legal moves (optionally for one piece)
  undo                           revert the last move
  help                           this message
  quit
""".rstrip()


def repl() -> None:
    state = GameState()
    history: list[GameState] = []
    print(HELP)
    draw(state)

    while True:
        try:
            raw = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not raw:
            continue
        tok = raw.split()
        cmd = tok[0].lower()

        if cmd in ("quit", "q", "exit"):
            return
        if cmd == "help":
            print(HELP)
        elif cmd == "pieces":
            for n, k in state.remaining[state.to_move].items():
                if k > 0:
                    print(f"  {n:<10} x{k}")
        elif cmd == "moves":
            if len(tok) > 1 and tok[1].lower() in _NAMES:
                want = _NAMES[tok[1].lower()]
                n = sum(1 for m in state.legal_moves() if m.name == want)
                print(f"  {want}: {n} legal placements")
            else:
                print(f"  {sum(1 for _ in state.legal_moves())} legal moves")
        elif cmd == "show" and len(tok) > 1 and tok[1].lower() in _NAMES:
            show_piece(state, _NAMES[tok[1].lower()])
        elif cmd == "undo":
            if history:
                state = history.pop()
                draw(state)
            else:
                print("  nothing to undo")
        elif cmd in _NAMES:
            if len(tok) != 4:
                print("  usage: <Name> <orient> <row> <col>")
                continue
            try:
                orient, row, col = int(tok[1]), int(tok[2]), int(tok[3])
            except ValueError:
                print("  orient/row/col must be integers")
                continue
            move = Move(state.to_move, _NAMES[cmd], orient, (row, col))
            if not state.is_legal(move):
                print("  illegal move")
                continue
            history.append(copy.deepcopy(state))
            state.apply(move)
            draw(state)
        else:
            print("  unknown command (try 'help')")


if __name__ == "__main__":
    repl()
