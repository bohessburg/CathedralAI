# Cathedral

A Python implementation of the board game **Cathedral**, built as the game engine
for a future AlphaZero-style model. The current focus is a correct, well-tested
rules engine plus a terminal viewer for manual play.

> Longer-term the plan is a C++ core for self-play speed, Python for the ML, and a
> FastAPI UI. Right now everything is a Python reference implementation: get the
> rules provably correct first, port hot paths later.

## Files

| File | Purpose |
|------|---------|
| `piece.py` | Piece shapes, orientations, and the piece registry (one player's 14 buildings + the neutral Cathedral). |
| `game.py` | `GameState`: board, legal moves, placement, and capture/territory resolution. The engine. |
| `view.py` | Terminal viewer + REPL for playing by hand (ANSI color board). |
| `test_capture.py` | Unit tests for capture/territory detection. |

Run anything from the project root so the imports resolve:

```bash
python3 piece.py          # print every piece and its shape
python3 game.py           # print a fresh board + piece counts
python3 view.py           # interactive play
python3 test_capture.py   # run the capture test suite
```

## Core concepts

### The board

A 10×10 grid, `state.board[row][col]`, row 0 at the top. Each cell is a small int:

| Value | Const | Meaning |
|-------|-------|---------|
| 0 | `EMPTY` | empty square |
| 1 | `WHITE` | white building |
| 2 | `BLACK` | black building |
| 3 | `CATHEDRAL` | the neutral Cathedral |
| 4 | `WHITE_TERRITORY` | square claimed by white |
| 5 | `BLACK_TERRITORY` | square claimed by black |

Players are referred to by their cell value: `WHITE` (1) and `BLACK` (2). Helper
maps `OWNED[player]` and `TERRITORY[player]` give the building / territory value
for a player.

Cells are stored as plain ints (not enums) so the representation ports cleanly to
a C++/bitboard core later.

### Pieces (`piece.py`)

A `Piece` has a name, a normalized set of `(row, col)` cells, a `count` (how many
the player owns), and precomputed `orientations` (the unique rotations — Cathedral
pieces may be **rotated but never flipped**, since they're solid buildings).

- `PIECES` is the registry: one player's 14 buildings plus the Cathedral.
- The **Abbey** and **Academy** are *chiral* — the two players get mirror-image
  versions. `game.py` builds Black's set with `piece.mirrored()` for those.
- `PIECE_SETS[player]` (in `game.py`) maps name → `Piece` for each player.

### Moves

A move is an immutable tuple:

```python
Move(player, name, orientation, anchor)
# player:      WHITE or BLACK (the placer; the Cathedral is placed by a player too)
# name:        piece name, e.g. "Tower" or "Cathedral"
# orientation: index into that piece's .orientations
# anchor:      (row, col) added to the piece's normalized cells
```

`state.absolute_cells(move)` returns the board cells a move would occupy.

## `GameState` API (`game.py`)

```python
s = GameState()                 # fresh game; White to move, must place the Cathedral first

s.is_legal(move) -> bool        # bounds, occupancy, own-territory rule, Cathedral-first rule
s.legal_moves(player=None)      # generator of every legal Move for the side to move
s.apply(move)                   # stamp the piece, decrement count, flip the turn
s.resolve_captures(player)      # apply enclosures the player just made (see below)
s.find_captures(player)         # pure detection; returns capture candidates, no mutation
s.render() -> str               # plain-text board (also see view.py for color)

s.piece(player, name) -> Piece  # the Piece object (orientations live here)
```

Important state fields: `board`, `to_move`, `remaining[player][name]` (live counts),
`cathedral_placed`, `cathedral_captured`, and `piece_at[r][c]` / `placements[id]`
which track **which placed building** occupies each cell (needed to count distinct
buildings and to return a captured one to its owner).

### Capture / territory rules

When you place a piece you may enclose territory. The rules implemented:

- Walls seal **orthogonally** ("wall to wall"); diagonal contact does not seal.
- A region you wall off (with your buildings and/or the board edges) becomes your
  territory if it contains **at most one opponent building** (or the Cathedral),
  which is removed and returned to its owner.
- The Cathedral can be captured **only if it is the only piece** in the region.
- The Cathedral can never be part of a wall.
- Opponent territory inside a region you capture is **reclaimed** (it doesn't count
  as a building and doesn't block the capture).

Detection (`find_captures`) is pure and returns
`[(region_cells, captured_piece_id_or_None), ...]`. Mutation (`resolve_captures`)
applies them: empty + reclaimed cells → your territory, the captured building
removed and returned, and returns `[(region_cells, (owner, name)_or_None), ...]`
for display. Keeping detection and mutation separate makes the logic easy to test.

> Algorithm note: a "region" is a connected component of every cell that is **not
> your wall** (empties, enemy buildings, and the Cathedral flood together), so an
> enemy piece is "inside" whether or not empty squares buffer it. A region that
> touches all four board edges is the open board, never an enclosure.

## Playing in the viewer (`view.py`)

```
python3 view.py
```

The board draws as shaded color squares. Commands:

| Command | Action |
|---------|--------|
| `<Name> <orient> <row> <col>` | place a piece for the side to move, e.g. `Tower 0 3 4` |
| `show <Name>` | print a piece's orientations with their indices |
| `pieces` | list remaining pieces for the side to move |
| `moves [Name]` | count legal moves (optionally for one piece) |
| `undo` | revert the last move |
| `help` / `quit` | |

The viewer calls `resolve_captures` after each move and prints what was claimed or
captured, so you can watch territory and captures happen live.

## Writing unit tests

Tests live in `test_capture.py` and run as a plain script (no test framework) —
each test builds a board, calls an engine method, and prints `[OK ]` / `[XX ]`.

### Helpers

```python
fresh()                          # -> a new empty GameState
place(s, owner, name, cells)     # stamp a building and register its identity
box_perimeter(r0, r1, c0, c1)    # cells forming the perimeter of a rectangle (handy for walls)
report(name, caps, expect_n)     # print PASS/FAIL comparing len(caps) to expect_n
```

`place(s, owner, name, cells)` is the key one. It stamps a piece directly onto the
board and gives it a **single piece id** covering all `cells`:

- `owner` is `WHITE`, `BLACK`, or `None` (for the Cathedral).
- `cells` is a list of `(row, col)`.
- **One call = one building.** To make a 3-cell Inn, pass all three cells in one
  call: `place(s, BLACK, 'Inn', [(0,1),(1,1),(1,0)])`. Looping and calling `place`
  per cell would create *separate* one-cell pieces (separate ids), which the
  capture logic counts as multiple buildings — almost never what you want.

`place` builds a board state directly, which is more convenient for capture tests
than playing out legal moves. (It does not touch `remaining` counts; that only
matters if your test also checks counts — in that case adjust them yourself.)

> Quirk: `report` reads the module-level `s` to look up captured-piece names, so by
> convention each test assigns its board to `s` before calling `report`.

### Pattern

```python
# Tnn: one-line description of what should happen
s = fresh()
# ... build the board with place() / box_perimeter() / direct s.board[r][c] = ...
caps = s.find_captures(WHITE)          # or BLACK
report("Tnn description", caps, <expected number of captures>)
# optional extra assertions on the specifics:
print("         <what>:", <bool condition>)
```

### Worked example

"White walls off a 3×3 area containing a single Black tavern — it should capture
the tavern and claim the area."

```python
# T12: white captures a lone black tavern inside a walled box
s = fresh()
for c in box_perimeter(3, 7, 3, 7):    # a 5x5 ring of white wall
    place(s, WHITE, 'w', [c])
place(s, BLACK, 'Tavern', [(5, 5)])    # one black piece inside
caps = s.find_captures(WHITE)
report("T12 capture lone tavern", caps, 1)               # exactly one capture
captured = [s.placements[pid][1] for _, pid in caps if pid is not None]
print("         captured a Tavern:", captured == ['Tavern'])
```

### Testing mutation (not just detection)

`find_captures` is pure. To check that a capture actually *applies* correctly
(territory flips, piece returned), call `resolve_captures` and inspect the board:

```python
s = fresh()
# ... set up an enclosed black piece ...
before = s.remaining[BLACK]['Tavern']
s.resolve_captures(WHITE)
assert s.board[5][5] == WHITE_TERRITORY          # square became white territory
assert s.remaining[BLACK]['Tavern'] == before + 1 # piece returned to its owner
```

### What to cover when adding capture cases

The existing suite (T1–T11) covers: interior captures, pure-territory claims,
two-foreign rejection, wall gaps leaking, the Cathedral, "island"/open-board
safety, diagonal non-sealing, tight (no-buffer) captures, wall-touching pieces,
first-move corner captures, and recapturing a lone piece over reclaimed territory.
When you add a rule or hit a bug, add a case that pins down both the **positive**
(it captures when it should) and the **negative** (it does *not* over-capture).
