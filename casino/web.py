"""Small browser interface for playing Cassino against a simple computer player."""

import json
import random
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from . import State, deal_over, legal_moves, new_deal, play, score

DECK = [rank + suit for suit in "SHDC" for rank in ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]]
GAMES: dict[str, State] = {}


def _new_game() -> tuple[str, State]:
    game_id = str(random.randint(100000, 999999))
    cards = DECK[:]
    random.shuffle(cards)
    state = new_deal(cards)
    GAMES[game_id] = state
    return game_id, state


def _computer_move(state: State) -> State:
    moves = sorted(legal_moves(state), key=lambda move: (not move.table, -len(move.table), sorted(move.hand)))
    return play(state, moves[0])


def _view(game_id: str, state: State) -> dict:
    return {
        "game": game_id,
        "hand": list(state.hands[0]),
        "computer_cards": len(state.hands[1]),
        "table": list(state.table),
        "player": state.player,
        "over": deal_over(state),
        "score": list(score(state)) if deal_over(state) else None,
        "sweeps": list(state.sweeps),
    }


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cassino Table</title><style>
body{margin:0;background:#17352c;color:#f7f0dc;font:16px Georgia,serif}main{max-width:900px;margin:auto;padding:28px 20px}h1{font-size:42px;margin:0 0 8px}p{color:#d8ccb0}.felt{background:#1f5a45;border:10px solid #a97842;border-radius:18px;padding:24px;box-shadow:0 12px 30px #071610}section{margin:20px 0}.cards{display:flex;flex-wrap:wrap;gap:10px;min-height:74px}.card{background:#fffdf6;color:#1d2520;border:0;border-radius:6px;padding:15px 11px;min-width:45px;font:18px Georgia;box-shadow:0 3px 4px #092218;cursor:pointer}.card.red{color:#ae3029}.card.selected{outline:4px solid #e8c56b;transform:translateY(-5px)}button.action{background:#e8c56b;border:0;border-radius:5px;padding:12px 18px;font-weight:bold;cursor:pointer}button.action:disabled{opacity:.45;cursor:not-allowed}.status{font-size:18px;min-height:28px}.meta{display:flex;justify-content:space-between;border-bottom:1px solid #76a58a;padding-bottom:12px}@media(max-width:600px){h1{font-size:34px}.felt{padding:15px;border-width:6px}.card{padding:12px 8px}}
</style></head><body><main><h1>Cassino</h1><p>Capture cards whose values add up to the card or cards you play.</p><div class="felt"><div class="meta"><span id="turn"></span><span id="count"></span></div><section><strong>Computer</strong><div id="computer" class="cards"></div></section><section><strong>Table</strong><div id="table" class="cards"></div></section><section><strong>Your hand</strong><div id="hand" class="cards"></div></section><button id="play" class="action">Play selected cards</button><button id="new" class="action">New deal</button><div id="status" class="status"></div></div></main><script>
let game, selectedHand=[],selectedTable=[];const $=id=>document.getElementById(id);
async function newGame(){let r=await fetch('/new');game=await r.json();selectedHand=[];selectedTable=[];render()}
async function refresh(){game=await (await fetch('/state?id='+game.game)).json();render()}
function card(c,area){let b=document.createElement('button');b.className='card '+(/[HD]/.test(c)?'red':'');b.textContent=c;b.onclick=()=>{let a=area==='hand'?selectedHand:selectedTable,i=a.indexOf(c);i<0?a.push(c):a.splice(i,1);render()};if((area==='hand'?selectedHand:selectedTable).includes(c))b.classList.add('selected');return b}
function render(){['hand','table'].forEach(area=>{$(area).replaceChildren(...game[area].map(c=>card(c,area)))});$('computer').replaceChildren(...Array(game.computer_cards).fill(0).map(()=>{let b=document.createElement('span');b.className='card';b.textContent='?';return b}));$('turn').textContent=game.over?'Deal complete':game.player===0?'Your turn':'Computer is thinking';$('count').textContent='Sweeps '+game.sweeps[0]+' / '+game.sweeps[1];$('play').disabled=game.player!==0||!selectedHand.length;$('status').textContent=game.score?'Score: '+game.score.join(' - '):''}
async function computerTurn(){while(game.player===1&&!game.over){let r=await fetch('/computer?id='+game.game,{method:'POST'});if(!r.ok){$('status').textContent='The computer could not make a move.';return}game=await r.json();render();if(game.player===1&&!game.over){await new Promise(resolve=>setTimeout(resolve,250))}}}
async function playMove(){let r=await fetch('/move',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:game.game,hand:selectedHand,table:selectedTable})});if(!r.ok){$('status').textContent='That capture is not legal.';return}game=await r.json();selectedHand=[];selectedTable=[];render();if(game.player===1&&!game.over){await computerTurn()}}$('play').onclick=playMove;$('new').onclick=newGame;newGame();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, body: str, content_type: str = "text/html"):
        encoded = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send(HTML)
        elif parsed.path == "/new":
            self._send(json.dumps(_view(*_new_game())), "application/json")
        elif parsed.path == "/state":
            game_id = parsed.query.removeprefix("id=")
            self._send(json.dumps(_view(game_id, GAMES[game_id])), "application/json")
        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length) or b"{}")
        game_id = data.get("id") or parsed.query.removeprefix("id=")
        try:
            state = GAMES[game_id]
            if parsed.path == "/move":
                from . import Move
                state = play(state, Move(frozenset(data["hand"]), frozenset(data["table"])))
            elif parsed.path == "/computer":
                state = _computer_move(state)
            else:
                self.send_error(404)
                return
            GAMES[game_id] = state
            self._send(json.dumps(_view(game_id, state)), "application/json")
        except (KeyError, ValueError):
            self.send_error(400)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    print("Cassino is ready at http://127.0.0.1:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()