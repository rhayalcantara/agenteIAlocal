"""
Agente de ajedrez con Playwright.
- Abre el browser con index.html
- Espera que el usuario configure y cierre el lobby
- Juega como la IA del color opuesto al elegido por el usuario
- Dificultad: easy/medium/hard (minimax) | expert (Stockfish) | llm (Claude AI)
"""
import re
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

HTML_PATH = Path(__file__).parent / "index.html"
STOCKFISH_PATH = Path(__file__).parent / "stockfish.exe"

# -------------------------------------------------------
# Minimax paramétrico — recibe [forWhite, depth, easyMode]
# Usa las funciones del juego expuestas globalmente en la página:
# getLegalMoves, applyMoveToBoard, isWhitePiece, board
# -------------------------------------------------------
MINIMAX_JS = """
([forWhite, depth, easyMode]) => {
    const PIECE_VAL = {p:1,n:3,b:3.1,r:5,q:9,k:1000,P:1,N:3,B:3.1,R:5,Q:9,K:1000};
    const CENTER = [[3,3],[3,4],[4,3],[4,4]];

    function evalBoard(b) {
        let s = 0;
        for (let r = 0; r < 8; r++) for (let c = 0; c < 8; c++) {
            const p = b[r][c]; if (!p) continue;
            const v = (PIECE_VAL[p] || 0) + (CENTER.some(([cr,cc]) => cr===r && cc===c) ? 0.15 : 0);
            s += p === p.toUpperCase() ? v : -v;
        }
        return s;
    }

    function allMoves(b, isW) {
        const mv = [];
        for (let r = 0; r < 8; r++) for (let c = 0; c < 8; c++) {
            const p = b[r][c];
            if (!p || isWhitePiece(p) !== isW) continue;
            getLegalMoves(r, c, b).forEach(([tr, tc]) => mv.push({fromR:r,fromC:c,toR:tr,toC:tc}));
        }
        return mv;
    }

    function minimax(b, d, alpha, beta, maxi) {
        const mv = allMoves(b, maxi);
        if (d === 0 || !mv.length) return evalBoard(b);
        if (maxi) {
            let best = -Infinity;
            for (const m of mv) {
                best = Math.max(best, minimax(applyMoveToBoard(b,m.fromR,m.fromC,m.toR,m.toC), d-1, alpha, beta, false));
                alpha = Math.max(alpha, best);
                if (beta <= alpha) break;
            }
            return best;
        } else {
            let best = Infinity;
            for (const m of mv) {
                best = Math.min(best, minimax(applyMoveToBoard(b,m.fromR,m.fromC,m.toR,m.toC), d-1, alpha, beta, true));
                beta = Math.min(beta, best);
                if (beta <= alpha) break;
            }
            return best;
        }
    }

    const moves = allMoves(board, forWhite);
    if (!moves.length) return null;

    const scored = moves.map(m => ({
        ...m,
        score: minimax(applyMoveToBoard(board,m.fromR,m.fromC,m.toR,m.toC), depth-1, -Infinity, Infinity, !forWhite)
    }));
    scored.sort((a, b) => forWhite ? b.score - a.score : a.score - b.score);

    if (easyMode) {
        const pool = scored.slice(0, Math.min(3, scored.length));
        return pool[Math.floor(Math.random() * pool.length)];
    }
    return scored[0];
}
"""

# -------------------------------------------------------
# Helpers Playwright
# -------------------------------------------------------

def make_move(page, from_r, from_c, to_r, to_c):
    # Llamar directamente a executeMove en el JS del juego (no via clicks),
    # para evitar el filtro de playerColor en handleSquareClick
    page.evaluate("""([fr, fc, tr, tc]) => {
        executeMove(fr, fc, tr, tc);
        selectedSquare = null;
        legalMovesForSelected = [];
        renderBoard();
    }""", [from_r, from_c, to_r, to_c])
    time.sleep(0.4)

def take_screenshot(page, name):
    path = str(Path(__file__).parent / name)
    page.screenshot(path=path)

# -------------------------------------------------------
# Lobby
# -------------------------------------------------------

def wait_for_lobby(page) -> dict:
    """Espera que el usuario cierre el lobby (gameStarted = true)."""
    print("Esperando configuracion del lobby...")
    page.wait_for_function("() => gameStarted === true", timeout=120_000)
    config = page.evaluate("() => ({ playerColor, difficulty, gameTimeMinutes, aiShouldMoveFirst })")
    print(f"Config: color={config['playerColor']}, dificultad={config['difficulty']}, tiempo={config['gameTimeMinutes']}min")
    return config

# -------------------------------------------------------
# Motor de IA
# -------------------------------------------------------

def get_minimax_move(page, for_white: bool, difficulty: str) -> dict | None:
    depth     = {'easy': 1, 'medium': 2, 'hard': 3}.get(difficulty, 2)
    easy_mode = (difficulty == 'easy')
    return page.evaluate(MINIMAX_JS, [for_white, depth, easy_mode])


