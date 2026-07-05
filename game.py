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
        self.cathedral_captured = False
        self.placed_count = {WHITE: 0, BLACK: 0}  # placements made, for the first-move rule
        # Piece identity per cell: piece_at[r][c] is a placement id, or None.
        # Lets us count *distinct* buildings in a region (adjacent same-color
        # buildings are allowed) and return a captured one to its owner.
        self.piece_at = [[None] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.placements: dict[int, tuple] = {}   # id -> (owner|None, name, cells)
        self._next_id = 0

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

    def find_captures(self, player: int) -> list[tuple[frozenset, int | None]]:
        N = BOARD_SIZE
        B = self.board
        own = (OWNED[player], TERRITORY[player])
        opp_territory = TERRITORY[BLACK if player == WHITE else WHITE]
        seen = [[False] * N for _ in range(N)]
        captures = []

        def neighbors(r, c):
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < N and 0 <= nc < N:
                    yield nr, nc

        for sr in range(N):
            for sc in range(N):
                if seen[sr][sc] or B[sr][sc] in own:
                    continue
                # Flood the region C: everything that is not player's wall.
                comp, stack = [], [(sr, sc)]
                seen[sr][sc] = True
                while stack:
                    r, c = stack.pop()
                    comp.append((r, c))
                    for nr, nc in neighbors(r, c):
                        if not seen[nr][nc] and B[nr][nc] not in own:
                            seen[nr][nc] = True
                            stack.append((nr, nc))
                cset = set(comp)

                # Contents: count distinct foreign *buildings* (incl. cathedral).
                # Opponent territory does not count -- it is reclaimed on capture.
                foreign = set()
                for r, c in comp:
                    val = B[r][c]
                    if val != EMPTY and val != opp_territory:  # a piece cell
                        pid = self.piece_at[r][c]
                        if pid is not None and self.placements[pid][0] != player:
                            foreign.add(pid)
                if len(foreign) > 1:
                    continue

                # A region touching all four edges is the open board itself
                # (bounded by the frame on every side), never an enclosure.
                edges = set()
                for r, c in comp:
                    if r == 0: edges.add("T")
                    if r == N - 1: edges.add("B")
                    if c == 0: edges.add("L")
                    if c == N - 1: edges.add("R")
                if len(edges) == 4:
                    continue

                # Reachable from the board edge "around" C (through non-C cells).
                reach = [[False] * N for _ in range(N)]
                rstack = []
                for i in range(N):
                    for r, c in ((0, i), (N - 1, i), (i, 0), (i, N - 1)):
                        if (r, c) not in cset and not reach[r][c]:
                            reach[r][c] = True
                            rstack.append((r, c))
                while rstack:
                    r, c = rstack.pop()
                    for nr, nc in neighbors(r, c):
                        if not reach[nr][nc] and (nr, nc) not in cset:
                            reach[nr][nc] = True
                            rstack.append((nr, nc))

                walled = any(
                    B[nr][nc] in own and reach[nr][nc]
                    for r, c in comp for nr, nc in neighbors(r, c)
                    if (nr, nc) not in cset
                )
                if not walled:
                    continue

                region = frozenset((r, c) for r, c in comp
                                   if B[r][c] in (EMPTY, opp_territory))
                captured = next(iter(foreign)) if foreign else None
                captures.append((region, captured))
        return captures

    def apply(self, move: Move) -> None:
        """Stamp the piece onto the board. (Capture/territory handled later.)"""
        cells = self.absolute_cells(move)
        if move.name == CATHEDRAL_NAME:
            value, owner = CATHEDRAL, None
            self.cathedral_placed = True
        else:
            value, owner = OWNED[move.player], move.player
            self.remaining[move.player][move.name] -= 1
        pid = self._next_id
        self._next_id += 1
        self.placements[pid] = (owner, move.name, frozenset(cells))
        for r, c in cells:
            self.board[r][c] = value
            self.piece_at[r][c] = pid
        self.placed_count[move.player] += 1
        self.to_move = BLACK if move.player == WHITE else WHITE

    def resolve_captures(self, player: int) -> list[tuple[frozenset, tuple | None]]:
        terr = TERRITORY[player]
        results = []
        for region, pid in self.find_captures(player):
            for r, c in region:
                self.board[r][c] = terr
            captured = None
            if pid is not None:
                owner, name, cells = self.placements.pop(pid)
                for r, c in cells:
                    self.board[r][c] = terr
                    self.piece_at[r][c] = None
                if owner is None:
                    self.cathedral_captured = True
                else:
                    self.remaining[owner][name] += 1
                captured = (owner, name)
            results.append((region, captured))
        return results

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
