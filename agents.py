"""
Agent implementations for Liar's Dice.
Uses probability calculations to make rational decisions.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
import random
from game_state import GameState, Bid, Player
from bayesian_playground import count_atleast_prob, count_exact_prob, next_valid_bids, safest_bids


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, player_id: str, verbose: bool = False):
        self.player_id = player_id
        self.verbose = verbose

    @abstractmethod
    def make_decision(self, game_state: GameState) -> Tuple[str, Optional[Bid]]:
        """
        Decide whether to bid or challenge.

        Returns:
            ('bid', Bid) to make a bid
            ('challenge', None) to challenge the current bid
        """
        pass

    def get_my_dice(self, game_state: GameState) -> List[int]:
        """Get this agent's dice."""
        return game_state.players[self.player_id].dice

    def calculate_bid_probability(self, bid: Bid, game_state: GameState) -> float:
        """
        Calculate the probability that a bid is valid given what we know.

        This uses our own dice and assumes unknown dice are random.
        """
        my_dice = self.get_my_dice(game_state)
        total_dice = game_state.get_total_dice()
        unknown_dice = total_dice - len(my_dice)

        # Count our matching dice
        my_matches = 0
        # During palifico, aces are NOT wild
        effective_joker_mode = game_state.joker_mode and not game_state.is_palifico_round

        for die in my_dice:
            if die == bid.face_value:
                my_matches += 1
            elif effective_joker_mode and die == 1 and bid.face_value != 1:
                my_matches += 1  # Aces count as jokers (except during palifico)

        # How many more matches do we need from unknown dice?
        needed_from_unknown = max(0, bid.quantity - my_matches)

        # Calculate probability of getting at least that many matches from unknown dice
        if unknown_dice == 0:
            return 1.0 if needed_from_unknown == 0 else 0.0

        # Probability of a single unknown die matching
        if effective_joker_mode and bid.face_value != 1:
            # Die matches if it's the target value OR an ace
            p_match = 2 / 6  # 1/6 for target + 1/6 for ace
        else:
            # Die matches only if it's the target value (or during palifico)
            p_match = 1 / 6

        return count_atleast_prob(needed_from_unknown, unknown_dice, p_match)


