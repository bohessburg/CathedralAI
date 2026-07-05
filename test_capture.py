from game import *

def fresh():
    return GameState()

def place(s, owner, name, cells):
    """Stamp a building (owner WHITE/BLACK, or None for cathedral) with an id."""
    val = OWNED[owner] if owner is not None else CATHEDRAL
    pid = s._next_id; s._next_id += 1
    s.placements[pid] = (owner, name, frozenset(cells))
    for r, c in cells:
        s.board[r][c] = val
        s.piece_at[r][c] = pid
    return pid

def box_perimeter(r0, r1, c0, c1):
    cells = []
    for r in range(r0, r1+1):
        for c in range(c0, c1+1):
            if r in (r0, r1) or c in (c0, c1):
                cells.append((r, c))
    return cells

def report(name, caps, expect_n, expect_captured=...):
    ok = len(caps) == expect_n
    detail = []
    for region, cap in caps:
        capname = None if cap is None else s.placements[cap]
        detail.append(f"region={len(region)}cells captured={capname}")
    print(f"[{'OK ' if ok else 'XX '}] {name}: {len(caps)} capture(s) (expected {expect_n})")
    for d in detail: print("        ", d)

# T1: white encloses a single black tavern (ring of empties around it)
s = fresh()
for c in box_perimeter(3,7,3,7): place(s, WHITE, 'wall', [c])
place(s, BLACK, 'Tavern', [(5,5)])
report("T1 interior single-piece capture", s.find_captures(WHITE), 1)

# T2: white encloses empty 3x3 (no foreign) -> territory
s = fresh()
for c in box_perimeter(3,7,3,7): place(s, WHITE, 'wall', [c])
report("T2 territory capture (no foreign)", s.find_captures(WHITE), 1)

# T3: two black taverns inside -> no capture
s = fresh()
for c in box_perimeter(3,7,3,7): place(s, WHITE, 'wall', [c])
place(s, BLACK, 'Tavern', [(4,4)])
place(s, BLACK, 'Tavern', [(6,6)])
report("T3 two foreign inside", s.find_captures(WHITE), 0)

# T4: gap in wall (one orthogonal wall cell missing) -> region leaks, no capture
s = fresh()
wall = box_perimeter(3,7,3,7)
wall.remove((3,5))  # leave a gap on the top wall
for c in wall: place(s, WHITE, 'wall', [c])
place(s, BLACK, 'Tavern', [(5,5)])
report("T4 wall gap leaks", s.find_captures(WHITE), 0)

# T5: cathedral enclosed alone by white -> capture cathedral
s = fresh()
for c in box_perimeter(3,7,3,7): place(s, WHITE, 'wall', [c])
place(s, None, 'Cathedral', [(5,5)])
report("T5 cathedral captured alone", s.find_captures(WHITE), 1)

# T6: reachable island safety: cathedral + black piece both present, mostly empty board
s = fresh()
place(s, WHITE, 'Stable', [(0,0),(0,1)])   # white island on the edge
place(s, None, 'Cathedral', [(5,5)])
place(s, BLACK, 'Tavern', [(9,9)])
report("T6 island safety (2 foreign in big region)", s.find_captures(WHITE), 0)

# T7: diagonal-only contact does NOT seal (corner pocket with diagonal gap leaks)
s = fresh()
# try to wall off (0,0) using only a diagonal neighbor at (1,1) -> leaks
place(s, WHITE, 'Tavern', [(1,1)])
report("T7 diagonal contact does not seal", s.find_captures(WHITE), 0)

# T8: enemy piece surrounded tightly by walls, no empty buffer -> capture
s = fresh()
for c in [(4,5),(6,5),(5,4),(5,6)]: place(s, WHITE, 'w', [c])
place(s, BLACK, 'Tavern', [(5,5)])
report("T8 tight piece capture (no empty buffer)", s.find_captures(WHITE), 1)

# T9: enemy piece inside a box but touching the wall -> capture
s = fresh()
for c in box_perimeter(3,7,3,7): place(s, WHITE, 'w', [c])
place(s, BLACK, 'Tavern', [(4,4)])
report("T9 wall-touching piece capture", s.find_captures(WHITE), 1)

# T10: corner capture while the cathedral sits on the open board (move-2 case).
# Exactly the corner pocket is claimed; the board-spanning region (which holds
# the cathedral) must NOT be captured.
s = fresh()
for c in [(0,1),(1,1),(1,0)]: place(s, BLACK, 'Inn', [c])   # seals corner (0,0)
place(s, None, 'Cathedral', [(4,3),(5,3),(5,2),(5,4),(6,3)])
caps = s.find_captures(BLACK)
ok = len(caps) == 1 and caps[0][1] is None and caps[0][0] == frozenset({(0,0)})
report("T10 first-move corner capture, cathedral safe", caps, 1)
print("         corner-only & cathedral safe:", ok)

# T11: Piece surrounding territory on the corner can still be captured if its the only piece
s = fresh()
place(s, BLACK, 'Inn', [(0,1),(1,1),(1,0)])   # ONE Inn (single piece) sealing corner (0,0)
s.board[0][0] = BLACK_TERRITORY               # the square black claimed when sealing it
place(s, None, 'Cathedral', [(4,3),(5,3),(5,2),(5,4),(6,3)])
# white walls off the whole corner: its only foreign building is the lone Inn
for c in [(0,2),(1,2),(2,1),(2,0)]: place(s, WHITE, 'w', [c])
caps = s.find_captures(WHITE)
captured = [s.placements[pid][1] for _, pid in caps if pid is not None]
report("T11 lone corner piece can be recaptured", caps, 1)
print("         captured the Inn & reclaimed (0,0):",
      captured == ['Inn'] and any((0, 0) in region for region, _ in caps))