from scipy.stats import binom


def count_atleast_prob(k_matches, n_dice, p):
    """Calculate the probability of at least k matches in n dice rolls.

    Args:
        k_matches: Number of matches needed
        n_dice: Number of dice being rolled
        p: Probability for a single die match

    This is equivalent to summing the probabilities of getting k, k+1, ..., n matches, but faster in python.
    """
    return binom.sf(k_matches - 1, n_dice, p)


def count_exact_prob(k_matches, n_dice, p):
    """Calculate the probability of exactly k matches in n dice rolls."""
    return binom.pmf(k_matches, n_dice, p)


def count_atmost_prob(k_matches, n_dice, p):
    """Calculate the probability of at most k matches in n dice rolls.
    This is equivalent to summing the probabilities of getting 0, 1, ..., k matches, but faster in python.
    """
    return binom.cdf(k_matches, n_dice, p)


def count_matches(known_dice, value, joker_mode=True):
    """Count the number of dice that match the given value, including aces if in joker mode"""
    return sum(1 for die in known_dice if die == value or (joker_mode and die == 1))


def next_valid_bids(current_bid, n_dice, joker_mode=True):
    """Generate the next valid bids"""
    quantity, value = current_bid
    next_bids = []

    # Higher quantities with same value
    next_bids.extend((q, value) for q in range(quantity + 1, n_dice + 1))

    # Higher values with any valid quantity
    quantity = (
        2 * quantity if value == 1 else quantity
    )  # Minimum quantity for next value when current is ace
    for v in range(value + 1, 7):
        next_bids.extend((q, v) for q in range(quantity + 1, n_dice + 1))

    # Joker bid (half quantity, value = 1)
    if joker_mode and value != 1:
        next_bids.append(((quantity + 1) // 2, 1))

    return next_bids


def safest_bids(my_dice, current_bid, n_dice):
    """Select the next bid based on highest probability of being valid."""
    unknown_dice = n_dice - len(my_dice)
    next_bids = next_valid_bids(current_bid, n_dice)
    all_bids = []

    for bid in next_bids:
        known_matches = count_matches(my_dice, bid[1])
        prob = count_atleast_prob(bid[0] - known_matches, unknown_dice, 1 / 3)
        prob_norm = round(float(prob), 4)
        all_bids.append((bid, prob_norm))

    bids_sorted = sorted(all_bids, key=lambda x: x[1], reverse=True)

    return bids_sorted


def acceptable_bids(my_dice, current_bid, n_dice, prob_threshold):
    """Select bids above a certain probability threshold."""
    bids = safest_bids(my_dice, current_bid, n_dice)
    selected = [bid for bid in bids if bid[1] >= prob_threshold]
    return selected


def risky_bids(my_dice, current_bid, n_dice, prob_threshold):
    """Select bids with the highest jump"""
    bids = acceptable_bids(my_dice, current_bid, n_dice, prob_threshold)
    risky_bids = sorted(bids, key=lambda x: x[0][0], reverse=True)
    return risky_bids


def select_action(my_dice, current_bid, n_dice, prob_threshold):
    """Select action based on baseline bid probabilities."""
    candidate_bids = risky_bids(my_dice, current_bid, n_dice, prob_threshold)
    current_bid_prob = count_atleast_prob(current_bid[0], n_dice - len(my_dice), 1 / 3)
    equal_prob = count_exact_prob(current_bid[0], n_dice - len(my_dice), 1 / 3)
    print(
        f"Current bid: {current_bid} (probability: {current_bid_prob:.4f}, exact: {equal_prob:.4f})"
    )
    print(f"Top 5 bids (with prob >= {prob_threshold}):")
    for bid, prob in candidate_bids[:5]:
        print(f"  Bid: {bid}, Probability: {prob:.4f}")


if __name__ == "__main__":
    my_dice = [2, 3, 1, 5]  # Example known dice
    current_bid = (3, 2)  # Example current bid
    n_dice = 30  # Total number of dice in the game

    print(select_action(my_dice, current_bid, n_dice, prob_threshold=0.5))
