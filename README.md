# Cassino

The **Hungarian two-player version** of Cassino, with a 52-card French deck —
in the browser, you against the computer.

## What to build

1. A module `casino` that passes the tests in `tests/`.
2. A table in the browser where you play a whole deal against the computer.
   Card images: for example [Byron Knoll's public-domain deck](https://commons.wikimedia.org/wiki/Category:Playing_cards_set_by_Byron_Knoll)
   on Wikimedia Commons (SVG, all 52 cards).

## Run the tests

```sh
uv run pytest
```

Without `uv`: `python -m pip install pytest`, then `python -m pytest`.

## Play in the browser

```sh
uv run python -m casino.web
```

Then open <http://127.0.0.1:8000>.

## The interface the tests use

```python
from casino import value, Move, new_deal, legal_moves, play, deal_over, score
```

A card is a string: rank, then suit. Ranks `A 2 3 4 5 6 7 8 9 10 J Q K`,
suits `S H D C`. So `"10D"`, `"AS"`, `"QH"`.

| Name | What it is |
|---|---|
| `value(card)` | The card's value. |
| `Move(hand, table)` | Two `frozenset`s of cards: what the player plays from hand, and what they take from the table. Placing a card without taking anything is `Move(frozenset({"7H"}), frozenset())`. |
| `new_deal(deck, first=0)` | Deals from `deck`, a sequence of the 52 cards in order: the first three go to player `first`, the next three to the other player, the next four face up on the table. The rest is the stock, drawn from the front. |
| `legal_moves(state)` | Every legal `Move` for the player to move. |
| `play(state, move)` | The state after the move — including everything the rules make happen before the next move. Raises `ValueError` if the move is not legal. |
| `deal_over(state)` | `True` once every card has been taken. |
| `score(state)` | A pair: the points each player earned in the finished deal. |

The tests read these fields of a state:

| Field | What it is |
|---|---|
| `hands` | A pair of tuples: each player's cards. |
| `table` | A tuple: the cards face up on the table. |
| `talon` | A tuple: the stock, next card first. |
| `piles` | A pair of tuples: the cards each player has taken. |
| `sweeps` | A pair: the points each player has earned from sweeps so far. |
| `player` | Whose turn it is, `0` or `1`. |
