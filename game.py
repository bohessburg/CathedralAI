class Cathedral:
    def __init__(self):
        #0: empty space
        #1: White piece
        #2: Black piece
        #3: Cathedral
        self.board = [[0 for _ in range(10)] for _ in range(10)]

        self.pieces = []

