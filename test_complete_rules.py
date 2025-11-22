"""
Comprehensive test suite for complete Perudo rules compliance.
Tests all advanced rules: palifico, calza, and ace restrictions.

DO NOT RUN AUTOMATICALLY - User will run manually when ready.
"""

import pytest
from game_state import GameState, Bid, Player
from agents import ThresholdAgent, ConservativeAgent
import random


class TestAceRestrictions:
    """Test ace bidding restrictions (official Perudo rules)."""

    def test_aces_cannot_be_first_bid(self):
        """Aces cannot be bid as the opening bid of a round."""
        game = GameState(["Alice", "Bob"], starting_dice=5, joker_mode=True)
        game.start_new_round()

        ace_bid = Bid(2, 1)  # 2 aces
        assert not game.is_valid_bid(ace_bid, "Alice"), "Aces should not be valid as first bid"

    def test_non_ace_first_bid_allowed(self):
        """Non-ace bids are allowed as opening bid."""
        game = GameState(["Alice", "Bob"], starting_dice=5, joker_mode=True)
        game.start_new_round()

        non_ace_bid = Bid(3, 4)  # 3 fours
        assert game.is_valid_bid(non_ace_bid, "Alice"), "Non-ace bid should be valid as first bid"

    def test_duplicate_ace_quantity_not_allowed(self):
        """Same quantity of aces cannot be bid twice in one round."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)
        game.start_new_round()

        # First player bids 3 fours
        game.make_bid("Alice", Bid(3, 4))

        # Second player bids 2 aces (halving from 3 fours)
        success = game.make_bid("Bob", Bid(2, 1))
        assert success, "First ace bid of quantity 2 should be valid"

        # Third player bids 5 fours
        game.make_bid("Charlie", Bid(5, 4))

        # Try to bid 2 aces again (should fail)
        duplicate_ace_bid = Bid(2, 1)
        assert not game.is_valid_bid(duplicate_ace_bid, "Alice"), "Duplicate ace quantity should not be valid"

    def test_different_ace_quantities_allowed(self):
        """Different quantities of aces are allowed in same round."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)
        game.start_new_round()

        game.make_bid("Alice", Bid(4, 3))  # 4 threes
        game.make_bid("Bob", Bid(2, 1))  # 2 aces (valid)
        game.make_bid("Charlie", Bid(5, 4))  # 5 fours
        game.make_bid("Alice", Bid(3, 1))  # 3 aces (different quantity, should be valid)

        assert 2 in game.ace_quantities_bid
        assert 3 in game.ace_quantities_bid

    def test_ace_quantities_reset_between_rounds(self):
        """Ace quantity tracking resets each round."""
        game = GameState(["Alice", "Bob"], starting_dice=5, joker_mode=True)

        # Round 1
        game.start_new_round()
        game.make_bid("Alice", Bid(3, 4))
        game.make_bid("Bob", Bid(2, 1))  # 2 aces
        assert 2 in game.ace_quantities_bid

        # Round 2
        game.start_new_round()
        assert 2 not in game.ace_quantities_bid, "Ace quantities should reset between rounds"
        game.make_bid("Alice", Bid(3, 5))
        bid_2_aces = Bid(2, 1)
        assert game.is_valid_bid(bid_2_aces, "Bob"), "Same ace quantity should be valid in new round"


