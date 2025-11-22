from agents import ConservativeAgent, BalancedAgent, AggressiveAgent
from game_state import GameState

from time import sleep

# Create agents
agents = {
    "Alice": ConservativeAgent("Alice", verbose=True),
    "Bob": BalancedAgent("Bob", verbose=True),
    "Charlie": AggressiveAgent("Charlie", verbose=True),
}

# Initialize game
player_ids = list(agents.keys())
game = GameState(player_ids, starting_dice=5, joker_mode=True)

# Play NUM_ROUNDS rounds (or until game ends)
NUM_ROUNDS = 5
for round_num in range(1, NUM_ROUNDS + 1):
    if game.is_game_over():
        print(f"\nGame ended early! Winner: {game.get_winner()}")
        break

    print(f"\n{'='*60}")
    print(f"ROUND {round_num}")
    print(f"{'='*60}")

    # Start round - roll dice
    game.start_new_round()

    # Show everyone's dice
    print("\nDice rolls:")
    for pid, player in game.players.items():
        if player.is_active:
            print(f"  {pid}: {sorted(player.dice)} ({player.num_dice} dice)")

    # Play until someone challenges
    turn = 0
    while turn < 20:  # Max turns per round. TODO: question
        current_player = game.get_current_player()
        if not current_player:
            break

        agent = agents[current_player.id]
        action, bid = agent.make_decision(game)

        if action == "bid":
            if game.make_bid(current_player.id, bid):
                print(f"\n{current_player.id} bids: {bid}")
            else:
                # This should never happen after our fixes
                raise RuntimeError(
                    f"CRITICAL ERROR: {current_player.id} attempted invalid bid {bid}! "
                    f"Current bid: {game.current_bid}. This should never occur."
                )

        elif action == "calza":
            caller = current_player.id
            bidder = game.bid_history[-1][0] if game.bid_history else "Unknown"

            print(f"\n{caller} calls CALZA on {bidder}'s bid!")
            print(f"The bid was: {game.current_bid}")

            # Show actual count
            dist = game.get_dice_distribution()
            target = game.current_bid.face_value
            actual = dist.get(target, 0)
            # During palifico, aces are NOT wild
            effective_joker = game.joker_mode and not game.is_palifico_round
            if effective_joker and target != 1:
                actual += dist.get(1, 0)
            print(f"Actual count: {actual}")

            # Resolve calza
            result = game.calza(caller)
            if not result['valid']:
                print(f"CALZA INVALID: {result['error']}")
                # Force challenge instead
                print(f"\n{caller} CHALLENGES {bidder} instead!")
                success, winner, loser = game.challenge_current_bid(caller)
                print(
                    f"Challenge {'SUCCESSFUL' if success else 'FAILED'}! {loser} loses a die."
                )
                print(f"{loser} now has {game.players[loser].num_dice} dice")
            else:
                if result['success']:
                    print(f"CALZA SUCCESSFUL! Exactly {actual} dice!")
                    print(f"{result['winner_id']} GAINS a die! (now has {game.players[result['winner_id']].num_dice} dice)")
                else:
                    print(f"CALZA FAILED! (bid was {result['bid_quantity']}, actual was {actual})")
                    print(f"{result['loser_id']} LOSES a die! (now has {game.players[result['loser_id']].num_dice} dice)")
            break

        elif action == "challenge":
            challenger = current_player.id
            challenged = game.bid_history[-1][0]

            print(f"\n{challenger} CHALLENGES {challenged}!")
            print(f"The bid was: {game.current_bid}")

            # Show actual count
            dist = game.get_dice_distribution()
            target = game.current_bid.face_value
            actual = dist.get(target, 0)
            if game.joker_mode and target != 1:
                actual += dist.get(1, 0)
            print(f"Actual count: {actual}")

            # Resolve
            success, winner, loser = game.challenge_current_bid(challenger)
            print(
                f"Challenge {'SUCCESSFUL' if success else 'FAILED'}! {loser} loses a die."
            )
            print(f"{loser} now has {game.players[loser].num_dice} dice")
            break

        turn += 1

    print(f"\nEnd of round {round_num}")
    print(f"Active players: {[p.id for p in game.get_active_players()]}")

    sleep(5)

print(f"\n{'='*60}")
print("5 ROUNDS COMPLETE (or game ended)")
print(f"{'='*60}")
