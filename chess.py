import itertools
from typing import Union, Optional, List, Iterable

from utils import list_in_list, str_range, make_iter, chunk_list


class CheckErrorMsg:
    SquareToOutOfBounds = "You can't remove this piece by moving it out of this board!"
    SquareFromNoPiece = "You can't move nothing!"
    SquareFromNotYourPiece = "It's not yet this pieces turn!"
    SquareFromAndToSame = "You can't pass a turn unless you literally can't move or are checkmated!"
    FriendlyFire = "Friendly Fire is disabled!"
    WallsInTheWay = "You can't move through walls!"
    PromotionFromNonPawn = "You can't promote a non-pawn!"
    PromotionOutOfBounds = "You can't promote without being being on the back rank of your teammate!"
    SquareToIllegal = "You can't move there."
    CheckmateYourself = "This move would checkmate you!"
    CheckmateTeammate = "This move would put your teammate at risk of checkmate!"
    TargetFrozen = "You can't remove pieces from frozen players!"


class Piece:
    pieces = ["king", "queen", "rook", "bishop", "knight", "pawn"]
    piece_initials = dict(zip(("k", "q", "r", "b", "n", "p"), pieces))

    def __init__(self, _type: str, _color: str):
        self.type = _type if not len(_type) == 1 else self.piece_initials[_type]
        self.color = _color

    def __str__(self):
        return f"{self.color} {self.type}"

    def __repr__(self):
        return f"<{self}>"

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.type == other.type and self.color == other.color

    @classmethod
    def from_initial(cls, initial) -> str:
        return cls.piece_initials.get(initial)

    @classmethod
    def to_initial(cls, name) -> str:
        return {v: k for k, v in cls.piece_initials.items()}.get(name)