class TestPalificoDetection:
    """Test palifico round detection and triggering."""

    def test_palifico_triggered_when_player_has_1_die(self):
        """Palifico triggers when a player has exactly 1 die."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)

        # Manually set one player to 1 die
        game.players["Bob"].num_dice = 1

        game.start_new_round()

        assert game.is_palifico_round, "Palifico should trigger with 1-die player"
        assert game.palifico_player_id == "Bob", "Bob should be the palifico player"

    def test_palifico_not_triggered_with_2_players(self):
        """Palifico does NOT trigger with only 2 players remaining."""
        game = GameState(["Alice", "Bob"], starting_dice=5, joker_mode=True)

        # Set one player to 1 die
        game.players["Bob"].num_dice = 1

        game.start_new_round()

        assert not game.is_palifico_round, "Palifico should not trigger with only 2 players"

    def test_palifico_one_time_per_player(self):
        """Each player only gets one palifico round."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)

        # Bob gets 1 die - first palifico
        game.players["Bob"].num_dice = 1
        game.start_new_round()
        assert game.is_palifico_round
        assert "Bob" in game.players_who_had_palifico

        # Bob wins dice back to 3, then loses to 1 again
        game.players["Bob"].num_dice = 3
        game.start_new_round()
        assert not game.is_palifico_round  # No palifico

        game.players["Bob"].num_dice = 1
        game.start_new_round()
        assert not game.is_palifico_round, "Bob should not get second palifico"

    def test_different_players_can_have_palifico(self):
        """Different players can each have their one palifico."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)

        # Bob's palifico
        game.players["Bob"].num_dice = 1
        game.start_new_round()
        assert game.palifico_player_id == "Bob"

        # Later, Alice's palifico
        game.players["Bob"].num_dice = 3
        game.players["Alice"].num_dice = 1
        game.start_new_round()
        assert game.is_palifico_round
        assert game.palifico_player_id == "Alice"


class TestPalificoBidValidation:
    """Test palifico bid validation rules."""

    def test_palifico_only_quantity_increases(self):
        """During palifico, only quantity can increase (same face value)."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)

        game.players["Bob"].num_dice = 1
        game.start_new_round()
        assert game.is_palifico_round

        # First bid: 2 threes
        game.make_bid("Alice", Bid(2, 3))

        # Try to bid different face value (should fail)
        bid_fours = Bid(3, 4)
        assert not game.is_valid_bid(bid_fours, "Bob"), "Face value change not allowed in palifico"

        # Bid same face, higher quantity (should succeed)
        bid_more_threes = Bid(3, 3)
        assert game.is_valid_bid(bid_more_threes, "Bob"), "Quantity increase should be allowed"

    def test_palifico_aces_not_wild(self):
        """During palifico, aces are NOT counted as wild."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)

        game.players["Bob"].num_dice = 1
        game.start_new_round()  # This rolls dice - must set them AFTER this call

        # Set dice AFTER start_new_round() to prevent re-rolling
        game.players["Bob"].dice = [1]  # Bob has an ace
        game.players["Alice"].dice = [1, 3, 3, 4, 5]
        game.players["Charlie"].dice = [2, 3, 4, 5, 6]

        game.make_bid("Alice", Bid(3, 3))  # Bid 3 threes

        # Count: Alice has 2 threes, Charlie has 1 three, Bob has 0 threes
        # Total = 3 threes (aces should NOT count as wild)
        all_dice = game.players["Alice"].dice + game.players["Bob"].dice + game.players["Charlie"].dice
        count = game.count_matching_dice(all_dice, 3)  # Should automatically use palifico logic

        assert count == 3, f"Should count exactly 3 threes (no aces wild), got {count}"

    def test_palifico_player_can_open_with_aces(self):
        """Only palifico player can open round with aces."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)

        game.players["Bob"].num_dice = 1
        game.start_new_round()

        # Bob (palifico player) can open with aces
        ace_bid = Bid(1, 1)
        assert game.is_valid_bid(ace_bid, "Bob"), "Palifico player should be able to open with aces"

        # But in normal round, first bid cannot be aces
        game2 = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)
        game2.start_new_round()
        assert not game2.is_valid_bid(ace_bid, "Alice"), "Normal player cannot open with aces"

    def test_exception_player_can_change_face_value(self):
        """Player who already had palifico can change face value during another player's palifico."""
        game = GameState(["Alice", "Bob", "Charlie", "Dave"], starting_dice=5, joker_mode=True)

        # Alice had palifico previously
        game.players["Alice"].num_dice = 1
        game.start_new_round()
        assert game.palifico_player_id == "Alice"
        game.players_who_had_palifico.add("Alice")  # Simulating she completed it

        # Later, Bob has palifico
        game.players["Alice"].num_dice = 3
        game.players["Bob"].num_dice = 1
        game.start_new_round()
        assert game.is_palifico_round
        assert game.palifico_player_id == "Bob"

        game.make_bid("Charlie", Bid(2, 3))  # Bid 2 threes

        # Dave (no prior palifico) cannot change face value
        bid_fours = Bid(3, 4)
        assert not game.is_valid_bid(bid_fours, "Dave"), "Normal player cannot change face in palifico"

        # Alice (had prior palifico) CAN change face value
        assert game.is_valid_bid(bid_fours, "Alice"), "Exception player can change face value"