def board_to_fen(page) -> str:
    """Convierte el estado JS del tablero a notacion FEN."""
    state = page.evaluate("""() => ({
        board:           board,
        currentTurn:     currentTurn,
        castlingRights:  castlingRights,
        enPassantTarget: enPassantTarget,
        moveNumber:      currentMoveNumber
    })""")

    rows = []
    for js_row in state['board']:
        empty, row_str = 0, ''
        for piece in js_row:
            if not piece:
                empty += 1
            else:
                if empty:
                    row_str += str(empty)
                    empty = 0
                row_str += piece
        if empty:
            row_str += str(empty)
        rows.append(row_str)

    pos      = '/'.join(rows)
    active   = 'w' if state['currentTurn'] == 'white' else 'b'
    cr       = state['castlingRights']
    castling = (('K' if cr.get('wK') else '') + ('Q' if cr.get('wQ') else '') +
                ('k' if cr.get('bK') else '') + ('q' if cr.get('bQ') else '')) or '-'
    ep       = state['enPassantTarget']
    ep_str   = ('abcdefgh'[int(ep[1])] + str(8 - int(ep[0]))) if ep else '-'
    return f"{pos} {active} {castling} {ep_str} 0 {state['moveNumber']}"


def uci_to_coords(uci: str) -> tuple:
    """'e2e4' -> (6, 4, 4, 4)"""
    fc = ord(uci[0]) - ord('a')
    fr = 8 - int(uci[1])
    tc = ord(uci[2]) - ord('a')
    tr = 8 - int(uci[3])
    return fr, fc, tr, tc


def get_stockfish_move(page, for_white: bool) -> dict | None:
    """Consulta Stockfish para obtener la mejor jugada."""
    try:
        import chess
        import chess.engine
    except ImportError:
        print("python-chess no instalado. Instala con: pip install python-chess")
        return None

    if not STOCKFISH_PATH.exists():
        print(f"Stockfish no encontrado en {STOCKFISH_PATH}")
        print("Descarga desde https://stockfishchess.org/download/ y coloca stockfish.exe aqui.")
        return None

    fen = board_to_fen(page)
    try:
        b = chess.Board(fen)
        with chess.engine.SimpleEngine.popen_uci(str(STOCKFISH_PATH)) as eng:
            result = eng.play(b, chess.engine.Limit(time=1.0))
        if not result.move:
            return None
        fr, fc, tr, tc = uci_to_coords(result.move.uci())
        return {'fromR': fr, 'fromC': fc, 'toR': tr, 'toC': tc}
    except Exception as e:
        print(f"Error Stockfish: {e}")
        return None


def board_to_ascii(js_board) -> str:
    """Convierte el tablero JS a representacion ASCII para el prompt del LLM."""
    lines = ['  a b c d e f g h']
    for ri, row in enumerate(js_board):
        rank = 8 - ri
        cells = [p if p else '.' for p in row]
        lines.append(f"{rank} {' '.join(cells)}")
    return '\n'.join(lines)


def get_llm_move(page, for_white: bool) -> dict | None:
    """Pide una jugada a Claude via API de Anthropic."""
    try:
        import anthropic
        import chess
    except ImportError as e:
        print(f"Dependencia faltante: {e}")
        return None

    state = page.evaluate("""() => ({
        board: board,
        moveHistory: moveHistory,
        pendingWhiteMove: pendingWhiteMove
    })""")

    fen        = board_to_fen(page)
    ascii_board = board_to_ascii(state['board'])
    color      = 'white' if for_white else 'black'

    # Construir historial de movimientos
    history_parts = []
    for m in state['moveHistory']:
        history_parts.append(f"{m['num']}. {m['white']} {m.get('black', '')}")
    if state['pendingWhiteMove']:
        history_parts.append(f"{len(state['moveHistory'])+1}. {state['pendingWhiteMove']} ...")
    history_str = ' '.join(history_parts) if history_parts else 'Inicio de partida'

    prompt = f"""You are playing chess as {color.upper()}.

Board (uppercase=white, lowercase=black, .=empty):
{ascii_board}

FEN: {fen}
Move history: {history_str}

Choose your best move and respond in this EXACT format:
MOVE: <uci>

UCI format: source+destination squares, e.g. e2e4, g1f3, e1g1 (kingside castling)
Only output the MOVE line, nothing else."""

    client = anthropic.Anthropic()

    for attempt in range(3):
        print(f"  Claude pensando... (intento {attempt+1}/3)")
        try:
            message = client.messages.create(
                model="claude-opus-4-6",
                max_tokens=128,
                system="You are a strong chess player. Always respond with a valid UCI move in the requested format.",
                messages=[{"role": "user", "content": prompt}]
            )
            response_text = message.content[0].text.strip()
            print(f"  Respuesta: {response_text}")

            match = re.search(r'MOVE:\s*([a-h][1-8][a-h][1-8][qrbn]?)', response_text, re.IGNORECASE)
            if not match:
                print(f"  No se encontro movimiento UCI en la respuesta.")
                prompt += f"\n\nYour response '{response_text}' did not contain a valid UCI move. Try again with format: MOVE: e2e4"
                continue

            uci = match.group(1).lower()
            # Validar con python-chess
            chess_board = chess.Board(fen)
            move        = chess.Move.from_uci(uci)
            if move not in chess_board.legal_moves:
                print(f"  Movimiento ilegal: {uci}")
                legal = [m.uci() for m in list(chess_board.legal_moves)[:8]]
                prompt += f"\n\nMove {uci} is illegal. Some legal moves: {', '.join(legal)}. Choose one of the legal moves."
                continue

            print(f"  Claude jugo: {uci}")
            fr, fc, tr, tc = uci_to_coords(uci)
            return {'fromR': fr, 'fromC': fc, 'toR': tr, 'toC': tc}

        except Exception as e:
            print(f"  Error llamando a la API: {e}")
            break

    print("Claude no pudo dar un movimiento valido. Usando minimax como fallback.")
    return get_minimax_move(page, for_white, 'medium')


