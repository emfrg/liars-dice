"""
Core game state management for Liar's Dice.
Handles dice, bids, challenges, and game flow.
"""

import random
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from collections import Counter


@dataclass
class Bid:
    """Represents a bid in the game."""

    quantity: int
    face_value: int  # 1-6, where 1 is ace

    def __str__(self):
        face_names = {
            1: "aces",
            2: "twos",
            3: "threes",
            4: "fours",
            5: "fives",
            6: "sixes",
        }
        return f"{self.quantity} {face_names[self.face_value]}"

    def is_higher_than(self, other: "Bid") -> bool:
        """Check if this bid is higher than another (Perudo rules)."""
        # Can increase quantity with ANY face value
        if self.quantity > other.quantity:
            return True
        # Can keep same quantity only with HIGHER face value
        if self.quantity == other.quantity and self.face_value > other.face_value:
            return True
        return False

    def is_joker_bid(self) -> bool:
        """Check if this is a bid on aces (joker bid)."""
        return self.face_value == 1


class Player:
    """Represents a player in the game."""

    def __init__(self, player_id: str, num_dice: int = 5):
        self.id = player_id
        self.dice: List[int] = []
        self.num_dice = num_dice
        self.is_active = True

    def roll_dice(self):
        """Roll all dice for this player."""
        self.dice = [random.randint(1, 6) for _ in range(self.num_dice)]

    def lose_die(self):
        """Remove one die from the player."""
        self.num_dice -= 1
        if self.num_dice <= 0:
            self.is_active = False
            self.dice = []

    def __str__(self):
        return f"Player {self.id} ({self.num_dice} dice)"


class GameState:
    """Manages the complete state of a Liar's Dice game."""

    def __init__(
        self, player_ids: List[str], starting_dice: int = 5, joker_mode: bool = True
    ):
        """
        Initialize game state.

        Args:
            player_ids: List of player identifiers
            starting_dice: Number of dice each player starts with
            joker_mode: Whether aces are wild (count as any value)
        """
        self.players = {pid: Player(pid, starting_dice) for pid in player_ids}
        self.player_order = player_ids.copy()
        self.current_player_idx = 0
        self.current_bid: Optional[Bid] = None
        self.bid_history: List[Tuple[str, Bid]] = []
        self.joker_mode = joker_mode
        self.round_number = 1
        self.last_loser: Optional[str] = None  # Player who lost the last challenge

    def start_new_round(self):
        """Start a new round by rolling all dice."""
        for player in self.players.values():
            if player.is_active:
                player.roll_dice()
        self.current_bid = None
        self.bid_history = []
        # Last loser starts the new round (or keep current order)
        if self.last_loser and self.last_loser in self.player_order:
            self.current_player_idx = self.player_order.index(self.last_loser)

    def get_current_player(self) -> Optional[Player]:
        """Get the current active player."""
        if not self.player_order:
            return None
        return self.players[self.player_order[self.current_player_idx]]

    def get_next_player(self) -> Optional[Player]:
        """Get the next active player in turn order."""
        if len(self.get_active_players()) <= 1:
            return None

        next_idx = (self.current_player_idx + 1) % len(self.player_order)
        # Skip inactive players
        while not self.players[self.player_order[next_idx]].is_active:
            next_idx = (next_idx + 1) % len(self.player_order)
        return self.players[self.player_order[next_idx]]

    def make_bid(self, player_id: str, bid: Bid) -> bool:
        """
        Make a bid for the specified player.

        Returns:
            True if bid is valid and accepted, False otherwise
        """
        if not self.is_valid_bid(bid):
            return False

        self.current_bid = bid
        self.bid_history.append((player_id, bid))
        self.advance_turn()
        return True

    def is_valid_bid(self, bid: Bid) -> bool:
        """Check if a bid is valid given the current state."""
        # First bid of the round is always valid (except for invalid values)
        if bid.quantity <= 0 or bid.face_value < 1 or bid.face_value > 6:
            return False

        if self.current_bid is None:
            return True

        # Check if it's a valid raise
        if bid.is_joker_bid() and not self.current_bid.is_joker_bid():
            # Switching to joker bid: quantity must be at least half (rounded up) of current
            min_quantity = (self.current_bid.quantity + 1) // 2
            return bid.quantity >= min_quantity
        elif not bid.is_joker_bid() and self.current_bid.is_joker_bid():
            # Switching from joker bid: quantity must be at least double + 1
            min_quantity = self.current_bid.quantity * 2 + 1
            return bid.quantity >= min_quantity
        else:
            # Normal raise: must be higher
            return bid.is_higher_than(self.current_bid)

    def challenge_current_bid(self, challenger_id: str) -> Tuple[bool, str, str]:
        """
        Challenge the current bid.

        Returns:
            (challenge_successful, winner_id, loser_id)
        """
        if self.current_bid is None:
            raise ValueError("No bid to challenge")

        # Count all dice
        all_dice = []
        for player in self.players.values():
            if player.is_active:
                all_dice.extend(player.dice)

        # Count matches (including jokers/aces if in joker mode)
        actual_count = self.count_matching_dice(all_dice, self.current_bid.face_value)

        # Determine winner/loser
        if actual_count >= self.current_bid.quantity:
            # Bid was valid, challenger loses
            winner_id = self.bid_history[-1][0]  # Last bidder
            loser_id = challenger_id
            challenge_successful = False
        else:
            # Bid was invalid, bidder loses
            winner_id = challenger_id
            loser_id = self.bid_history[-1][0]
            challenge_successful = True

        # Loser loses a die
        self.players[loser_id].lose_die()
        self.last_loser = loser_id

        # Remove eliminated players from turn order
        if not self.players[loser_id].is_active:
            self.player_order.remove(loser_id)
            # Adjust current player index if needed
            if self.current_player_idx >= len(self.player_order):
                self.current_player_idx = 0

        return challenge_successful, winner_id, loser_id

    def count_matching_dice(self, dice: List[int], face_value: int) -> int:
        """Count dice matching the face value (including jokers if applicable)."""
        count = dice.count(face_value)

        # In joker mode, aces (1s) count as any value (unless we're counting aces)
        if self.joker_mode and face_value != 1:
            count += dice.count(1)

        return count

    def advance_turn(self):
        """Move to the next player's turn."""
        if len(self.get_active_players()) <= 1:
            return

        self.current_player_idx = (self.current_player_idx + 1) % len(self.player_order)
        # Skip inactive players
        while not self.players[self.player_order[self.current_player_idx]].is_active:
            self.current_player_idx = (self.current_player_idx + 1) % len(
                self.player_order
            )

    def get_active_players(self) -> List[Player]:
        """Get list of active players."""
        return [p for p in self.players.values() if p.is_active]

    def get_total_dice(self) -> int:
        """Get total number of dice in play."""
        return sum(p.num_dice for p in self.players.values() if p.is_active)

    def is_game_over(self) -> bool:
        """Check if the game is over (only one player left)."""
        return len(self.get_active_players()) <= 1

    def get_winner(self) -> Optional[str]:
        """Get the winner if the game is over."""
        active_players = self.get_active_players()
        if len(active_players) == 1:
            return active_players[0].id
        return None

    def get_dice_distribution(self) -> Dict[int, int]:
        """Get the actual distribution of all dice in play."""
        all_dice = []
        for player in self.players.values():
            if player.is_active:
                all_dice.extend(player.dice)
        return dict(Counter(all_dice))
