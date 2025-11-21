"""
Entry point for running Liar's Dice simulations and experiments.
Compares different agent strategies and analyzes results.
"""

import random
from simulator import GameSimulator, TournamentRunner
from agents import ConservativeAgent, BalancedAgent, AggressiveAgent, RandomAgent, ThresholdAgent


def run_single_verbose_game():
    """Run a single game with verbose output to see the gameplay."""
    print("\n" + "="*80)
    print("SINGLE GAME DEMONSTRATION")
    print("="*80)

    # Create agents
    agents = [
        ConservativeAgent("Alice", verbose=True),
        BalancedAgent("Bob", verbose=True),
        AggressiveAgent("Charlie", verbose=True)
    ]

    # Run game
    simulator = GameSimulator(agents, verbose=True, starting_dice=5, joker_mode=True)
    winner, stats = simulator.run_game()

    print("\nGame Statistics:")
    print(f"  Winner: {winner}")
    print(f"  Total rounds: {stats['rounds']}")
    print(f"  Total bids made: {stats['total_bids']}")
    print(f"  Successful challenges: {stats['successful_challenges']}")
    print(f"  Failed challenges: {stats['failed_challenges']}")


def run_strategy_comparison_tournament():
    """Compare different strategies in a tournament."""
    print("\n" + "="*80)
    print("STRATEGY COMPARISON TOURNAMENT")
    print("="*80)

    # Run multiple configurations
    configurations = [
        {
            'name': '3-Player Games (Conservative vs Balanced vs Aggressive)',
            'agents': [
                ConservativeAgent("Player1"),
                BalancedAgent("Player2"),
                AggressiveAgent("Player3")
            ],
            'num_games': 100
        },
        {
            'name': '4-Player Games (All Strategies)',
            'agents': [
                ConservativeAgent("Player1"),
                BalancedAgent("Player2"),
                AggressiveAgent("Player3"),
                RandomAgent("Player4")
            ],
            'num_games': 100
        },
        {
            'name': '2-Player Duel (Conservative vs Aggressive)',
            'agents': [
                ConservativeAgent("Player1"),
                AggressiveAgent("Player2")
            ],
            'num_games': 100
        }
    ]

    for config in configurations:
        print(f"\n{config['name']}")
        print("-" * len(config['name']))

        runner = TournamentRunner(verbose_games=False)
        results = runner.run_tournament(
            config['agents'],
            num_games=config['num_games'],
            starting_dice=5,
            joker_mode=True
        )
        runner.print_tournament_results(results)


def run_threshold_exploration():
    """Explore how different probability thresholds affect performance."""
    print("\n" + "="*80)
    print("THRESHOLD EXPLORATION")
    print("="*80)
    print("Testing different probability thresholds...")

    thresholds_to_test = [
        (0.8, 0.2, "Ultra-Conservative"),  # Very high bid threshold, low challenge threshold
        (0.7, 0.25, "Conservative"),
        (0.6, 0.3, "Moderately Conservative"),
        (0.5, 0.35, "Balanced"),
        (0.4, 0.35, "Moderately Aggressive"),
        (0.3, 0.2, "Aggressive"),
        (0.2, 0.15, "Ultra-Aggressive"),  # Very low thresholds - lots of bluffing
    ]

    results_by_threshold = {}

    for bid_thresh, challenge_thresh, name in thresholds_to_test:
        print(f"\nTesting {name} (bid>{bid_thresh:.0%}, challenge<{challenge_thresh:.0%})...")

        agents = [
            ThresholdAgent(f"Agent_{name}", bid_thresh, challenge_thresh, name=name),
            BalancedAgent("Opponent1"),  # Fixed opponents for comparison
            BalancedAgent("Opponent2"),
        ]

        runner = TournamentRunner(verbose_games=False)
        results = runner.run_tournament(agents, num_games=50, starting_dice=5, joker_mode=True)

        # Store results
        results_by_threshold[name] = results.get('ThresholdAgent', {})

    # Print comparison
    print("\n" + "="*60)
    print("THRESHOLD COMPARISON RESULTS")
    print("="*60)
    print(f"\n{'Strategy':<25} {'Win Rate':<12} {'Avg Bids':<12} {'Avg Challenges':<15}")
    print("-"*70)

    # Sort by win rate
    sorted_results = sorted(
        results_by_threshold.items(),
        key=lambda x: x[1].get('win_rate', 0),
        reverse=True
    )

    for name, stats in sorted_results:
        if stats:
            win_rate = f"{stats['win_rate']:.1%}"
            avg_bids = f"{stats['avg_bids_per_game']:.1f}"
            avg_challenges = f"{stats['avg_challenges_per_game']:.1f}"
            print(f"{name:<25} {win_rate:<12} {avg_bids:<12} {avg_challenges:<15}")


def run_game_size_analysis():
    """Analyze how the number of players affects strategy effectiveness."""
    print("\n" + "="*80)
    print("GAME SIZE ANALYSIS")
    print("="*80)
    print("Testing how strategy performs with different numbers of players...")

    for num_players in [2, 3, 4, 5, 6]:
        print(f"\n{num_players}-Player Games:")
        print("-" * 20)

        # Create a mix of agents
        agents = []
        strategies = [ConservativeAgent, BalancedAgent, AggressiveAgent]
        for i in range(num_players):
            strategy_class = strategies[i % len(strategies)]
            agents.append(strategy_class(f"Player{i+1}"))

        runner = TournamentRunner(verbose_games=False)
        results = runner.run_tournament(agents, num_games=50, starting_dice=5, joker_mode=True)

        # Print condensed results
        for agent_type, stats in sorted(results.items(), key=lambda x: x[1]['win_rate'], reverse=True):
            print(f"  {agent_type:<20} Win Rate: {stats['win_rate']:.1%}")


def main():
    """Main entry point."""
    print("\n" + "="*80)
    print("LIAR'S DICE SIMULATION FRAMEWORK")
    print("="*80)

    # Set random seed for reproducibility
    random.seed(42)

    # Menu of experiments
    while True:
        print("\nAvailable Experiments:")
        print("1. Watch a single verbose game")
        print("2. Run strategy comparison tournament")
        print("3. Explore probability thresholds")
        print("4. Analyze effect of game size")
        print("5. Run all experiments")
        print("0. Exit")

        choice = input("\nSelect experiment (0-5): ").strip()

        if choice == "1":
            run_single_verbose_game()
        elif choice == "2":
            run_strategy_comparison_tournament()
        elif choice == "3":
            run_threshold_exploration()
        elif choice == "4":
            run_game_size_analysis()
        elif choice == "5":
            print("\nRunning all experiments...")
            run_single_verbose_game()
            run_strategy_comparison_tournament()
            run_threshold_exploration()
            run_game_size_analysis()
            print("\n" + "="*80)
            print("ALL EXPERIMENTS COMPLETE")
            print("="*80)
        elif choice == "0":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please select 0-5.")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()