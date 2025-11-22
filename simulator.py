"""
Game simulator for running Liar's Dice games and tournaments.
Handles game flow, agent interactions, and statistics collection.
"""

from typing import List, Dict, Tuple, Optional
from collections import defaultdict
import random
from game_state import GameState, Bid
from agents import BaseAgent
import time


class GameSimulator:
    """Runs individual games and collects statistics."""

    def __init__(self, agents: List[BaseAgent], verbose: bool = False,
                 starting_dice: int = 5, joker_mode: bool = True):
        """
        Initialize the simulator.

        Args:
            agents: List of agents to play the game
            verbose: Whether to print game progress
            starting_dice: Number of dice each player starts with
            joker_mode: Whether aces are wild
        """
        self.agents = {agent.player_id: agent for agent in agents}
        self.verbose = verbose
        self.starting_dice = starting_dice
        self.joker_mode = joker_mode
        self.game_stats = {
            'rounds': 0,
            'total_bids': 0,
            'successful_challenges': 0,
            'failed_challenges': 0,
            'successful_calzas': 0,
            'failed_calzas': 0,
            'bids_by_player': defaultdict(int),
            'challenges_by_player': defaultdict(int),
            'calzas_by_player': defaultdict(int),
            'dice_lost_by_player': defaultdict(int),
            'dice_gained_by_player': defaultdict(int)
        }

    def run_game(self) -> Tuple[str, Dict]:
        """
        Run a complete game.

        Returns:
            (winner_id, game_statistics)
        """
        # Initialize game state
        player_ids = list(self.agents.keys())
        game_state = GameState(player_ids, self.starting_dice, self.joker_mode)

        if self.verbose:
            print("\n" + "="*60)
            print("STARTING NEW GAME")
            print(f"Players: {', '.join(player_ids)}")
            print(f"Starting dice: {self.starting_dice} per player")
            print(f"Joker mode: {'ON' if self.joker_mode else 'OFF'}")
            print("="*60)

        # Play rounds until someone wins
        while not game_state.is_game_over():
            self._play_round(game_state)
            self.game_stats['rounds'] += 1

        winner = game_state.get_winner()

        if self.verbose:
            print("\n" + "="*60)
            print(f"GAME OVER! Winner: {winner}")
            print(f"Total rounds played: {self.game_stats['rounds']}")
            print("="*60)

        return winner, self.game_stats

    def _play_round(self, game_state: GameState):
        """Play a single round of the game."""
        game_state.start_new_round()

        if self.verbose:
            print(f"\n--- Round {game_state.round_number} ---")
            # Display palifico notification
            if game_state.is_palifico_round:
                print(f"*** PALIFICO ROUND *** (Player {game_state.palifico_player_id} has 1 die)")
                print("    Aces are NOT wild this round!")
                print("    Only quantity can be raised (same face value)")
            print(f"Active players: {[p.id for p in game_state.get_active_players()]}")
            print(f"Total dice in play: {game_state.get_total_dice()}")

        # Players take turns until someone challenges
        round_over = False
        turns_in_round = 0
        max_turns = 100  # Prevent infinite loops

        while not round_over and turns_in_round < max_turns:
            current_player = game_state.get_current_player()
            if not current_player:
                break

            current_agent = self.agents[current_player.id]

            # Agent makes decision
            action, bid = current_agent.make_decision(game_state)

            if action == 'bid':
                if game_state.make_bid(current_player.id, bid):
                    self.game_stats['total_bids'] += 1
                    self.game_stats['bids_by_player'][current_player.id] += 1

                    if self.verbose:
                        print(f"  {current_player.id} bids: {bid}")
                else:
                    if self.verbose:
                        print(f"  {current_player.id} made invalid bid: {bid}")
                    # Invalid bid, force challenge
                    action = 'challenge'

            if action == 'calza':
                # Handle calza (exact bid call)
                if self.verbose:
                    bidder_id = game_state.bid_history[-1][0] if game_state.bid_history else "Unknown"
                    print(f"  {current_player.id} calls CALZA on {bidder_id}'s bid!")
                    self._reveal_all_dice(game_state)

                # Resolve calza
                result = game_state.calza(current_player.id)

                if not result['valid']:
                    if self.verbose:
                        print(f"  CALZA INVALID: {result['error']}")
                    # Invalid calza, force challenge instead
                    action = 'challenge'
                else:
                    self.game_stats['calzas_by_player'][current_player.id] += 1
                    if result['success']:
                        self.game_stats['successful_calzas'] += 1
                        self.game_stats['dice_gained_by_player'][result['winner_id']] += 1
                    else:
                        self.game_stats['failed_calzas'] += 1
                        self.game_stats['dice_lost_by_player'][result['loser_id']] += 1

                    if self.verbose:
                        if result['success']:
                            print(f"  CALZA SUCCESSFUL! Exactly {result['actual_count']} dice!")
                            print(f"  {result['winner_id']} GAINS a die! (now has {game_state.players[result['winner_id']].num_dice} dice)")
                        else:
                            print(f"  CALZA FAILED! Actual count: {result['actual_count']} (bid was {result['bid_quantity']})")
                            print(f"  {result['loser_id']} LOSES a die! (now has {game_state.players[result['loser_id']].num_dice} dice)")

                    round_over = True

            if action == 'challenge':
                # Get the previous bidder (the one being challenged)
                if len(game_state.bid_history) == 0:
                    if self.verbose:
                        print("  No bid to challenge!")
                    break

                challenged_player_id = game_state.bid_history[-1][0]

                if self.verbose:
                    print(f"  {current_player.id} CHALLENGES {challenged_player_id}'s bid!")
                    self._reveal_all_dice(game_state)

                # Resolve challenge
                success, winner, loser = game_state.challenge_current_bid(current_player.id)

                self.game_stats['challenges_by_player'][current_player.id] += 1
                if success:
                    self.game_stats['successful_challenges'] += 1
                else:
                    self.game_stats['failed_challenges'] += 1

                self.game_stats['dice_lost_by_player'][loser] += 1

                if self.verbose:
                    if success:
                        print(f"  Challenge SUCCESSFUL! {loser} loses a die.")
                    else:
                        print(f"  Challenge FAILED! {loser} loses a die.")
                    print(f"  Remaining dice - {loser}: {game_state.players[loser].num_dice}")

                round_over = True

            turns_in_round += 1

        game_state.round_number += 1

    def _reveal_all_dice(self, game_state: GameState):
        """Reveal all dice for dramatic effect in verbose mode."""
        if not self.verbose:
            return

        print("\n  Revealing all dice:")
        for player_id, player in game_state.players.items():
            if player.is_active:
                dice_str = ', '.join(str(d) for d in sorted(player.dice))
                print(f"    {player_id}: [{dice_str}]")

        # Show the actual count
        if game_state.current_bid:
            dist = game_state.get_dice_distribution()
            target_face = game_state.current_bid.face_value
            actual = dist.get(target_face, 0)

            # Add jokers if applicable (NOT during palifico)
            effective_joker_mode = game_state.joker_mode and not game_state.is_palifico_round

            if effective_joker_mode and target_face != 1:
                actual += dist.get(1, 0)
                print(f"\n  Bid was: {game_state.current_bid}")
                print(f"  Actual {target_face}s: {dist.get(target_face, 0)} + {dist.get(1, 0)} aces = {actual}")
            else:
                print(f"\n  Bid was: {game_state.current_bid}")
                if game_state.is_palifico_round and target_face != 1:
                    print(f"  Actual count: {actual} (PALIFICO - aces not wild)")
                else:
                    print(f"  Actual count: {actual}")