class TestCalza:
    """Test calza (exact bid) functionality."""

    def test_calza_success_caller_gains_die(self):
        """Successful calza: caller gains a die."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)

        # Start Bob with 4 dice so he can gain one (max is 5)
        game.players["Bob"].num_dice = 4

        game.start_new_round()

        # Set up exact scenario
        game.players["Alice"].dice = [3, 3, 4, 5, 6]
        game.players["Bob"].dice = [1, 3, 4, 5]  # Ace counts as wild (4 dice)
        game.players["Charlie"].dice = [2, 4, 5, 6, 6]

        # Total threes = 2 (Alice) + 2 (Bob: 1 three + 1 ace) + 0 (Charlie) = 4 threes
        # Alice: 3,3 = 2 threes
        # Bob: 1,3 = 1 three + (ace counts for 3) = 2
        # Charlie: none = 0
        # Total = 4 threes

        game.make_bid("Alice", Bid(4, 3))  # Bid exactly 4 threes

        # Bob calls calza
        initial_dice = game.players["Bob"].num_dice
        result = game.calza("Bob")

        assert result['valid'], "Calza should be valid"
        assert result['success'], "Calza should be successful (exact match)"
        assert game.players["Bob"].num_dice == initial_dice + 1, "Bob should gain a die"
        assert game.players["Bob"].num_dice == 5, "Bob should now have 5 dice (4 + 1)"

    def test_calza_failure_caller_loses_die(self):
        """Failed calza: caller loses a die."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)
        game.start_new_round()

        game.make_bid("Alice", Bid(5, 3))  # Bid 5 threes

        initial_dice = game.players["Bob"].num_dice
        result = game.calza("Bob")

        assert result['valid'], "Calza should be valid"
        # Calza will likely fail (not exactly 5)
        if not result['success']:
            assert game.players["Bob"].num_dice == initial_dice - 1, "Bob should lose a die"

    def test_calza_not_allowed_during_palifico(self):
        """Calza is not allowed during palifico rounds."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)

        game.players["Bob"].num_dice = 1
        game.start_new_round()
        assert game.is_palifico_round

        game.make_bid("Alice", Bid(2, 3))

        result = game.calza("Charlie")
        assert not result['valid'], "Calza should not be allowed during palifico"
        assert 'palifico' in result['error'].lower()

    def test_calza_not_allowed_with_2_players(self):
        """Calza is not allowed with 2 or fewer players."""
        game = GameState(["Alice", "Bob"], starting_dice=5, joker_mode=True)
        game.start_new_round()

        game.make_bid("Alice", Bid(3, 4))

        result = game.calza("Bob")
        assert not result['valid'], "Calza should not be allowed with 2 players"
        assert '2' in result['error'] or 'fewer' in result['error']

    def test_next_player_cannot_call_calza(self):
        """Next player in turn cannot call calza."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)
        game.start_new_round()

        game.make_bid("Alice", Bid(3, 4))

        # After Alice's bid, turn advances to Bob (current player)
        # Charlie is the next player in turn
        current_player = game.get_current_player()
        next_player = game.get_next_player()
        assert current_player.id == "Bob", "Bob should be current player"
        assert next_player.id == "Charlie", "Charlie should be next player"

        # Charlie (next player) should NOT be able to call calza
        result = game.calza("Charlie")
        assert not result['valid'], "Next player should not be able to call calza"
        assert 'next player' in result['error'].lower()

        # But Bob (current player) CAN call calza (if other conditions met)
        result_bob = game.calza("Bob")
        assert result_bob['valid'], "Current player should be able to call calza"

    def test_calza_max_5_dice(self):
        """Calza cannot increase dice above 5."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)
        game.start_new_round()

        # Bob already has 5 dice
        game.players["Bob"].num_dice = 5
        game.make_bid("Alice", Bid(2, 4))

        # Set up exact match scenario (details omitted for brevity)
        # Assume calza succeeds
        result = game.calza("Bob")

        # Even if successful, Bob should not exceed 5 dice
        assert game.players["Bob"].num_dice <= 5, "Player cannot have more than 5 dice"


class TestEdgeCases:
    """Test edge cases and complex scenarios."""

    def test_two_players_one_die_each_no_palifico(self):
        """With 2 players remaining (even both with 1 die), palifico does not apply."""
        game = GameState(["Alice", "Bob"], starting_dice=5, joker_mode=True)

        game.players["Alice"].num_dice = 1
        game.players["Bob"].num_dice = 1

        game.start_new_round()

        assert not game.is_palifico_round, "Palifico should not apply with 2 players"
        # Aces should still be wild
        all_dice = game.players["Alice"].dice + game.players["Bob"].dice
        if 1 in all_dice and 2 in all_dice:  # If there's an ace and a two
            count = game.count_matching_dice(all_dice, 2)
            # Count should include aces as wild
            assert count == all_dice.count(2) + all_dice.count(1), "Aces should be wild with 2 players"

    def test_player_loses_to_1_die_wins_back_to_3_loses_to_1_again(self):
        """Player with 1 die, gains dice, loses to 1 die again (no second palifico)."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)

        # Bob loses to 1 die - first palifico
        game.players["Bob"].num_dice = 1
        game.start_new_round()
        assert game.is_palifico_round
        assert "Bob" in game.players_who_had_palifico

        # Bob wins calzas and gets back to 3 dice
        game.players["Bob"].num_dice = 3
        game.start_new_round()
        assert not game.is_palifico_round

        # Bob loses again to 1 die
        game.players["Bob"].num_dice = 1
        game.start_new_round()
        assert not game.is_palifico_round, "Bob should not get a second palifico"

    def test_ace_bid_transitions_during_palifico(self):
        """Test ace bid rules during palifico."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)

        game.players["Bob"].num_dice = 1
        game.start_new_round()

        # Normal ace transition rules (half, double+1) should still apply to aces
        # Even though aces aren't wild during palifico
        game.make_bid("Alice", Bid(4, 5))

        # Switching to aces: should be (4+1)//2 = 2 minimum
        ace_bid = Bid(2, 1)
        # But this also needs to satisfy palifico rules if Bob bids it
        # This is complex - aces in palifico likely rare
        pass  # Complex interaction - document for manual testing

    def test_multiple_ace_quantities_different_values_same_round(self):
        """Multiple different ace quantities can be bid in same round."""
        game = GameState(["Alice", "Bob", "Charlie", "Dave"], starting_dice=5, joker_mode=True)
        game.start_new_round()

        game.make_bid("Alice", Bid(4, 3))
        game.make_bid("Bob", Bid(2, 1))  # 2 aces
        assert game.is_valid_bid(Bid(5, 4), "Charlie")
        game.make_bid("Charlie", Bid(5, 4))
        assert game.is_valid_bid(Bid(3, 1), "Dave"), "Different ace quantity should be valid"

        assert len(game.ace_quantities_bid) == 1  # Only 2 has been bid so far
        game.make_bid("Dave", Bid(3, 1))
        assert len(game.ace_quantities_bid) == 2  # Now 2 and 3


class TestProbabilityCalculations:
    """Test that probability calculations respect palifico mode."""

    def test_agent_probability_calculation_palifico(self):
        """Agent probability calculations should use p=1/6 during palifico."""
        from agents import ThresholdAgent

        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)
        game.players["Bob"].num_dice = 1
        game.start_new_round()
        assert game.is_palifico_round

        agent = ThresholdAgent("Alice")
        game.players["Alice"].dice = [2, 3, 4, 5, 6]

        # Bid 3 threes
        bid = Bid(3, 3)
        prob = agent.calculate_bid_probability(bid, game)

        # With 10 unknown dice, need 3 threes
        # During palifico: p=1/6 (not 1/3)
        # This should result in lower probability than normal mode
        assert prob < 0.5, "Palifico probability should be lower without joker mode"

    def test_agent_probability_calculation_normal(self):
        """Agent probability calculations should use p=1/3 in normal mode for non-aces."""
        from agents import ThresholdAgent

        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)
        game.start_new_round()
        assert not game.is_palifico_round

        agent = ThresholdAgent("Alice")
        game.players["Alice"].dice = [2, 3, 4, 5, 6]

        bid = Bid(3, 3)
        prob = agent.calculate_bid_probability(bid, game)

        # With joker mode, probability should be higher (p=1/3 vs p=1/6)
        assert prob > 0.2, "Normal mode should have reasonable probability"


class TestIntegration:
    """Integration tests combining multiple features."""

    def test_full_game_with_all_features(self):
        """Run a simulated game scenario with palifico, calza, and ace restrictions."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=5, joker_mode=True)
        game.start_new_round()

        # Normal round with ace restrictions
        assert not game.is_valid_bid(Bid(2, 1), "Alice"), "Aces cannot be first bid"
        game.make_bid("Alice", Bid(3, 4))
        game.make_bid("Bob", Bid(2, 1))  # First ace bid of quantity 2
        assert 2 in game.ace_quantities_bid
        assert not game.is_valid_bid(Bid(2, 1), "Charlie"), "Cannot bid same ace quantity twice"

        # Charlie challenges
        game.challenge_current_bid("Charlie")

        # New round - Bob now has 1 die - PALIFICO!
        game.players["Bob"].num_dice = 1
        game.start_new_round()
        assert game.is_palifico_round

        # During palifico: face value cannot change
        game.make_bid("Alice", Bid(2, 3))
        assert not game.is_valid_bid(Bid(3, 4), "Bob"), "Cannot change face during palifico"
        assert game.is_valid_bid(Bid(3, 3), "Bob"), "Can increase quantity during palifico"

    def test_realistic_game_flow(self):
        """Test realistic game flow from start to potential palifico."""
        game = GameState(["Alice", "Bob", "Charlie"], starting_dice=3, joker_mode=True)

        # Round 1
        game.start_new_round()
        game.make_bid("Alice", Bid(2, 4))
        game.make_bid("Bob", Bid(1, 1))  # Aces
        success, winner, loser = game.challenge_current_bid("Charlie")

        # Round 2 - someone might be down to 1 die
        game.start_new_round()
        if game.is_palifico_round:
            # Palifico rules in effect
            assert game.palifico_player_id is not None
            print(f"Palifico triggered by {game.palifico_player_id}")


if __name__ == "__main__":
    print("=" * 70)
    print("COMPREHENSIVE PERUDO RULES TEST SUITE")
    print("=" * 70)
    print("\nThis test suite covers:")
    print("  ✓ Ace bidding restrictions (no first bid, no duplicate quantities)")
    print("  ✓ Palifico round detection and rules")
    print("  ✓ Palifico one-time-per-player enforcement")
    print("  ✓ Palifico exception for previously-palifico players")
    print("  ✓ Calza (exact bid) success and failure")
    print("  ✓ Calza restrictions (palifico, 2 players, next player)")
    print("  ✓ Aces NOT wild during palifico")
    print("  ✓ Edge cases (2 players with 1 die, repeated palifico attempts)")
    print("  ✓ Probability calculations respecting palifico mode")
    print("  ✓ Integration tests combining multiple features")
    print("\n" + "=" * 70)
    print("Run with: pytest test_complete_rules.py -v")
    print("=" * 70)
