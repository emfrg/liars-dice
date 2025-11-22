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

    def gain_die(self):
        """Add one die to the player (max 5 dice total)."""
        if self.num_dice < 5:
            self.num_dice += 1
            # Reactivate player if they were inactive (edge case)
            if not self.is_active:
                self.is_active = True

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
        self.ace_quantities_bid: set = set()  # Track which ace quantities have been bid this round

        # Palifico round tracking (special round when player has 1 die)
        self.is_palifico_round: bool = False
        self.palifico_player_id: Optional[str] = None  # Player who triggered palifico
        self.players_who_had_palifico: set = set()  # Track one-time-per-player palifico

    def start_new_round(self):
        """Start a new round by rolling all dice."""
        for player in self.players.values():
            if player.is_active:
                player.roll_dice()
        self.current_bid = None
        self.bid_history = []
        self.ace_quantities_bid.clear()  # Reset ace quantities tracking for new round

        # Detect Palifico round (special round when player has exactly 1 die)
        self.is_palifico_round = False
        self.palifico_player_id = None

        active_players = self.get_active_players()

        # Palifico does NOT apply when only 2 players remain
        if len(active_players) > 2:
            # Check if any player has exactly 1 die and hasn't had palifico yet
            for player in active_players:
                if (
                    player.num_dice == 1
                    and player.id not in self.players_who_had_palifico
                ):
                    self.is_palifico_round = True
                    self.palifico_player_id = player.id
                    # Mark that this player has had their palifico round
                    self.players_who_had_palifico.add(player.id)
                    break  # Only one player triggers palifico per round

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
        if not self.is_valid_bid(bid, player_id):
            return False

        self.current_bid = bid
        self.bid_history.append((player_id, bid))

        # Track ace quantities bid this round
        if bid.is_joker_bid():
            self.ace_quantities_bid.add(bid.quantity)

        self.advance_turn()
        return True

    def is_valid_bid(self, bid: Bid, player_id: Optional[str] = None) -> bool:
        """Check if a bid is valid given the current state.

        Args:
            bid: The bid to validate
            player_id: The player making the bid (needed for palifico exception check)
        """
        # Basic validation
        if bid.quantity <= 0 or bid.face_value < 1 or bid.face_value > 6:
            return False

        # Palifico round special rules
        if self.is_palifico_round:
            # During palifico, aces can only be bid by the palifico player (first bid)
            if bid.is_joker_bid() and self.current_bid is None:
                # Only palifico player can open with aces
                if player_id != self.palifico_player_id:
                    return False

            # During palifico, face value must stay the same (only quantity increases)
            if self.current_bid is not None:
                # Exception: players who already had palifico can change face value
                player_already_had_palifico = (
                    player_id in self.players_who_had_palifico
                    and player_id != self.palifico_player_id
                )

                if not player_already_had_palifico:
                    # Face value must match current bid
                    if bid.face_value != self.current_bid.face_value:
                        return False
                    # Quantity must be higher
                    if bid.quantity <= self.current_bid.quantity:
                        return False
                # If player already had palifico, they can change face value
                # and normal bid rules apply (checked below)

        # Ace bidding restrictions (official Perudo rules) - not during palifico
        if bid.is_joker_bid() and not self.is_palifico_round:
            # Rule 1: Aces cannot be bid on the FIRST bid of the round
            if self.current_bid is None:
                return False
            # Rule 2: Each quantity of aces can only be bid ONCE per round
            if bid.quantity in self.ace_quantities_bid:
                return False

        # If this is the first bid of the round, it's valid (non-ace bids or palifico aces)
        if self.current_bid is None:
            return True

        # During palifico with exception player or normal rounds: check valid raise
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

    def calza(self, calling_player_id: str) -> Dict[str, any]:
        """
        Call calza (exact bid) on the current bid.

        Args:
            calling_player_id: Player calling calza

        Returns:
            Dictionary with calza results:
            {
                'valid': bool,
                'error': str (if invalid),
                'success': bool (if exact match),
                'actual_count': int,
                'winner_id': str,
                'loser_id': str,
                'dice_change': int (+1 or -1)
            }
        """
        # Validation checks
        if self.current_bid is None:
            return {'valid': False, 'error': 'No bid to call calza on'}

        # Calza not applicable during palifico
        if self.is_palifico_round:
            return {'valid': False, 'error': 'Calza not allowed during palifico round'}

        # Calza not applicable with only 2 players
        if len(self.get_active_players()) <= 2:
            return {'valid': False, 'error': 'Calza not allowed with 2 or fewer players'}

        # Caller cannot be the next player in turn
        next_player = self.get_next_player()
        if next_player and calling_player_id == next_player.id:
            return {'valid': False, 'error': 'Next player in turn cannot call calza'}

        # Count all dice
        all_dice = []
        for player in self.players.values():
            if player.is_active:
                all_dice.extend(player.dice)

        # Count exact matches
        actual_count = self.count_matching_dice(all_dice, self.current_bid.face_value)

        # Determine if calza was successful (exact match)
        calza_successful = (actual_count == self.current_bid.quantity)

        if calza_successful:
            # Caller was correct - gains a die
            winner_id = calling_player_id
            loser_id = self.bid_history[-1][0]  # Last bidder
            self.players[winner_id].gain_die()
            dice_change = +1
        else:
            # Caller was wrong - loses a die
            winner_id = self.bid_history[-1][0]  # Last bidder
            loser_id = calling_player_id
            self.players[loser_id].lose_die()
            dice_change = -1

        # Update game state
        self.last_loser = loser_id

        # Remove eliminated players from turn order
        if not self.players[loser_id].is_active:
            self.player_order.remove(loser_id)
            # Adjust current player index if needed
            if self.current_player_idx >= len(self.player_order):
                self.current_player_idx = 0

        return {
            'valid': True,
            'success': calza_successful,
            'actual_count': actual_count,
            'bid_quantity': self.current_bid.quantity,
            'winner_id': winner_id,
            'loser_id': loser_id,
            'dice_change': dice_change,
            'caller_gained_die': calza_successful
        }

    def count_matching_dice(
        self, dice: List[int], face_value: int, use_joker: Optional[bool] = None
    ) -> int:
        """Count dice matching the face value (including jokers if applicable).

        Args:
            dice: List of dice values to count
            face_value: The face value to count
            use_joker: Override joker mode for this count (used for palifico)
                      If None, uses self.joker_mode and self.is_palifico_round
        """
        count = dice.count(face_value)

        # Determine if jokers should be counted
        if use_joker is None:
            # During palifico, aces are NOT wild
            effective_joker_mode = self.joker_mode and not self.is_palifico_round
        else:
            effective_joker_mode = use_joker

        # In joker mode, aces (1s) count as any value (unless we're counting aces)
        if effective_joker_mode and face_value != 1:
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