class ThresholdAgent(BaseAgent):
    """
    Agent that bids when probability is above a threshold.
    Challenges when current bid probability is below threshold.
    """

    def __init__(
        self,
        player_id: str,
        bid_threshold: float = 0.5,
        challenge_threshold: float = 0.3,
        calza_threshold: float = 0.15,
        verbose: bool = False,
        name: str = None,
    ):
        super().__init__(player_id, verbose)
        self.bid_threshold = bid_threshold
        self.challenge_threshold = challenge_threshold
        self.calza_threshold = calza_threshold  # Minimum probability for calling calza
        self.name = name or f"Threshold-{bid_threshold}"

    def make_decision(self, game_state: GameState) -> Tuple[str, Optional[Bid]]:
        """Decide whether to bid, challenge, or call calza based on probability thresholds."""

        # If there's no current bid, we must bid
        if game_state.current_bid is None:
            return self._make_opening_bid(game_state)

        # Calculate probability of current bid being valid
        current_bid_prob = self.calculate_bid_probability(
            game_state.current_bid, game_state
        )

        if self.verbose:
            print(
                f"{self.player_id} ({self.name}) sees bid {game_state.current_bid} with probability {current_bid_prob:.2%}"
            )

        # Consider calza before challenging or bidding
        calza_decision = self._consider_calza(game_state, current_bid_prob)
        if calza_decision:
            return calza_decision

        # Challenge if probability is too low
        if current_bid_prob < self.challenge_threshold:
            if self.verbose:
                print(
                    f"{self.player_id} ({self.name}) challenges! (prob {current_bid_prob:.2%} < threshold {self.challenge_threshold:.2%})"
                )
            return ("challenge", None)

        # Try to find a good bid to make
        bid = self._select_bid(game_state)
        if bid:
            return ("bid", bid)
        else:
            # Can't find a good bid, must challenge
            if self.verbose:
                print(
                    f"{self.player_id} ({self.name}) can't find good bid, challenges!"
                )
            return ("challenge", None)

    def _consider_calza(self, game_state: GameState, current_bid_prob: float) -> Optional[Tuple[str, None]]:
        """
        Consider calling calza (exact bid) if conditions are favorable.

        Returns:
            ('calza', None) if calza should be called, None otherwise
        """
        # Quick checks for calza eligibility
        if game_state.is_palifico_round:
            return None  # Calza not allowed during palifico
        if len(game_state.get_active_players()) <= 2:
            return None  # Calza not allowed with 2 or fewer players

        next_player = game_state.get_next_player()
        if next_player and self.player_id == next_player.id:
            return None  # Next player cannot call calza

        # Calculate exact probability
        my_dice = self.get_my_dice(game_state)
        total_dice = game_state.get_total_dice()
        unknown_dice = total_dice - len(my_dice)
        bid = game_state.current_bid

        # Count our matching dice
        my_matches = 0
        effective_joker_mode = game_state.joker_mode and not game_state.is_palifico_round

        for die in my_dice:
            if die == bid.face_value:
                my_matches += 1
            elif effective_joker_mode and die == 1 and bid.face_value != 1:
                my_matches += 1

        needed_from_unknown = max(0, bid.quantity - my_matches)

        # Probability of a single unknown die matching
        if effective_joker_mode and bid.face_value != 1:
            p_match = 2 / 6
        else:
            p_match = 1 / 6

        # Calculate exact probability
        if unknown_dice == 0:
            exact_prob = 1.0 if needed_from_unknown == 0 else 0.0
        else:
            exact_prob = count_exact_prob(needed_from_unknown, unknown_dice, p_match)

        # Calculate probability of at least N+1 (we want this to be low)
        if unknown_dice == 0:
            prob_more = 0.0
        else:
            prob_more = count_atleast_prob(needed_from_unknown + 1, unknown_dice, p_match)

        # Call calza if:
        # 1. Exact probability is high enough
        # 2. Probability of having more is low (ensures it's likely exactly N)
        # 3. Overall bid probability is reasonable (not too low)
        should_calza = (
            exact_prob >= self.calza_threshold
            and prob_more < 0.3  # Less than 30% chance of having more
            and current_bid_prob > 0.25  # Bid is at least somewhat plausible
        )

        if should_calza:
            if self.verbose:
                print(
                    f"{self.player_id} ({self.name}) calls CALZA! "
                    f"(exact prob: {exact_prob:.2%}, more prob: {prob_more:.2%})"
                )
            return ("calza", None)

        return None

    def _make_opening_bid(self, game_state: GameState) -> Tuple[str, Bid]:
        """Make the opening bid of a round."""
        my_dice = self.get_my_dice(game_state)
        total_dice = game_state.get_total_dice()

        # Count our dice frequencies
        dice_counts = {}
        for die in my_dice:
            dice_counts[die] = dice_counts.get(die, 0) + 1

        # During palifico, aces are NOT wild
        effective_joker_mode = game_state.joker_mode and not game_state.is_palifico_round

        # If we have aces and joker mode is on, they're valuable
        if effective_joker_mode and 1 in dice_counts:
            # Aces help with any bid
            joker_boost = dice_counts[1]
        else:
            joker_boost = 0

        # Find the face value we have most of (excluding aces initially)
        best_face = None
        best_count = 0
        for face in range(2, 7):  # 2-6
            count = dice_counts.get(face, 0) + joker_boost
            if count > best_count:
                best_count = count
                best_face = face

        # During palifico, only palifico player can bid on aces
        can_bid_aces = not game_state.is_palifico_round or (
            self.player_id == game_state.palifico_player_id
        )

        # If we have lots of aces, consider bidding aces (if allowed)
        if can_bid_aces and 1 in dice_counts and dice_counts[1] >= 2:
            best_face = 1
            best_count = dice_counts[1]

        # Make a conservative opening bid
        # Assume we might get 1/6 of unknown dice matching
        unknown_dice = total_dice - len(my_dice)
        expected_matches = best_count + (unknown_dice * 1 / 6)
        safe_quantity = max(1, int(expected_matches * 0.8))  # Be conservative

        opening_bid = Bid(safe_quantity, best_face)

        if self.verbose:
            palifico_note = " [PALIFICO]" if game_state.is_palifico_round else ""
            print(f"{self.player_id} ({self.name}) opens with {opening_bid}{palifico_note}")

        return ("bid", opening_bid)

    def _select_bid(self, game_state: GameState) -> Optional[Bid]:
        """Select a bid that meets our threshold."""
        my_dice = self.get_my_dice(game_state)
        total_dice = game_state.get_total_dice()

        # During palifico, effective joker mode is false
        effective_joker_mode = game_state.joker_mode and not game_state.is_palifico_round

        # Get all valid next bids
        valid_bids = next_valid_bids(
            (game_state.current_bid.quantity, game_state.current_bid.face_value),
            total_dice,
            effective_joker_mode,
        )

        # During palifico: filter bids to same face value only
        # Exception: if this player already had palifico, they can change face value
        if game_state.is_palifico_round:
            player_already_had_palifico = (
                self.player_id in game_state.players_who_had_palifico
                and self.player_id != game_state.palifico_player_id
            )

            if not player_already_had_palifico:
                # Can only raise quantity, same face value
                current_face = game_state.current_bid.face_value
                valid_bids = [
                    (q, f) for q, f in valid_bids if f == current_face
                ]

        # Calculate probability for each valid bid and filter by threshold
        acceptable_bids = []
        for quantity, face in valid_bids:
            bid = Bid(quantity, face)
            prob = self.calculate_bid_probability(bid, game_state)
            if prob >= self.bid_threshold:
                acceptable_bids.append((bid, prob))

        if not acceptable_bids:
            return None

        # Sort by probability (highest first) and take the safest
        acceptable_bids.sort(key=lambda x: x[1], reverse=True)

        # With some probability, take a riskier bid for variety
        if len(acceptable_bids) > 1 and random.random() < 0.2:
            # 20% of the time, take the second-best option
            selected_bid = acceptable_bids[1][0]
            selected_prob = acceptable_bids[1][1]
        else:
            selected_bid = acceptable_bids[0][0]
            selected_prob = acceptable_bids[0][1]

        # Safeguard: Verify the selected bid is actually valid
        if not game_state.is_valid_bid(selected_bid, self.player_id):
            if self.verbose:
                print(
                    f"WARNING: {self.player_id} generated invalid bid {selected_bid}!"
                )
            # Try to find any valid bid from our acceptable list
            for bid, prob in acceptable_bids:
                if game_state.is_valid_bid(bid, self.player_id):
                    selected_bid = bid
                    selected_prob = prob  # Update probability to match the new bid
                    break
            else:
                # No valid bids found at all - this should never happen
                print(
                    f"ERROR: No valid bids found for {self.player_id}!\n THIS SHOULD NEVER HAPPEN!"
                )
                return None

        if self.verbose:
            print(
                f"{self.player_id} ({self.name}) bids {selected_bid} (probability: {selected_prob:.2%})"
            )

        return selected_bid


