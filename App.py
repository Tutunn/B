#!/usr/bin/env python3
"""
Bagh Bandi Game - CLI version with AI player

Bagh Bandi is a traditional Indian tiger hunt game played on an Alquerque board.
This implementation supports:
- Accurate Alquerque board structure
- Piles of goats (initially 5 goats in each of 4 points)
- Full movement and capture rules for goats and tigers
- Win condition detection
- Basic AI that plays for the computer (plays tiger or goat)
- Text-based play with board display in console

Usage:
Run this script and follow on-screen prompts.

Author: BLACKBOXAI empowered
Date: 2024
"""

import sys
import copy
import random

# Constants for pieces
EMPTY = '.'
TIGER = 'T'
GOAT = 'G'  # single goat
# Piles of goats represented by int >1 (number of stacked goats at single point), e.g. '5' piles means 5 goats stacked

# Board point count and connections for Alquerque
# The board has 25 points, arranged in 5 rows and 5 columns
# Points identified by (row,col): (0..4, 0..4)

# Moves are allowed along lines that connect points:
# Vertical, horizontal, and diagonals where they connect

# Adjacency list per point (row,col) = list of connected points
# To avoid recomputing, we predefine adjacency based on Alquerque pattern

# Board layout:
#  0--1--2--3--4
#  |\/|\/|\/|\/|
#  5--6--7--8--9
#  |\/|\/|\/|\/|
# 10-11-12-13-14
#  |\/|\/|\/|\/|
# 15-16-17-18-19
#  |\/|\/|\/|\/|
# 20-21-22-23-24

# Positions (row, col) -> point id mapping for ease of use
# We'll use (row, col) tuple keys

# Precomputed adjacency per standard alquerque rules
ADJACENCY = {
    (0,0): [(0,1),(1,0),(1,1)],
    (0,1): [(0,0),(0,2),(1,1)],
    (0,2): [(0,1),(0,3),(1,1),(1,2),(1,3)],
    (0,3): [(0,2),(0,4),(1,3)],
    (0,4): [(0,3),(1,3),(1,4)],
    (1,0): [(0,0),(1,1),(2,0)],
    (1,1): [(0,0),(0,1),(0,2),(1,0),(1,2),(2,0),(2,1),(2,2)],
    (1,2): [(0,2),(1,1),(1,3),(2,1),(2,2),(2,3)],
    (1,3): [(0,2),(0,3),(0,4),(1,2),(1,4),(2,2),(2,3),(2,4)],
    (1,4): [(0,4),(1,3),(2,4)],
    (2,0): [(1,0),(1,1),(2,1),(3,0),(3,1)],
    (2,1): [(1,1),(1,2),(2,0),(2,2),(3,1),(3,2)],
    (2,2): [(1,1),(1,2),(1,3),(2,1),(2,3),(3,1),(3,2),(3,3)],
    (2,3): [(1,2),(1,3),(2,2),(2,4),(3,2),(3,3),(3,4)],
    (2,4): [(1,3),(1,4),(2,3),(3,3),(3,4)],
    (3,0): [(2,0),(2,1),(3,1),(4,0),(4,1)],
    (3,1): [(2,1),(2,2),(3,0),(3,2),(4,0),(4,1),(4,2)],
    (3,2): [(2,2),(2,3),(3,1),(3,3),(4,1),(4,2),(4,3)],
    (3,3): [(2,3),(2,4),(3,2),(3,4),(4,2),(4,3),(4,4)],
    (3,4): [(2,4),(3,3),(4,3),(4,4)],
    (4,0): [(3,0),(3,1),(4,1)],
    (4,1): [(3,1),(3,2),(4,0),(4,2)],
    (4,2): [(3,1),(3,2),(3,3),(4,1),(4,3)],
    (4,3): [(3,2),(3,3),(4,2),(4,4)],
    (4,4): [(3,3),(3,4),(4,3)]
}

# Board points list for iteration
POINTS = list(ADJACENCY.keys())

# Game configuration constants
GOATS_TOTAL = 20
GOATS_PER_PILE = 5  # initial goats per pile in 4 piles