def get_ai_move(page, for_white: bool, difficulty: str) -> dict | None:
    """Despacha la jugada de IA segun la dificultad."""
    if difficulty == 'expert':
        move = get_stockfish_move(page, for_white)
        if move:
            return move
        print("Stockfish no disponible, usando minimax hard como fallback.")
        return get_minimax_move(page, for_white, 'hard')
    if difficulty == 'llm':
        return get_llm_move(page, for_white)
    return get_minimax_move(page, for_white, difficulty)

# -------------------------------------------------------
# Bucle principal
# -------------------------------------------------------

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=400)
        page = browser.new_page(viewport={"width": 1200, "height": 750})
        page.goto(HTML_PATH.as_uri())
        page.wait_for_selector(".chessboard")

        # Esperar que el usuario cierre el lobby
        config       = wait_for_lobby(page)
        player_color = config['playerColor']
        diff         = config['difficulty']
        ia_is_white  = (player_color == 'black')
        ia_str       = 'white' if ia_is_white else 'black'
        human_str    = player_color
        move_num     = 1

        print(f"IA juega con: {ia_str} | Dificultad: {diff}")

        # Si el jugador eligio negras, la IA (blancas) hace la primera jugada
        if ia_is_white:
            print(f"\n[Turno {move_num} - IA Blancas] Primera jugada...")
            best = get_ai_move(page, True, diff)
            if best:
                make_move(page, best['fromR'], best['fromC'], best['toR'], best['toC'])
                take_screenshot(page, f"move_{move_num:02d}_ia_white.png")
                print(f"IA jugo: ({best['fromR']},{best['fromC']}) -> ({best['toR']},{best['toC']})")

        # Bucle de juego
        while True:
            # Esperar que sea el turno de la IA
            try:
                page.wait_for_function(
                    f"() => currentTurn === '{ia_str}' && !gameOver",
                    timeout=300_000
                )
            except Exception:
                print("Tiempo agotado o partida terminada. Saliendo.")
                break

            if page.evaluate("() => gameOver"):
                print("Partida terminada por el juego.")
                break

            # Verificar movimientos legales
            has_moves = page.evaluate(
                f"() => hasAnyLegalMoves(board, {'true' if ia_is_white else 'false'})"
            )
            if not has_moves:
                print(f"Sin movimientos para la IA ({ia_str}). Fin.")
                break

            move_num += 1
            take_screenshot(page, f"move_{move_num:02d}_{human_str}.png")

            # Calcular jugada
            print(f"\n[Turno {move_num} - IA {ia_str}] Calculando ({diff})...")
            best = get_ai_move(page, ia_is_white, diff)

            if not best:
                print("No se encontro jugada. Fin.")
                break

            make_move(page, best['fromR'], best['fromC'], best['toR'], best['toC'])
            take_screenshot(page, f"move_{move_num:02d}_{ia_str}.png")
            print(f"IA jugo: ({best['fromR']},{best['fromC']}) -> ({best['toR']},{best['toC']})")

            # Estado tras la jugada de la IA
            state = page.evaluate(f"""() => {{
                const humanIsWhite = {'false' if ia_is_white else 'true'};
                return {{
                    inCheck:  isKingInCheck(board, humanIsWhite),
                    hasLegal: hasAnyLegalMoves(board, humanIsWhite),
                    gameOver: gameOver
                }};
            }}""")

            if state['gameOver'] or not state['hasLegal']:
                status = 'JAQUE MATE' if state['inCheck'] else 'TABLAS'
                print(f"{status} - Fin de la partida.")
                break

            if state['inCheck']:
                print(f"Jaque al rey {'blanco' if not ia_is_white else 'negro'}!")

            print(f"Esperando jugada del humano ({human_str})...")

        print("\nPartida terminada. Cierra el navegador cuando quieras.")
        try:
            page.wait_for_event("close", timeout=0)
        except Exception:
            pass
        browser.close()


if __name__ == "__main__":
    main()