class TournamentRunner:
    """Runs multiple games and collects aggregate statistics."""

    def __init__(self, verbose_games: bool = False):
        self.verbose_games = verbose_games
        self.results = defaultdict(lambda: {
            'wins': 0,
            'games_played': 0,
            'total_bids': 0,
            'total_challenges': 0,
            'successful_challenges': 0,
            'total_calzas': 0,
            'successful_calzas': 0,
            'dice_lost': 0,
            'dice_gained': 0,
            'avg_game_length': []
        })

    def run_tournament(self, agents: List[BaseAgent], num_games: int = 100,
                       starting_dice: int = 5, joker_mode: bool = True) -> Dict:
        """
        Run a tournament with multiple games.

        Returns:
            Dictionary of results by agent type
        """
        print(f"\nRunning tournament: {num_games} games")
        print(f"Agents: {[type(a).__name__ for a in agents]}")
        print("-" * 40)

        for game_num in range(num_games):
            if (game_num + 1) % 10 == 0:
                print(f"  Games completed: {game_num + 1}/{num_games}")

            # Create new simulator for each game
            simulator = GameSimulator(agents, self.verbose_games, starting_dice, joker_mode)
            winner_id, stats = simulator.run_game()

            # Update results
            for agent in agents:
                agent_type = type(agent).__name__
                pid = agent.player_id

                self.results[agent_type]['games_played'] += 1

                if winner_id == pid:
                    self.results[agent_type]['wins'] += 1

                self.results[agent_type]['total_bids'] += stats['bids_by_player'][pid]
                self.results[agent_type]['total_challenges'] += stats['challenges_by_player'][pid]
                self.results[agent_type]['total_calzas'] += stats['calzas_by_player'][pid]
                self.results[agent_type]['dice_lost'] += stats['dice_lost_by_player'][pid]
                self.results[agent_type]['dice_gained'] += stats['dice_gained_by_player'][pid]
                self.results[agent_type]['avg_game_length'].append(stats['rounds'])

            # Track successful challenges by agent
            for pid, agent in simulator.agents.items():
                agent_type = type(agent).__name__
                if stats['challenges_by_player'][pid] > 0:
                    # This is approximate - would need more detailed tracking for exact numbers
                    pass

        return self._calculate_final_stats()

    def _calculate_final_stats(self) -> Dict:
        """Calculate final statistics from tournament results."""
        final_stats = {}

        for agent_type, data in self.results.items():
            games = data['games_played']
            if games == 0:
                continue

            avg_game_length = sum(data['avg_game_length']) / len(data['avg_game_length']) if data['avg_game_length'] else 0

            final_stats[agent_type] = {
                'win_rate': data['wins'] / games,
                'total_wins': data['wins'],
                'total_games': games,
                'avg_bids_per_game': data['total_bids'] / games,
                'avg_challenges_per_game': data['total_challenges'] / games,
                'avg_calzas_per_game': data['total_calzas'] / games,
                'total_calzas': data['total_calzas'],
                'successful_calzas': data['successful_calzas'],
                'avg_dice_lost_per_game': data['dice_lost'] / games,
                'avg_dice_gained_per_game': data['dice_gained'] / games,
                'avg_game_length': avg_game_length
            }

        return final_stats

    def print_tournament_results(self, results: Dict):
        """Pretty print tournament results."""
        print("\n" + "="*60)
        print("TOURNAMENT RESULTS")
        print("="*60)

        # Sort by win rate
        sorted_agents = sorted(results.items(), key=lambda x: x[1]['win_rate'], reverse=True)

        print(f"\n{'Agent Type':<20} {'Win Rate':<12} {'Wins/Games':<15} {'Avg Bids':<10} {'Avg Challenges':<15}")
        print("-"*80)

        for agent_type, stats in sorted_agents:
            win_rate = f"{stats['win_rate']:.1%}"
            wins_games = f"{stats['total_wins']}/{stats['total_games']}"
            avg_bids = f"{stats['avg_bids_per_game']:.1f}"
            avg_challenges = f"{stats['avg_challenges_per_game']:.1f}"

            print(f"{agent_type:<20} {win_rate:<12} {wins_games:<15} {avg_bids:<10} {avg_challenges:<15}")

        print("\nAdditional Statistics:")
        for agent_type, stats in sorted_agents:
            print(f"\n{agent_type}:")
            print(f"  Average dice lost per game: {stats['avg_dice_lost_per_game']:.1f}")
            print(f"  Average dice gained per game: {stats['avg_dice_gained_per_game']:.1f}")
            print(f"  Average calzas per game: {stats['avg_calzas_per_game']:.2f}")
            if stats['total_calzas'] > 0:
                calza_success_rate = stats['successful_calzas'] / stats['total_calzas']
                print(f"  Calza success rate: {calza_success_rate:.1%} ({stats['successful_calzas']}/{stats['total_calzas']})")
            print(f"  Average game length: {stats['avg_game_length']:.1f} rounds")