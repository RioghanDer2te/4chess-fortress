from src.chess4_fortress.chess4 import Board, Square, Move, Piece

def get_move(board: Board, from_square: str, to_square: str, promotion: Piece | None = None):
    return Move(board.get_square(from_square), board.get_square(to_square), promotion)

class TestCollision:
    def test_fortress(self):
        board = Board()
        move = get_move(board, "C14", "D12")
        assert board.is_valid(move)[0] is False

    def test_normal(self):
        board = Board()
        move = get_move(board, "F14", "E12")
        assert board.is_valid(move)[0] is True

    def test_corner(self):
        board = Board()
        move = get_move(board, "E13", "D12")
        assert board.is_valid(move)[0] is False

    def test_oob(self):
        board = Board()
        move = get_move(board, "H14", "H15")
        assert board.is_valid(move)[0] is False

    def test_oob2(self):
        board = Board()
        move = get_move(board, "A13", "A4")
        assert board.is_valid(move)[0] is False


def test_long_bishop_capture():
    board = Board()
    assert board.turn.lower() == "white"  # this test only applies for white
    board.get_square("E13").piece_at = None
    move = get_move(board, "B16", "M5")
    assert board.is_valid(move)[0] is True
    board.move(move)
    assert board.graveyard[-1] == Piece("pawn", "brown")

def test_promotion():
    board = Board()
    for _ in range(4):  # test for all 4 colors
        board.next_turn()
        from_sq = board.get_square(board.get_pawn_promotion_rank(board.turn)[5])  # grab a middle of the board promotion rank square, because the other pieces are still in their starting position
        from_sq.piece_at = Piece("pawn", board.turn)
        to_sq = board.get_neighbour(from_sq, 0, 1, True)
        move = Move(from_sq, to_sq, Piece("queen", board.turn))
        assert board.is_valid(move)[0] is True

def test_checkmate_and_frozen():
    for n in range(4):
        board = Board()
        board.next_turn(n)
        for pos in ("M9", "N10", "M7"):
            board.get_square(Square.pos_rot90(pos, 4-n)).piece_at = None
        board.get_square(Square.pos_rot90("L8", 4 - n)).piece_at = Piece("queen", board.turn)
        board.check_checks()
        assert board.checked[board.COLORS[(board.COLORS.index(board.turn) + 1) % 4]]

        board.update_frozen()
        current = board.turn
        board.next_turn()
        assert board.turn == board.COLORS[(board.COLORS.index(current) + 2) % 4]
