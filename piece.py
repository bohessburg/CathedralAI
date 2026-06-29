from __future__ import annotations


Cells = frozenset  # frozenset[tuple[int, int]] of (row, col) offsets


def _normalize(cells) -> Cells:
    min_r = min(r for r, _ in cells)
    min_c = min(c for _, c in cells)
    return frozenset((r - min_r, c - min_c) for r, c in cells)


def _rotate_cw(cells) -> Cells:
    return _normalize(frozenset((c, -r) for r, c in cells))


def _reflect(cells) -> Cells:
    return _normalize(frozenset((r, -c) for r, c in cells))


class Piece:
    def __init__(self, name: str, cells, count: int = 1, chiral: bool = False,
                 neutral: bool = False):
        self.name = name
        self.count = count
        self.chiral = chiral
        self.neutral = neutral  # True for the Cathedral: owned by neither player
        self.cells: Cells = _normalize(frozenset(cells))
        self.orientations: list[Cells] = self._unique_orientations()

    def mirrored(self, name: str | None = None) -> "Piece":
        return Piece(name or self.name, _reflect(self.cells),
                     count=self.count, chiral=self.chiral, neutral=self.neutral)

    @classmethod
    def from_grid(cls, name: str, grid, count: int = 1, chiral: bool = False,
                  neutral: bool = False, fill="1#xX*") -> "Piece":
        cells = []
        for r, row in enumerate(grid):
            for c, val in enumerate(row):
                filled = (val in fill) if isinstance(val, str) else bool(val)
                if filled:
                    cells.append((r, c))
        if not cells:
            raise ValueError(f"Piece {name!r} has no filled cells")
        return cls(name, cells, count=count, chiral=chiral, neutral=neutral)

    def _unique_orientations(self) -> list[Cells]:
        seen: list[Cells] = []
        cur = self.cells
        for _ in range(4):
            if cur not in seen:
                seen.append(cur)
            cur = _rotate_cw(cur)
        return seen

    @property
    def size(self) -> int:
        return len(self.cells)

    def render(self, cells: Cells | None = None, filled="#", empty=".") -> str:
        cells = self.cells if cells is None else cells
        rows = max(r for r, _ in cells) + 1
        cols = max(c for _, c in cells) + 1
        lines = []
        for r in range(rows):
            lines.append("".join(
                filled if (r, c) in cells else empty for c in range(cols)
            ))
        return "\n".join(lines)

    def __repr__(self) -> str:
        return (f"Piece(name={self.name!r}, size={self.size}, "
                f"count={self.count}, orientations={len(self.orientations)})")

# -- Piece Registry --

PIECES: list[Piece] = [
    Piece.from_grid("Tavern", ['1'], count=2),
    Piece.from_grid("Stable", ['11'], count=2),
    Piece.from_grid("Inn",    ['11','10'], count=2),
    Piece.from_grid("Bridge", ['111'], count=1),
    Piece.from_grid("Square", ['11','11'], count=1),
    Piece.from_grid("Manor",  ['111','010'], count=1),
    Piece.from_grid("Abbey",  ['011','110'], count=1, chiral=True),
    Piece.from_grid("Academy", ['110','011','010'], count=1, chiral=True),
    Piece.from_grid("Infirmary", ['010','111','010'], count=1),
    Piece.from_grid("Castle", ['111','101'], count=1),
    Piece.from_grid("Tower", ['011','110','100'], count=1),
    Piece.from_grid("Cathedral", ['010','111','010','010'], count=1, neutral=True)
]


if __name__ == "__main__":
    for p in PIECES:
        print(p)
        print(p.render())
        print()