class ConservativeAgent(ThresholdAgent):
    """Conservative agent - only bids on high probability outcomes."""

    def __init__(self, player_id: str, verbose: bool = False):
        super().__init__(
            player_id,
            bid_threshold=0.7,  # Only bid if 70%+ confident
            challenge_threshold=0.25,  # Challenge if bid seems <25% likely
            verbose=verbose,
            name="Conservative",
        )


class BalancedAgent(ThresholdAgent):
    """Balanced agent - moderate risk tolerance."""

    def __init__(self, player_id: str, verbose: bool = False):
        super().__init__(
            player_id,
            bid_threshold=0.5,  # Bid if 50%+ confident
            challenge_threshold=0.35,  # Challenge if bid seems <35% likely
            verbose=verbose,
            name="Balanced",
        )


class AggressiveAgent(ThresholdAgent):
    """Aggressive agent - willing to bluff and take risks."""

    def __init__(self, player_id: str, verbose: bool = False):
        super().__init__(
            player_id,
            bid_threshold=0.3,  # Bid even with 30% confidence (bluffing)
            challenge_threshold=0.2,  # Only challenge if very unlikely (<20%)
            verbose=verbose,
            name="Aggressive",
        )


class RandomAgent(BaseAgent):
    """Agent that makes random valid moves - useful for baseline comparison."""

    def __init__(self, player_id: str, verbose: bool = False):
        super().__init__(player_id, verbose)
        self.name = "Random"

    def make_decision(self, game_state: GameState) -> Tuple[str, Optional[Bid]]:
        """Randomly decide to bid or challenge."""

        # If no current bid, must bid
        if game_state.current_bid is None:
            return self._make_random_opening_bid(game_state)

        # 30% chance to challenge (if there's a bid to challenge)
        if random.random() < 0.3:
            if self.verbose:
                print(f"{self.player_id} ({self.name}) randomly challenges!")
            return ("challenge", None)

        # Try to make a random valid bid
        total_dice = game_state.get_total_dice()
        # During palifico, effective joker mode is false
        effective_joker_mode = game_state.joker_mode and not game_state.is_palifico_round

        valid_bids = next_valid_bids(
            (game_state.current_bid.quantity, game_state.current_bid.face_value),
            total_dice,
            effective_joker_mode,
        )

        # During palifico: filter to same face value only
        if game_state.is_palifico_round:
            player_already_had_palifico = (
                self.player_id in game_state.players_who_had_palifico
                and self.player_id != game_state.palifico_player_id
            )
            if not player_already_had_palifico:
                current_face = game_state.current_bid.face_value
                valid_bids = [(q, f) for q, f in valid_bids if f == current_face]

        if valid_bids:
            quantity, face = random.choice(valid_bids)
            bid = Bid(quantity, face)
            if self.verbose:
                print(f"{self.player_id} ({self.name}) randomly bids {bid}")
            return ("bid", bid)
        else:
            # No valid bids available, must challenge
            if self.verbose:
                print(
                    f"{self.player_id} ({self.name}) forced to challenge (no valid bids)"
                )
            return ("challenge", None)

    def _make_random_opening_bid(self, game_state: GameState) -> Tuple[str, Bid]:
        """Make a random opening bid."""
        total_dice = game_state.get_total_dice()
        # Random but reasonable opening bid
        quantity = random.randint(1, max(1, total_dice // 4))
        face = random.randint(1, 6)
        bid = Bid(quantity, face)

        if self.verbose:
            print(f"{self.player_id} ({self.name}) randomly opens with {bid}")

        return ("bid", bid)