def point_valid(pt):
    return pt in ADJACENCY

def points_adjacent(p1, p2):
    return p2 in ADJACENCY.get(p1, [])

def midpoint(p1, p2):
    return ((p1[0]+p2[0])//2, (p1[1]+p2[1])//2)


class BaghBandiGame:
    def __init__(self):
        """
        Initialize the board, pieces, and piles.
        Board is dict mapping point -> stack count or pieces:
          - EMPTY: '.' empty
          - TIGER: 'T'
          - GOAT: 'G' single goat (when only one goat)
          - int >1: pile of goats count at that point
        """
        # Set up empty board
        self.board = {pt: EMPTY for pt in POINTS}
        self.goats_in_supply = GOATS_TOTAL  # goats still off-board (for initial pile building)
        self.goats_captured = 0

        # Place 2 tigers in starting positions (middle column 2nd and 4th point from top)
        self.tiger_positions = [(1,2), (3,2)]
        for tpos in self.tiger_positions:
            self.board[tpos] = TIGER

        # Place goats in 4 piles on second left and second right columns, at points 1 & 3 from top
        # That means piles at four specific points: (0,1), (2,1), (0,3), (2,3)
        self.goat_pile_positions = [(0,1), (2,1), (0,3), (2,3)]
        for gp in self.goat_pile_positions:
            self.board[gp] = GOATS_PER_PILE
            self.goats_in_supply -= GOATS_PER_PILE

        # Current turn: 'goat' or 'tiger'; goats always start first
        self.turn = 'goat'

        # Record if the game is over
        self.game_over = False
        self.winner = None

        # For AI player (computer)
        # User plays 'goat' or 'tiger' (ask at start)
        self.player_piece = None
        self.computer_piece = None

        # For tiger multiple captures tracking (cannot jump back and forth over same pile in same move)
        self.tiger_last_jump_piles = set()

    def display_board(self):
        """
        Render the board state in text to console.
        Shows points with pieces or pile counts.
        Legend:
          T = tiger
          G = single goat
          numbers = goat pile count
          . = empty
        Coordinates are displayed for player ease.
        """
        print("    0 1 2 3 4")
        print("   ------------")
        for r in range(5):
            print(f"{r} | ", end='')
            for c in range(5):
                val = self.board.get((r,c), ' ')
                if val == TIGER:
                    print('T ', end='')
                elif val == EMPTY:
                    print('. ', end='')
                elif isinstance(val, int):
                    # pile of goats
                    print(f"{val} ", end='')
                elif val == GOAT:
                    print('G ', end='')
                else:
                    print('? ', end='')
            print()
        print(f"Goats in supply (off board): {self.goats_in_supply}")
        print(f"Goats captured: {self.goats_captured}")
        print(f"Goats on board: {GOATS_TOTAL - self.goats_in_supply - self.goats_captured}")
        print(f"Turn: {self.turn.title()}")

    def is_adjacent(self, p1, p2):
        """Return True if p2 adjacent to p1 on the board."""
        return p2 in ADJACENCY.get(p1, [])

    def can_goat_move_here(self, from_pt, to_pt):
        """Check if a goat can move from from_pt to to_pt according to the rules."""
        if not point_valid(to_pt):
            return False
        # Destination must be empty
        if self.board[to_pt] != EMPTY:
            return False
        # Must be adjacent
        if not self.is_adjacent(from_pt, to_pt):
            return False
        # Goats cannot move on piles or single goats to form piles (no stacking allowed outside initial)
        # So destination must be empty, enforced above
        return True

    def can_tiger_move_here(self, from_pt, to_pt):
        """Check if a tiger can move (non-capturing) from from_pt to to_pt."""
        if not point_valid(to_pt):
            return False
        if self.board[to_pt] != EMPTY:
            return False
        if not self.is_adjacent(from_pt, to_pt):
            return False
        return True

    def can_tiger_capture(self, from_pt, over_pt, to_pt):
        """
        Check if tiger at from_pt can jump over piece(s) at over_pt and land at to_pt capturing the top goat.
        Tigers can capture single goats or the top goat in piles.
        Only one capture allowed per turn.
        Jump must be in straight line and follow pattern.
        """
        if not (point_valid(from_pt) and point_valid(over_pt) and point_valid(to_pt)):
            return False
        # Must be in straight line: from_pt, over_pt, to_pt are colinear with over_pt the midpoint of from_pt and to_pt
        mx = (from_pt[0] + to_pt[0]) // 2
        my = (from_pt[1] + to_pt[1]) // 2
        if (mx, my) != over_pt:
            return False
        # from_pt and to_pt must be two steps apart along adjacency lines
        dr = abs(to_pt[0] - from_pt[0])
        dc = abs(to_pt[1] - from_pt[1])
        if (dr not in (0, 2)) or (dc not in (0, 2)) or (dr + dc) == 0:
            return False
        # to_pt must be empty
        if self.board[to_pt] != EMPTY:
            return False
        # over_pt must have goat(s)
        v = self.board[over_pt]
        if isinstance(v, int) and v >= 1:
            return True
        if v == GOAT:
            return True
        return False

    def get_all_tiger_captures(self, tiger_pos):
        """
        Returns all possible capturing moves for a tiger at tiger_pos.
        Returns list of tuples: (over_pt, to_pt)
        """
        captures = []
        for to_pt in POINTS:
            if self.can_tiger_capture(tiger_pos, midpoint(tiger_pos, to_pt), to_pt):
                captures.append((midpoint(tiger_pos, to_pt), to_pt))
        return captures

    def get_all_tiger_moves(self, tiger_pos):
        """
        Returns all possible non-capturing moves for tiger at tiger_pos.
        """
        moves = []
        for adj in ADJACENCY[tiger_pos]:
            if self.can_tiger_move_here(tiger_pos, adj):
                moves.append(adj)
        return moves

    def get_all_goat_moves(self):
        """
        Returns all possible goat moves:
        - Move top goat from any pile to adjacent empty
        - Move any single goat to adjacent empty
        Returns list of (start_pt, end_pt)
        """
        moves = []
        # First, top goats from piles
        for pt in POINTS:
            val = self.board[pt]
            if isinstance(val, int) and val > 1:
                # Top goat can move to adjacent empty points
                for adj in ADJACENCY[pt]:
                    if self.board[adj] == EMPTY:
                        moves.append((pt, adj))
        # Then, single goats
        for pt in POINTS:
            if self.board[pt] == GOAT:
                for adj in ADJACENCY[pt]:
                    if self.board[adj] == EMPTY:
                        moves.append((pt, adj))
        return moves

    def move_goat(self, start_pt, end_pt):
        """Move a goat from start_pt to end_pt. Respect piles and single goats."""
        v = self.board[start_pt]
        if isinstance(v, int) and v > 1:  # pile - remove one goat from pile, place single goat at end_pt
            self.board[start_pt] = v - 1
            if self.board[end_pt] == EMPTY:
                self.board[end_pt] = GOAT
            else:
                # Should never happen since moves valid only to empty
                raise ValueError("Invalid goat move destination")
        elif v == GOAT:
            # move single goat
            self.board[end_pt] = GOAT
            self.board[start_pt] = EMPTY
        else:
            raise ValueError("Invalid move goat from this position")

    def move_tiger(self, start_pt, end_pt):
        """Move tiger from start_pt to end_pt."""
        if self.board[start_pt] != TIGER or self.board[end_pt] != EMPTY:
            raise ValueError("Invalid tiger move")
        self.board[end_pt] = TIGER
        self.board[start_pt] = EMPTY
        # Update tiger positions list
        if start_pt in self.tiger_positions:
            self.tiger_positions.remove(start_pt)
            self.tiger_positions.append(end_pt)

    def perform_tiger_capture(self, start_pt, over_pt, end_pt):
        """
        Tiger jumps over over_pt to end_pt capturing top goat from pile or single goat.
        """
        if not self.can_tiger_capture(start_pt, over_pt, end_pt):
            raise ValueError("Invalid tiger capture")
        # Remove top goat from pile or single goat at over_pt
        val = self.board[over_pt]
        if isinstance(val, int) and val > 1:
            self.board[over_pt] = val - 1
        elif val == GOAT:
            self.board[over_pt] = EMPTY
        else:
            raise ValueError("No goat to capture at over_pt")
        self.goats_captured += 1

        # Move tiger
        self.move_tiger(start_pt, end_pt)

    def is_goat_immobilized(self, tiger_pos):
        """
        Check if tiger at tiger_pos is immobilized (cannot move or capture).
        """
        if self.get_all_tiger_captures(tiger_pos):
            return False
        if self.get_all_tiger_moves(tiger_pos):
            return False
        return True

    def check_win_condition(self):
        """
        Check whether goats win (both tigers immobilized),
        or tigers win (captured goats so goats cannot immobilize tigers)
        or game continues.
        """
        # Both tigers immobilized -> goats win
        immobilized = all(self.is_goat_immobilized(tpos) for tpos in self.tiger_positions)
        if immobilized:
            self.game_over = True
            self.winner = 'goats'
            return 'goats'

        # Tigers win if goats captured enough to prevent immobilization
        # Usually if goats are below certain number, they can't trap tigers
        # We use arbitrary threshold: if goats left on board < 10, tigers win
        goats_left_on_board = GOATS_TOTAL - self.goats_captured - self.goats_in_supply
        if goats_left_on_board < 10:
            self.game_over = True
            self.winner = 'tigers'
            return 'tigers'

        return None  # no winner yet

    def goat_turn(self):
        """
        Handle goat player turn input and move execution.
        """
        print("\nGoat's turn. You can move:")
        valid_moves = self.get_all_goat_moves()
        if not valid_moves:
            print("No valid moves for goats. Tigers win!")
            self.game_over = True
            self.winner = 'tigers'
            return

        self.display_board()

        # Ask for move input
        while True:
            print("Enter your move in format 'start_row start_col end_row end_col'")
            print("Example: '0 1 0 0' to move from (0,1) to (0,0)")
            inp = input("Your move: ").strip()
            if inp.lower() in ('q','quit','exit'):
                print("Exiting game.")
                sys.exit(0)
            try:
                sr, sc, er, ec = map(int, inp.split())
                start = (sr, sc)
                end = (er, ec)
            except:
                print("Invalid input format. Try again.")
                continue

            if (start, end) not in valid_moves:
                print("Invalid move according to rules. Try again.")
                continue

            # Execute move
            try:
                self.move_goat(start, end)
            except Exception as e:
                print(f"Error executing move: {e}")
                continue
            break

    def tiger_turn(self):
        """
        Handle tiger player turn input and move/capture execution.
        """
        print("\nTiger's turn.")
        self.display_board()
        # Tigers can capture or move:
        # Show possible captures or moves for user

        # Gather all captures for tigers
        all_captures = []
        for tpos in self.tiger_positions:
            caps = self.get_all_tiger_captures(tpos)
            # caps is list of (over_pt, to_pt)
            for capture in caps:
                all_captures.append((tpos, capture[0], capture[1]))
        if all_captures:
            print("Available captures:")
            for idx, (st, ov, en) in enumerate(all_captures):
                print(f"{idx}: Tiger at {st} capture goat/pile at {ov} and move to {en}")
        else:
            print("No captures available. Tigers can move:")

        # If no captures, show moves
        all_moves = []
        if not all_captures:
            for tpos in self.tiger_positions:
                moves = self.get_all_tiger_moves(tpos)
                for mv in moves:
                    all_moves.append((tpos,mv))

            if all_moves:
                print("Available moves:")
                for idx, (st, en) in enumerate(all_moves):
                    print(f"{idx}: Tiger move from {st} to {en}")

        if not all_captures and not all_moves:
            print("No moves or captures possible for tigers. Goats win!")
            self.game_over = True
            self.winner = 'goats'
            return

        # Ask user to pick move/capture
        while True:
            if all_captures:
                inp = input("Choose capture index or 'pass' to skip: ").strip()
                if inp.lower() in ('q', 'quit', 'exit'):
                    print("Exiting game.")
                    sys.exit(0)
                if inp.lower() == 'pass':
                    # Tigers skip capture (allowed), move to moves or pass turn
                    if all_moves:
                        continue  # go to moves selection below
                    else:
                        break  # no moves, end turn
                try:
                    choice = int(inp)
                    if 0 <= choice < len(all_captures):
                        st, ov, en = all_captures[choice]
                        self.perform_tiger_capture(st, ov, en)
                        break
                    else:
                        print("Invalid selection.")
                except:
                    print("Invalid input.")
            else:
                inp = input("Choose move index or 'pass' to skip: ").strip()
                if inp.lower() in ('q', 'quit', 'exit'):
                    print("Exiting game.")
                    sys.exit(0)
                if inp.lower() == 'pass':
                    break
                try:
                    choice = int(inp)
                    if 0 <= choice < len(all_moves):
                        st, en = all_moves[choice]
                        self.move_tiger(st, en)
                        break
                    else:
                        print("Invalid selection.")
                except:
                    print("Invalid input.")

    def ai_goat_move(self):
        """
        AI player logic for goat moves:
        Prefer moving top goat from piles to block tigers or occupy strategic positions.
        """
        possible_moves = self.get_all_goat_moves()
        if not possible_moves:
            return False
        # Simple strategy: move randomly for now
        move = random.choice(possible_moves)
        try:
            self.move_goat(move[0], move[1])
            print(f"AI-Goat moved from {move[0]} to {move[1]}")
            return True
        except Exception:
            return False

    def ai_tiger_move(self):
        """
        AI player logic for tiger:
        Prioritize captures, if none pick random move.
        """
        captures = []
        for tpos in self.tiger_positions:
            caps = self.get_all_tiger_captures(tpos)
            for over_pt, to_pt in caps:
                captures.append((tpos, over_pt, to_pt))
        if captures:
            c = random.choice(captures)
            self.perform_tiger_capture(c[0], c[1], c[2])
            print(f"AI-Tiger captured from {c[0]} over {c[1]} to {c[2]}")
            return True
        else:
            moves = []
            for tpos in self.tiger_positions:
                ms = self.get_all_tiger_moves(tpos)
                for mv in ms:
                    moves.append((tpos, mv))
            if moves:
                m = random.choice(moves)
                self.move_tiger(m[0], m[1])
                print(f"AI-Tiger moved from {m[0]} to {m[1]}")
                return True
        return False

    def user_choose_side(self):
        """
        Ask the user which side they want to play.
        """
        while True:
            choice = input("Choose your side: (G)oat / (T)iger: ").strip().lower()
            if choice in ('g', 'goat'):
                self.player_piece = 'goat'
                self.computer_piece = 'tiger'
                print("You play as Goats. Goats start first.")
                break
            elif choice in ('t', 'tiger'):
                self.player_piece = 'tiger'
                self.computer_piece = 'goat'
                print("You play as Tigers. Goats start first, then your turn.")
                break
            else:
                print("Invalid choice, enter G or T.")

    def play(self):
        print("Welcome to Bagh Bandi Game!")
        self.user_choose_side()

        while not self.game_over:
            if self.turn == self.player_piece:
                if self.turn == 'goat':
                    self.goat_turn()
                else:
                    self.tiger_turn()
            else:
                # AI turn
                if self.turn == 'goat':
                    moved = self.ai_goat_move()
                    if not moved:
                        print("AI-Goat has no valid moves, Tigers win!")
                        self.game_over = True
                        self.winner = 'tigers'
                        break
                else:
                    moved = self.ai_tiger_move()
                    if not moved:
                        print("AI-Tiger has no valid moves, Goats win!")
                        self.game_over = True
                        self.winner = 'goats'
                        break

            # Check win condition after each move
            winner = self.check_win_condition()
            if winner:
                print(f"\nGame Over! {winner.title()} win the game!")
                self.game_over = True
                self.winner = winner
                self.display_board()
                break

            # Switch turn
            self.turn = 'goat' if self.turn == 'tiger' else 'tiger'

        print("Thank you for playing Bagh Bandi!")

if __name__ == "__main__":
    game = BaghBandiGame()
    game.play()

