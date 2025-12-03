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

    # Higher quantities with same face value
    next_bids.extend((q, value) for q in range(quantity + 1, n_dice + 1))

    # Higher face values with same or higher quantity
    if value == 1:
        # If current bid is aces (joker), need at least 2*quantity + 1 for non-aces
        min_quantity = 2 * quantity + 1
        for v in range(2, 7):  # Values 2-6
            next_bids.extend((q, v) for q in range(min_quantity, n_dice + 1))
    else:
        # For non-ace current bids:
        # Same quantity with higher face values
        for v in range(value + 1, 7):
            next_bids.extend((q, v) for q in range(quantity, n_dice + 1))

    # Joker bids (switching to aces)
    if joker_mode and value != 1:
        # When switching to joker, min quantity is (current_quantity + 1) // 2
        min_joker_quantity = (quantity + 1) // 2
        next_bids.extend((q, 1) for q in range(min_joker_quantity, n_dice + 1))

    return next_bids


def safest_bids(my_dice, current_bid, n_dice, joker_mode=True):
    """Select the next bid based on highest probability of being valid.

    Args:
        my_dice: List of known dice
        current_bid: Current bid tuple (quantity, face_value)
        n_dice: Total dice in game
        joker_mode: Whether aces are wild
    """
    unknown_dice = n_dice - len(my_dice)
    next_bids = next_valid_bids(current_bid, n_dice, joker_mode)
    all_bids = []

    for bid in next_bids:
        # Count matches in known dice (handles joker mode internally)
        known_matches = count_matches(my_dice, bid[1], joker_mode)

        # Determine probability for unknown dice
        if bid[1] == 1:
            # Bidding on aces - only aces count (p = 1/6)
            p_match = 1 / 6
        elif joker_mode:
            # Bidding on non-aces with joker mode - aces count as wild (p = 2/6 = 1/3)
            p_match = 1 / 3
        else:
            # No joker mode - only exact matches count (p = 1/6)
            p_match = 1 / 6

        prob = count_atleast_prob(bid[0] - known_matches, unknown_dice, p_match)
        prob_norm = round(float(prob), 4)
        all_bids.append((bid, prob_norm))

    bids_sorted = sorted(all_bids, key=lambda x: x[1], reverse=True)

    return bids_sorted


def acceptable_bids(my_dice, current_bid, n_dice, prob_threshold, joker_mode=True):
    """Select bids above a certain probability threshold."""
    bids = safest_bids(my_dice, current_bid, n_dice, joker_mode)
    selected = [bid for bid in bids if bid[1] >= prob_threshold]
    return selected


def risky_bids(my_dice, current_bid, n_dice, prob_threshold, joker_mode=True):
    """Select bids with the highest jump"""
    bids = acceptable_bids(my_dice, current_bid, n_dice, prob_threshold, joker_mode)
    risky_bids = sorted(bids, key=lambda x: x[0][0], reverse=True)
    return risky_bids


def select_action(my_dice, current_bid, n_dice, prob_threshold, joker_mode=True):
    """Select action based on baseline bid probabilities.

    Args:
        my_dice: List of known dice
        current_bid: Current bid tuple (quantity, face_value)
        n_dice: Total dice in game
        prob_threshold: Minimum probability threshold for acceptable bids
        joker_mode: Whether aces are wild
    """
    candidate_bids = risky_bids(
        my_dice, current_bid, n_dice, prob_threshold, joker_mode
    )

    # Determine probability for current bid
    if current_bid[1] == 1:
        # Bidding on aces - only aces count (p = 1/6)
        p_match = 1 / 6
    elif joker_mode:
        # Bidding on non-aces with joker mode - aces count as wild (p = 1/3)
        p_match = 1 / 3
    else:
        # No joker mode - only exact matches count (p = 1/6)
        p_match = 1 / 6

    current_bid_prob = count_atleast_prob(
        current_bid[0], n_dice - len(my_dice), p_match
    )
    equal_prob = count_exact_prob(current_bid[0], n_dice - len(my_dice), p_match)
    print(
        f"Current bid: {current_bid} (probability: {current_bid_prob:.4f}, exact: {equal_prob:.4f})"
    )
    print(f"Top 5 bids (with prob >= {prob_threshold}):")
    for bid, prob in candidate_bids[:5]:
        print(f"  Bid: {bid}, Probability: {prob:.4f}")


if __name__ == "__main__":

    my_dice = [2, 2, 2, 4, 6]  # Example known dice
    current_bid = (4, 3)  # Example current bid
    n_dice = 15  # Total number of dice in the game

    # print(select_action(my_dice, current_bid, n_dice, prob_threshold=0.5))
    print(count_atleast_prob(current_bid[0], n_dice - 5, 1 / 3))
