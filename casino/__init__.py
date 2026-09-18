"""Rules and state transitions for a two-player game of Cassino."""

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

RANKS = "A23456789 10JQK".replace(" ", "")
SUITS = "SHDC"


def value(card: str) -> int:
    """Return the numerical value of a card."""
    rank = card[:-1]
    if rank not in RANKS:
        raise ValueError(f"invalid card: {card}")
    return 1 if rank == "A" else int(rank) if rank.isdigit() else {"J": 11, "Q": 12, "K": 13}[rank]


@dataclass(frozen=True)
class Move:
    hand: frozenset[str]
    table: frozenset[str]


@dataclass(frozen=True)
class State:
    hands: tuple[tuple[str, ...], tuple[str, ...]]
    table: tuple[str, ...]
    talon: tuple[str, ...]
    piles: tuple[tuple[str, ...], tuple[str, ...]]
    sweeps: tuple[int, int]
    player: int
    last_capturer: int | None = None
    double_move: bool = False


def new_deal(deck: Iterable[str], first: int = 0) -> State:
    """Create a deal from an ordered deck, preserving card order in each area."""
    cards = tuple(deck)
    if first not in (0, 1):
        raise ValueError("first must be 0 or 1")
    if len(cards) < 10:
        raise ValueError("a deal needs at least ten cards")
    hands = [[], []]
    hands[first].extend(cards[:3])
    hands[1 - first].extend(cards[3:6])
    return State(
        hands=(tuple(hands[0]), tuple(hands[1])),
        table=cards[6:10],
        talon=cards[10:],
        piles=((), ()),
        sweeps=(0, 0),
        player=first,
    )


def _subsets(cards: tuple[str, ...]) -> list[frozenset[str]]:
    return [
        frozenset(combo)
        for size in range(1, len(cards) + 1)
        for combo in combinations(cards, size)
    ]


def legal_moves(state: State) -> set[Move]:
    """Return all captures and placements available to the current player."""
    hand = state.hands[state.player]
    moves = {Move(frozenset({card}), frozenset()) for card in hand}
    hand_sets = _subsets(hand)
    table_sets = _subsets(state.table)
    for played in hand_sets:
        hand_total = sum(value(card) for card in played)
        for captured in table_sets:
            if hand_total == sum(value(card) for card in captured):
                moves.add(Move(played, captured))
    return moves


def _draw_round(state: State, player: int) -> State:
    if not state.talon:
        return state
    hands = [[], []]
    cards = state.talon
    hands[player].extend(cards[:3])
    hands[1 - player].extend(cards[3:6])
    return State(
        hands=(tuple(hands[0]), tuple(hands[1])),
        table=state.table,
        talon=cards[6:],
        piles=state.piles,
        sweeps=state.sweeps,
        player=player,
        last_capturer=state.last_capturer,
        double_move=state.double_move,
    )


def play(state: State, move: Move) -> State:
    """Apply a legal move and perform any redeal or final collection it causes."""
    if move not in legal_moves(state):
        raise ValueError("illegal move")
    player = state.player
    hands = [list(hand) for hand in state.hands]
    table = list(state.table)
    piles = [list(pile) for pile in state.piles]
    sweeps = list(state.sweeps)

    for card in move.hand:
        hands[player].remove(card)
    if move.table:
        for card in move.table:
            table.remove(card)
        piles[player].extend(move.hand | move.table)
        last_capturer = player
    else:
        table.extend(move.hand)
        last_capturer = state.last_capturer

    if move.table and not table:
        sweeps[player] += 1

    next_player = player if state.double_move else 1 - player
    double_move = False
    if move.table and not table:
        double_move = True
    if not hands[next_player] and hands[1 - next_player]:
        next_player = 1 - next_player
        double_move = False
    result = State(
        hands=(tuple(hands[0]), tuple(hands[1])),
        table=tuple(table),
        talon=state.talon,
        piles=(tuple(piles[0]), tuple(piles[1])),
        sweeps=(sweeps[0], sweeps[1]),
        player=next_player,
        last_capturer=last_capturer,
        double_move=double_move,
    )
    if not any(result.hands) and result.talon:
        result = _draw_round(result, result.last_capturer if result.last_capturer is not None else next_player)
    elif not any(result.hands) and not result.talon and result.table and result.last_capturer is not None:
        final_piles = [list(pile) for pile in result.piles]
        final_piles[result.last_capturer].extend(result.table)
        result = State(
            hands=result.hands,
            table=(),
            talon=(),
            piles=(tuple(final_piles[0]), tuple(final_piles[1])),
            sweeps=result.sweeps,
            player=result.player,
            last_capturer=result.last_capturer,
            double_move=result.double_move,
        )
    return result


def deal_over(state: State) -> bool:
    return not any(state.hands) and not state.talon and not state.table


def score(state: State) -> tuple[int, int]:
    """Score a finished deal using the standard Hungarian two-player rules."""
    if not deal_over(state):
        raise ValueError("the deal is not over")
    points = []
    for pile in state.piles:
        points.append(
            (3 if len(pile) >= 27 else 0)
            + (2 if sum(card.endswith("S") for card in pile) >= 7 else 0)
            + sum(card.startswith("A") for card in pile)
            + (2 if "10D" in pile else 0)
            + (1 if "2S" in pile else 0)
            + state.sweeps[len(points)]
        )
    return tuple(points)