class Square:
    def __init__(self, position: Union[int, str], piece_at: Optional[Piece] = None):
        self.position = position[0].upper() + position[1:].zfill(2) if isinstance(position, str) else self.pos_itos(position)
        self.piece_at = piece_at

    def __repr__(self):
        return f"<Square {self}>"

    def __str__(self):
        return f"{self.position}{f' with a {self.piece_at}' if self.piece_at else ''}"

    def __int__(self):
        return self.pos_stoi(self.position)

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.position == other.position and self.piece_at == other.piece_at

    @property
    def column(self) -> int:
        return ord(self.position[0]) - ord("A")

    @property
    def row(self) -> int:
        return int(self.position[1:])

    @property
    def x(self) -> str:
        return self.position[0]

    @property
    def y(self) -> str:
        return self.position[1:]

    @staticmethod
    def pos_stoi(pos: str) -> int:
        """Position String to Integer; Return a board.layout valid position for a string notation of a square"""
        return ord(pos[0].upper()) - ord("A") + (int(pos[1:])-1) * 16 + 1

    @staticmethod
    def pos_itos(pos: int) -> str:
        """Position Integer to String; Return a string notation of a square based on what would be the position in board.layout"""
        return chr(ord("A") + (pos-1) % 16) + str(pos // 16 + (1 if not pos % 16 == 0 else 0)).zfill(2)

    @classmethod
    def pos_rot90(cls, pos: str, times=1) -> str:
        """Return the position rotated clockwise around the center of the board, `times` times"""
        if times == 0:
            return pos[0]+pos[1:].zfill(2)
        return cls.pos_rot90(chr(ord("P") - int(pos[1:]) + 1) + str(ord(pos[0].upper()) - ord("A") + 1).zfill(2), times - 1)

    @classmethod
    def pos_rot90_list(cls, pos: Union[list, tuple], times=1) -> list:
        return [cls.pos_rot90(a, times) for a in pos]

    @staticmethod
    def get_ray(pos1: str, pos2: str) -> list:
        """
            Return a list of all squares between pos1 and pos2 inclusive.
            E.g. get_ray("a4", "d7") -> ['A04', 'B05', 'C06', 'D07']
            Raises ValueError when pos1 and pos2 don't build a diagonal
        """
        pos1, pos2 = pos1.upper(), pos2.upper()
        if not abs(ord(pos1[0])-ord(pos2[0])) == abs(int(pos1[1:])-int(pos2[1:])):
            raise ValueError(f"4Chess: {pos1} and {pos2} are not a diagonal ray!")

        ystep = 1 if pos1[1:] < pos2[1:] else -1
        path = zip(str_range(pos1[0], pos2[0], 1 if pos1[0] < pos2[0] else -1),  # count the files
                   range(int(pos1[1:]), int(pos2[1:])+ystep, ystep))  # count the ranks
        return [a + str(b).zfill(2) for a, b in path]  # string format

    @classmethod
    def square_in_ray(cls, squares: Iterable["Square"], pos1: str, pos2: str, require_all=False) -> bool:
        """Check if any (or all) squares are part of the diagonal ray between pos1 and pos2 inclusive"""
        return list_in_list([a.position for a in make_iter(squares)], cls.get_ray(pos1, pos2), require_all)

    @staticmethod  # square can be None, so this has to be a staticmethod
    def check_enemy(square: Optional["Square"], colors: Union[list, tuple]) -> bool:
        """Check if piece_at square is of given color"""
        return square is not None and square.piece_at is not None and square.piece_at.color in colors

    def confirm_piece(self, piece_type: Union[str, Piece], color: Optional[str] = None) -> bool:
        if isinstance(piece_type, Piece):
            piece_type, color = piece_type.type, piece_type.color
        return self.piece_at and self.piece_at.type == piece_type and (not color or self.piece_at.color == color)


class Board:
    COLORS = ("white", "brown", "grey", "black")
    TEAMS = (("white", "grey"), ("brown", "black"))

    def __init__(self):
        self.turn = "white"
        self.graveyard = []
        self.castling_rights = {a: [True] * 2 for a in self.COLORS}  # [kingside, queenside]  # can't use dict.fromkeys because of object mutation
        self.checked = dict.fromkeys(self.COLORS, False)
        self.frozen = self.checked.copy()
        self.layout: List[Optional[Square]] = [Square(a) for a in range(1, 16*16 + 1)]
        self.winner = None
        self.move_stack = []

        # empty out squares of the board to achieve the correct shape
        for a in list(range(2)) + list(range(14, 16)):
            self.layout[a*16+4 : a*16+12] = [None]*8
        for a in range(4, 12):
            self.layout[a*16 : a*16+2], self.layout[(a+1)*16-2 : (a+1)*16] = [[None]*2]*2

        # place the starting layout
        for n, a in enumerate(("grey", "brown", "white", "black")):
            for s in ([Square(Square.pos_rot90(chr(n2)+num.zfill(2), n), Piece(Piece.from_initial(p), a)) for row, num in (("rnbqkbnr", "3"), ("p"*8, "4")) for n2, p in enumerate(row, start=ord("E"))]
                      + [Square(Square.pos_rot90(s, n), Piece(Piece.from_initial(p), a)) for p, s in (("n", "N3"), ("b", "O1"), ("r", "P4"))]):
                self.update_square(s)

    def __str__(self):
        """Return the stringified board layout"""
        return "\n".join([str(a).replace("None", "<   >").replace("Square ", "")[1:-1] for a in chunk_list(self.layout, 16)])

    def __repr__(self):
        return f"<Board castling_rights={self.castling_rights} checked={self.checked} frozen={self.frozen} winner={self.winner} layout=\n{self}\n>"

    @property
    def move_count(self) -> int:
        # FIXME because mated people will get skipped, this wont notice it and will thus be off by whatever.
        # TODO either add NULL moves that also get skipped backwards when popping or manually create a move_count variable
        return len(self.move_stack) // 4

    @property
    def currently_frozen(self) -> List[str]:
        """Return the colors currently frozen by checkmate"""
        return [k for k, v in self.frozen.items() if v]

    def pop(self) -> bool:
        """Undo a move"""
        if not self.move_stack:
            return False
        move = self.move_stack.pop()
        if move.to_square.piece_at:
            self.graveyard.pop()
        self.update_square(move.from_square)
        self.update_square(move.to_square)
        if move.checks:
            self.checked = move.checks
        else:
            self.check_checks()  # should be redundant, but better safe than sorry
        self.update_frozen()
        # regrant castling rights if the move took them away
        if move.castling is not None:
            # same from move(), but with rook_start/_end swapped
            for index, rook_end, rook_start in ((0, "C5", "C7"), (1, "C12", "C9")):
                if move.castling[index]:
                    rook_sq: Square = self.get_square(Square.pos_rot90(rook_start, self.COLORS[::-1].index(move.from_square.piece_at.color)))
                    rook_target_sq: str = Square.pos_rot90(rook_end, self.COLORS[::-1].index(move.from_square.piece_at.color))
                    self.update_square(Square(rook_sq.position))
                    self.update_square(Square(rook_target_sq, rook_sq.piece_at))
            for n in range(2):
                if move.castling[n]:
                    self.castling_rights[move.from_square.piece_at.color][n] = True
                    break
        self.next_turn(-1)
        return True

    def check_checks(self):
        self.checked = {a.piece_at.color: Move.check_check(self, a) for a in self.get_kings()}

    def update_frozen(self):
        self.frozen = {k: self.is_mate(k) != 0 for k in self.frozen.keys()}

    def get_kings(self, color: Optional[str] = None, ignore: Union[None, str, List[str]] = None) -> List[Square]:
        """Fetch the kings of each color from the board. `ignore` to skip colors"""
        pass  # the following is not intended to be read as a docstring, it's just a broken up version of the one-liner following it
        """
        lst = []
        for col in (self.COLORS if color is None else make_iter(color)):
            if ignore is None or col not in make_iter(ignore):
                for sq in self.layout:
                    if sq and sq.piece_at == Piece("king", col):
                        lst.append(sq)
                else:
                    raise IndexError("Unreachable Code reached")
        return lst
        """
        return [[sq for sq in self.layout if sq and sq.piece_at == Piece("king", col)][0] for col in (self.COLORS if color is None else make_iter(color)) if ignore is None or col not in make_iter(ignore)]

    @classmethod
    def get_teams(cls, color: str, own_first=True) -> tuple:
        """
        Return the team color pairs, sorted by the current player.
        If own_first, then color will be part of the first returned team, otherwise it will be part of the second team
        """
        return cls.TEAMS[::-1 if color in Board.TEAMS[int(own_first)] else 1]

    @classmethod
    def get_teammate(cls, color: str) -> Optional[str]:
        """Return the color of color's teammate"""
        if color not in cls.COLORS:
            return None
        return cls.COLORS[cls.COLORS.index(color)-2]

    def update_square(self, square: Square):
        self.layout[int(square) - 1] = square

    def get_square(self, num: Union[int, Square, str]) -> Square:
        """
        Return an up to date square at num.
        num is either an integer counting the squares left to right, top to bottom since the top left square
          or a Square which may or may not be the same one returned by this
          or a string denoting the position, e.g. "e13"
        """
        if isinstance(num, str):
            num = Square.pos_stoi(num)
        return self.layout[int(num) - 1]

    def next_turn(self, jumps=1, skip_frozen=True) -> None:
        """Change the currently active color, allows for negative jumps"""
        self.turn = self.COLORS[(self.COLORS.index(self.turn) + jumps) % 4]
        if skip_frozen and self.frozen[self.turn]:
            self.next_turn(jumps, skip_frozen)

    def move(self, move: "Move") -> None:
        """Execute a Move"""
        team, enemy_team = self.get_teams(move.from_square.piece_at.color)
        if move.to_square.piece_at:
            self.graveyard.append(move.to_square.piece_at)
        self.update_square(Square(move.from_square.position))
        self.update_square(Square(move.to_square.position, move.promotion or move.from_square.piece_at))

        if move.castling is not None:
            for index, rook_start, rook_end in ((0, "C5", "C7"), (1, "C12", "C9")):
                if move.castling[index]:
                    rook_sq: Square = self.get_square(Square.pos_rot90(rook_start, self.COLORS[::-1].index(move.from_square.piece_at.color)))
                    rook_target_sq: str = Square.pos_rot90(rook_end, self.COLORS[::-1].index(move.from_square.piece_at.color))
                    self.update_square(Square(rook_sq.position))
                    self.update_square(Square(rook_target_sq, rook_sq.piece_at))
            for n in range(2):
                if move.castling[n]:
                    self.castling_rights[move.from_square.piece_at.color][n] = False
                    break

        self.checked = move.checks or self.checked
        self.update_frozen()
        if all([self.frozen[a] for a in enemy_team]):  # all(map(self.is_mate, enemy_team)):
            self.winner = team
        self.move_stack.append(move)
        self.next_turn()

    def is_valid(self, move: "Move", ignore_turn=False, ignore_check=False) -> tuple:
        """Check if a Move is valid, if not Return an appropriate error message."""
        if move.to_square is None:
            return False, CheckErrorMsg.SquareToOutOfBounds

        if move.from_square.piece_at is None:
            return False, CheckErrorMsg.SquareFromNoPiece

        if not ignore_turn and not move.from_square.piece_at.color == self.turn:
            return False, CheckErrorMsg.SquareFromNotYourPiece

        if move.from_square == move.to_square:
            return False, CheckErrorMsg.SquareFromAndToSame

        team, enemy_team = self.get_teams(move.from_square.piece_at.color)
        if move.to_square.piece_at is not None and move.to_square.piece_at.color in team:
            return False, CheckErrorMsg.FriendlyFire

        # border checks for this chess variant's specialty: fortresses
        if list_in_list((move.from_square.position, move.to_square.position), [Square.pos_rot90(a+str(b).zfill(2), n) for n in range(4) for a in str_range("K", "P") for b in range(1, 7)]) and (
                # first check whether the move needs to be checked for borders in the first place (check if from/to square is inside a fortress)
                # now check knight movement: (8 impossible moves each corner)
                any([list_in_list((move.from_square.position, move.to_square.position), Square.pos_rot90_list(a, n), True) for n in range(4) for a in (
                        ("F03", "D02"),
                        ("F03", "D04"),
                        ("F04", "D03"),
                        ("E03", "C02"),
                        ("E03", "C04"),
                        ("E03", "D01"),
                        ("E04", "D02"),
                        ("E04", "C03")
                )])
                # rook movement: (2 impossible rays each square)
                or (list_in_list((move.from_square.x, move.to_square.x), "MN", True) and not (list_in_list((move.from_square.row, move.to_square.row), range(1, 5), True) or list_in_list((move.from_square.row, move.to_square.row), range(5, 17), True)))
                or (list_in_list((move.from_square.x, move.to_square.x), "CD", True) and not (list_in_list((move.from_square.row, move.to_square.row), range(1, 13), True) or list_in_list((move.from_square.row, move.to_square.row), range(13, 17), True)))
                or (list_in_list((move.from_square.row, move.to_square.row), (3, 4), True) and not (list_in_list((move.from_square.x, move.to_square.x), str_range("A", "D"), True) or list_in_list((move.from_square.x, move.to_square.x), str_range("E", "P"), True)))
                or (list_in_list((move.from_square.row, move.to_square.row), (13, 14), True) and not (list_in_list((move.from_square.x, move.to_square.x), str_range("A", "L"), True) or list_in_list((move.from_square.x, move.to_square.x), str_range("M", "P"), True)))
                # bishop movement (8 impossible rays each square)
                or any([any([all([Square.square_in_ray((move.from_square, move.to_square), *Square.pos_rot90_list(xy, n)) for xy in a]) for a in (
                    (("K03", "L04"), ("M05", "N06")),
                    (("L03", "M04"), ("N05", "N05")),
                    (("A14", "L03"), ("M02", "N01")),
                    (("K03", "A13"), ("M01", "M01")),
                    (("P01", "M04"), ("L05", "A16")),
                    (("P02", "N04"), ("M05", "B16")),
                    (("P03", "O04"), ("N05", "C16")),
                    (("D16", "N06"), ("P04", "P04")))
                             ]) for n in range(4)])
        ):
            return False, CheckErrorMsg.WallsInTheWay

        if move.promotion:
            if not move.from_square.piece_at.type == "pawn":
                return False, CheckErrorMsg.PromotionFromNonPawn
            if move.to_square.position not in self.get_pawn_promotion_rank(move.from_square.piece_at.color):
                return False, CheckErrorMsg.PromotionOutOfBounds

        if move.to_square.piece_at is not None and move.to_square.piece_at.color in self.currently_frozen:
            return False, CheckErrorMsg.TargetFrozen

        pm = Move.possible_moves(self, move.from_square)
        if move.to_square not in pm:
            print(move.to_square, pm)
            return False, CheckErrorMsg.SquareToIllegal

        # check castling next
        castling = False
        if move.from_square == Square(Square.pos_rot90("C8", self.COLORS[::-1].index(move.from_square.piece_at.color)), Piece("king", move.from_square.piece_at.color)):
            for n, a in enumerate((6, 10)):
                if move.to_square.position == Square.pos_rot90(f"C{a}", self.COLORS[::-1].index(move.from_square.piece_at.color)):
                    move.castling = ([True, False], [False, True])[n]
                    castling = True
                    break

        # check checks, this should always be last, because it may be ignored
        for pos in ([self.get_neighbour(move.from_square, step, 0, adjust=True).position for step in ((1,) if move.castling[0] else (-1, -2))] if castling else []) + [move.to_square.position]:
            sq = self.get_square(pos)
            # ignore to ignore "captured" kings, tho that shouldn't be possible in this game in the first place...
            ignore = sq.piece_at.color if sq.piece_at and sq.piece_at.type == "king" else None

            # temporarily execute the move and check what it does, then undo that move
            tmp = self.layout.copy()
            self.update_square(Square(move.from_square.position))
            self.update_square(Square(pos, move.promotion or move.from_square.piece_at))
            move.checks = {king_sq.piece_at.color: Move.check_check(self, king_sq) for king_sq in self.get_kings(ignore=ignore)}
            self.layout = tmp

            if not ignore_check and move.checks.get(move.from_square.piece_at.color, True):
                return False, CheckErrorMsg.CheckmateYourself

            c = (set(team) - {move.from_square.piece_at.color}).pop()
            if not ignore_check and move.checks.get(c, True) and not self.checked.get(c, False):
                return False, CheckErrorMsg.CheckmateTeammate

        return True, move.checks

    def get_neighbour(self, square: "Square", column: Union[int, tuple, list], row: int = 0, adjust=False) -> Optional[Square]:
        """
        Return the neighbour of the square, offset by column and row with the origin at top left.
        `adjust` adjusts the orientation based on the grey color,
          so D12 + (5, 1) with a black rook on D12 would return E07 instead of I13. (Keep in mind, the board is flipped vertically (A1 is top left))
        """
        if not isinstance(column, int):
            column, row = column
        if square.piece_at is not None and adjust:
            # direction adjusting
            column, row = ((row if square.piece_at.color == "black" else -row if square.piece_at.color == "brown" else column if square.piece_at.color == "grey" else -column),
                           (row if square.piece_at.color == "grey"  else -row if square.piece_at.color == "white" else column if square.piece_at.color == "brown" else -column))
        column, row = (chr(ord(square.x) + column),
                square.row + row)
        if column not in str_range("A", "P") or row not in range(1, 16 + 1):
            return None
        target = self.get_square(column + str(row))
        if target is None:
            return None
        return target

    @staticmethod
    def get_pawn_promotion_rank(color: str) -> List[str]:
        """Return all squares for `color` in which pawn promotion would be legal"""
        # start with black's POV and rotate accordingly; list all squares since rank 8 (file J on the board), excluding squares that are OutOfBounds
        return [Square.pos_rot90(s, Board.COLORS[::-1].index(color)) for s in [f"{l}{n}" for l in str_range("J", "P") for n in range(3 if l in "JKL" else 1, 15 if l in "JKL" else 17) if not (l in "OP" and 4 < n < 13)]]

    def is_mate(self, color: str) -> int:  # 0: None, 1: Checkmate, 2: Stalemate
        if Move.possible_legal_moves_color(self, color):
            return 0
        if self.checked[color]:
            return 1
        return 2


class Move:
    def __init__(self, from_square: Square, to_square: Square, promotion: Optional[Piece] = None):
        self.from_square = from_square
        self.to_square = to_square
        self.promotion = promotion
        self._castling = None
        self._checks = None

    def __str__(self):
        return f"{self.from_square.piece_at.type.capitalize()} from {self.from_square.position} to {self.to_square.position}{f' beating the {self.to_square.piece_at} there' if self.to_square.piece_at else ''}{' to become a '+self.promotion.type.capitalize() if self.promotion is not None else ''}"

    def __repr__(self):
        return f"<{f'{self.from_square.piece_at.color}: ' if self.from_square and self.from_square.piece_at else ''}{str(self)}>"

    @property
    def checks(self) -> Optional[dict]:
        return self._checks

    @checks.setter
    def checks(self, _checks: dict):
        self._checks = _checks

    @property
    def castling(self) -> list:
        return self._castling

    @castling.setter
    def castling(self, _castling: list):
        self._castling = _castling

    @staticmethod
    def possible_moves(board: Board, square: Square) -> List[Square]:
        """Return a list of Squares that contain every Square that the piece on `square` can travel to, ignores Fortress Walls and frozen players"""
        team, enemy_team = Board.get_teams(square.piece_at.color)
        for cf in board.currently_frozen:
            if cf in enemy_team:
                enemy_team.remove(cf)
        result = []
        if square.piece_at.type == "pawn":
            # check the ahead square, the jump ahead (from home row) and the two attack squares
            t1 = board.get_neighbour(square, (0, 1), adjust=True)
            if t1 is None:
                return []
            if t1.piece_at is None:
                result.append(t1)
                if square.position in [Square.pos_rot90(s, Board.COLORS[::-1].index(square.piece_at.color)) for s in [f"D{n}" for n in range(5, 13)]]:
                    t2 = board.get_neighbour(square, (0, 2), adjust=True)
                    if t2 and t2.piece_at is None:
                        result.append(t2)
            t1 = board.get_neighbour(square, (1, 1), adjust=True)
            if Square.check_enemy(t1, enemy_team):
                result.append(t1)
            t1 = board.get_neighbour(square, (-1, 1), adjust=True)
            if Square.check_enemy(t1, enemy_team):
                result.append(t1)
            return result

        elif square.piece_at.type == "king":
            # check every square around the king: orthogonal and diagonal
            for direction in ((1, 1), (1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1)):
                t1 = board.get_neighbour(square, direction)  # adjusting is irrelevant, because we check the full circle anyway
                if t1 is None:  # Square out of bounds
                    continue
                elif t1.piece_at is None or t1.piece_at.color in enemy_team:
                    # we don't check for checks here, because that's only a concern for legal moves and there (Move.possible_legal_moves_color) we use Board.is_valid to achieve that
                    result.append(t1)

            if any(board.castling_rights[square.piece_at.color]):
                for queenside, castling in enumerate(board.castling_rights[square.piece_at.color]):
                    if not castling:
                        continue
                    for step in range(1, 3+queenside):
                        t1 = board.get_neighbour(square, -step if queenside else step, 0, adjust=True)
                        if t1.piece_at is not None:
                            break
                    else:
                        result.append(board.get_neighbour(square, -2 if queenside else 2, 0, adjust=True))
            return result

        # everything following this is no longer self-returning due to queen
        if square.piece_at.type in ("rook", "queen"):
            # check every tile in an orthogonal ray (until piece or OOB)
            for a in range(4):
                for b in itertools.count(start=1):
                    t1 = board.get_neighbour(square, ((b, 0), (0, b), (-b, 0), (0, -b))[a])
                    if t1 is None:  # Square out of bounds
                        break
                    if t1.piece_at is None:  # empty Square
                        result.append(t1)
                        continue
                    if t1.piece_at.color in enemy_team:
                        result.append(t1)
                    break

        if square.piece_at.type in ("bishop", "queen"):
            # check every tile in a diagonal ray (until piece or OOB)
            for a in range(4):
                for b in itertools.count(start=1):
                    t1 = board.get_neighbour(square, ((b, b), (b, -b), (-b, -b), (-b, b))[a])
                    if t1 is None:  # Square out of bounds
                        break
                    if t1.piece_at is None:  # empty Square
                        result.append(t1)
                        continue
                    if t1.piece_at.color in enemy_team:
                        result.append(t1)
                    break

        if square.piece_at.type in ("knight", "queen"):
            # check every knight move
            for a in range(4):
                for b in range(2):
                    t1 = board.get_neighbour(square, (((1, 2), (-1, 2)), ((1, -2), (-1, -2)), ((2, 1), (2, -1)), ((-2, 1), (-2, -1)))[a][b])
                    if t1 is None:  # Square out of bounds
                        continue
                    if t1.piece_at is None or t1.piece_at.color in enemy_team:  # empty Square or (non-frozen) enemy
                        result.append(t1)
        return result

    @staticmethod
    def check_check(board: Board, square: Square) -> bool:
        if square is None or square.piece_at is None or not square.piece_at.type == "king":
            return False
        team, enemy_team = board.get_teams(square.piece_at.color)
        cf = board.currently_frozen
        for a in range(4):
            # checking for rook
            for b in itertools.count(start=1):
                t1 = board.get_neighbour(square, ((b, 0), (0, b), (-b, 0), (0, -b))[a])
                if t1 is None:
                    break
                if t1.piece_at is None:
                    continue
                if t1.piece_at.color in enemy_team and t1.piece_at.type in ("rook", "queen") and t1.piece_at.color not in cf:
                    return True
                break
            # checking for bishop
            for b in itertools.count(start=1):
                t1 = board.get_neighbour(square, ((b, b), (b, -b), (-b, -b), (-b, b))[a])
                if t1 is None:
                    break
                if t1.piece_at is None:
                    continue
                if t1.piece_at.color in enemy_team and t1.piece_at.type in ("bishop", "queen") and t1.piece_at.color not in cf:
                    return True
                else:
                    break
            # checking for knight
            for b in range(2):
                t1 = board.get_neighbour(square, (((1, 2), (-1, 2)), ((1, -2), (-1, -2)), ((2, 1), (2, -1)), ((-2, 1), (-2, -1)))[a][b])
                if t1 is None or t1.piece_at is None:
                    continue
                if t1.piece_at.color in enemy_team and t1.piece_at.type in ("knight", "queen") and t1.piece_at.color not in cf:
                    return True
        for corner in range(4):
            # TODO find a more readable solution
            # check all 4 corners of a king for an enemy pawn of the correct color
            t1 = board.get_neighbour(square, ((-1, 1), (-1, -1), (1, 1), (1, -1))[corner])
            if not (t1 and t1.piece_at and t1.piece_at.type == "pawn"):
                continue
            # reminder:
            # COLORS = ("white", "brown", "grey", "black")
            # TEAMS = (("white", "grey"), ("brown", "black"))
            index = Board.COLORS.index(square.piece_at.color)-1
            if square.piece_at.color in Board.TEAMS[1]:
                # if king is brown or black, set index to grey for the top corners (1, 3) and white for the bottom corners (0, 2)
                if corner & 1 == int(square.piece_at.color == Board.COLORS[1]):  # if corner is uneven and king's color is brown or corner is even and king's color is black
                    index -= 2  # results in (0, -2, 0, -2) for brown and (-2, 0, -2, 0) for black
            else:
                # if king is white or grey, set index to black for the left corners (0, 1) and brown for the right corners (2, 3)
                if square.piece_at.color == Board.COLORS[2]:
                    index -= 2
                index += corner - (corner & 1)  # floor the unevenness to get (0, 0, 2, 2)
            if t1.piece_at.color == Board.COLORS[index] and t1.piece_at.color not in cf:
                return True
        return False

    @classmethod
    def possible_legal_moves_color(cls, board: Board, color: str) -> List["Move"]:
        """Return a list of all the possible moves that `color` has as option"""
        # get all squares that have a piece from `color`
        squares = [a for a in board.layout if a is not None and a.piece_at is not None and a.piece_at.color == color]
        if not squares:
            raise ValueError(f"invalid color: {color}, or no pieces for that color")
        cf = board.currently_frozen
        pm = []
        for square in squares:
            for possible_square in filter(lambda s: s.piece_at is None or s.piece_at.color not in cf, cls.possible_moves(board, square)):
                # verify the moves and add them, add them twice if a pawn promotion is possible
                promotion = square.piece_at.type == "pawn" and possible_square.position in Board.get_pawn_promotion_rank(square.piece_at.color)
                for c in range(2 if promotion else 1):  # run this once, if promotion: repeat it
                    move = cls(square, possible_square, promotion=Piece("queen", color) if promotion and c else None)
                    if board.is_valid(move, ignore_turn=True, ignore_check=True)[0]:
                        pm.append(move)
        return pm
