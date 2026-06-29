from __future__ import annotations

from typing import NamedTuple

from piece import PIECES, Piece

# -- Cell values (kept as small ints so this ports cleanly to a C++/bitboard core) --
EMPTY = 0
WHITE = 1
BLACK = 2
CATHEDRAL = 3
WHITE_TERRITORY = 4
BLACK_TERRITORY = 5

BOARD_SIZE = 10

PLAYERS = (WHITE, BLACK)

# Cell value marking a player's own building / their claimed territory.
OWNED = {WHITE: WHITE, BLACK: BLACK}
TERRITORY = {WHITE: WHITE_TERRITORY, BLACK: BLACK_TERRITORY}


def _build_piece_set(player: int) -> list[Piece]:
    """One player's 14 buildings. Black gets mirror images of the chiral
    pieces (Abbey, Academy), since the two players' sets are reflections."""
    pieces = []
    for p in PIECES:
        if p.neutral:
            continue  # the Cathedral belongs to neither player
        pieces.append(p.mirrored() if (player == BLACK and p.chiral) else p)
    return pieces


CATHEDRAL_PIECE = next(p for p in PIECES if p.neutral)
CATHEDRAL_NAME = CATHEDRAL_PIECE.name


class Move(NamedTuple):
    player: int          # WHITE or BLACK (the placer; cathedral is placed by a player too)
    name: str            # piece name, e.g. "Tower" or "Cathedral"
    orientation: int     # index into that piece's .orientations
    anchor: tuple[int, int]   # (row, col) added to the normalized piece offsets

# Static per-player registry: name -> Piece (shapes/orientations never change).
PIECE_SETS = {p: {pc.name: pc for pc in _build_piece_set(p)} for p in PLAYERS}

# Every placeable piece name (player buildings + the neutral Cathedral).
VALID_NAMES = set(PIECE_SETS[WHITE]) | {CATHEDRAL_NAME}


class GameState:
    def __init__(self):
        self.board = [[EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.to_move = WHITE
        # Live count of unplaced buildings per player, by piece name.
        self.remaining = {
            player: {name: pc.count for name, pc in PIECE_SETS[player].items()}
            for player in PLAYERS
        }
        self.cathedral_placed = False

    def piece(self, player: int, name: str) -> Piece:
        if name == CATHEDRAL_NAME:
            return CATHEDRAL_PIECE
        return PIECE_SETS[player][name]

    def absolute_cells(self, move: Move) -> list[tuple[int, int]]:
        """The board cells a move would occupy, before any legality check."""
        ar, ac = move.anchor
        shape = self.piece(move.player, move.name).orientations[move.orientation]
        return [(r + ar, c + ac) for r, c in shape]

    def is_legal(self, move: Move) -> bool:
        if move.name not in VALID_NAMES:
            return False
        if not (0 <= move.orientation < len(self.piece(move.player, move.name).orientations)):
            return False
        if move.name == CATHEDRAL_NAME:
            if self.cathedral_placed:
                return False
        else:
            # The game's opening move must be the Cathedral (White places it).
            if not self.cathedral_placed:
                return False
            if self.remaining[move.player].get(move.name, 0) <= 0:
                return False

        own_territory = TERRITORY[move.player]
        for r, c in self.absolute_cells(move):
            if not (0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE):
                return False
            cell = self.board[r][c]
            # A square is buildable only if empty or already the placer's territory.
            if cell != EMPTY and cell != own_territory:
                return False
        return True

    def legal_moves(self, player: int | None = None):
        """Yield every board-legal placement for `player` (default: side to move).

        Naive enumeration: each available piece, each unique orientation, every
        anchor; `is_legal` filters. Fine for the prototype (~thousands of checks);
        a bitboard core will make this far cheaper later. The mandatory Cathedral
        opening is enforced by is_legal; broader turn-order is the loop's job."""
        player = self.to_move if player is None else player

        names = [n for n, k in self.remaining[player].items() if k > 0]
        if not self.cathedral_placed:
            names.append(CATHEDRAL_NAME)

        for name in names:
            n_orient = len(self.piece(player, name).orientations)
            for o in range(n_orient):
                for r in range(BOARD_SIZE):
                    for c in range(BOARD_SIZE):
                        move = Move(player, name, o, (r, c))
                        if self.is_legal(move):
                            yield move

    def apply(self, move: Move) -> None:
        """Stamp the piece onto the board. (Capture/territory handled later.)"""
        if move.name == CATHEDRAL_NAME:
            value = CATHEDRAL
            self.cathedral_placed = True
        else:
            value = OWNED[move.player]
            self.remaining[move.player][move.name] -= 1
        for r, c in self.absolute_cells(move):
            self.board[r][c] = value
        self.to_move = BLACK if move.player == WHITE else WHITE

    def render(self) -> str:
        glyph = {EMPTY: ".", WHITE: "W", BLACK: "B", CATHEDRAL: "C",
                 WHITE_TERRITORY: "w", BLACK_TERRITORY: "b"}
        return "\n".join(
            "".join(glyph[c] for c in row) for row in self.board
        )


if __name__ == "__main__":
    s = GameState()
    print(s.render())
    for player, label in ((WHITE, "White"), (BLACK, "Black")):
        counts = s.remaining[player]
        print(f"{label}: {len(counts)} types, "
              f"{sum(counts.values())} buildings, "
              f"{sum(s.piece(player, n).size * c for n, c in counts.items())} squares")
