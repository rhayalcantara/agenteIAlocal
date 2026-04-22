const boardElement = document.getElementById('board');
const historyList = document.getElementById('move-history');

let board = [];
let selectedSquare = null;
let legalMovesForSelected = [];
let moveHistory = []; // [{num, white, black}, ...]
let currentTurn = 'white';
let currentMoveNumber = 1;
let pendingWhiteMove = null;
// Derechos de enroque: se pierde si el rey o la torre correspondiente se mueve
let castlingRights = { wK: true, wQ: true, bK: true, bQ: true };
// Casilla objetivo de captura al paso (null o [fila, col])
let enPassantTarget = null;
// Bandera de partida terminada
let gameOver = false;
let gameResult = '*'; // PGN result: '1-0' | '0-1' | '1/2-1/2' | '*'
let gameStartDate = null; // fecha de inicio para el PGN

// --- Configuración del lobby ---
let playerColor     = 'white';  // 'white' | 'black'
let difficulty      = 'medium'; // 'easy' | 'medium' | 'hard' | 'expert'
let gameTimeMinutes = 5;
let gameStarted     = false;
let aiShouldMoveFirst = false;

// --- Tablero girado y tamaño responsive ---
let boardFlipped = false;

// --- Temporizador ---
let whiteTimeMs = 0, blackTimeMs = 0;
let activeClockColor = null;
let clockInterval = null;
let clocksStarted = false;

const PIECES = {
    'r': '♜', 'n': '♞', 'b': '♝', 'q': '♛', 'k': '♚', 'p': '♟',
    'R': '♖', 'N': '♘', 'B': '♗', 'Q': '♕', 'K': '♔', 'P': '♙'
};

// Nombres de piezas en notación algebraica española
const PIECE_SYMBOL = {
    'k': 'R', 'K': 'R', // Rey
    'q': 'D', 'Q': 'D', // Dama
    'r': 'T', 'R': 'T', // Torre
    'b': 'A', 'B': 'A', // Alfil
    'n': 'C', 'N': 'C', // Caballo
    'p': '',  'P': ''   // Peón (sin símbolo)
};

const PIECE_NAME = {
    'k': 'Rey', 'K': 'Rey',
    'q': 'Dama', 'Q': 'Dama',
    'r': 'Torre', 'R': 'Torre',
    'b': 'Alfil', 'B': 'Alfil',
    'n': 'Caballo', 'N': 'Caballo',
    'p': 'Peón', 'P': 'Peón'
};

const INITIAL_LAYOUT = [
    ['r', 'n', 'b', 'q', 'k', 'b', 'n', 'r'],
    ['p', 'p', 'p', 'p', 'p', 'p', 'p', 'p'],
    ['', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', ''],
    ['', '', '', '', '', '', '', ''],
    ['P', 'P', 'P', 'P', 'P', 'P', 'P', 'P'],
    ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
];

// --- Utilidades ---

function isWhitePiece(p) { return p && p !== '' && p === p.toUpperCase(); }
function isBlackPiece(p) { return p && p !== '' && p === p.toLowerCase(); }

function getSquareName(r, c) {
    return 'abcdefgh'[c] + (8 - r);
}

function getMoveNotation(piece, fromR, fromC, toR, toC, isCapture) {
    // Enroque: rey mueve 2 columnas desde su posición inicial
    if ((piece === 'K' && fromR === 7 && fromC === 4) ||
        (piece === 'k' && fromR === 0 && fromC === 4)) {
        if (toC === 6) return 'O-O';
        if (toC === 2) return 'O-O-O';
    }
    const sym = PIECE_SYMBOL[piece] || '';
    const dest = getSquareName(toR, toC);
    if (piece.toLowerCase() === 'p') {
        if (isCapture) return 'abcdefgh'[fromC] + 'x' + dest;
        return dest;
    }
    return sym + (isCapture ? 'x' : '') + dest;
}

// --- Validación de movimientos ---

function getLegalMovesRaw(r, c, boardState, forAttack = false) {
    const piece = boardState[r][c];
    if (!piece) return [];
    const moves = [];
    const isWhite = isWhitePiece(piece);
    const pieceLower = piece.toLowerCase();

    function addIfValid(tr, tc) {
        if (tr < 0 || tr > 7 || tc < 0 || tc > 7) return;
        const target = boardState[tr][tc];
        if (target && isWhitePiece(target) === isWhite) return; // pieza propia
        moves.push([tr, tc]);
    }

    function addSliding(dirs) {
        for (const [dr, dc] of dirs) {
            let tr = r + dr, tc = c + dc;
            while (tr >= 0 && tr <= 7 && tc >= 0 && tc <= 7) {
                const target = boardState[tr][tc];
                if (target) {
                    if (isWhitePiece(target) !== isWhite) moves.push([tr, tc]); // captura
                    break; // bloqueado
                }
                moves.push([tr, tc]);
                tr += dr; tc += dc;
            }
        }
    }

    switch (pieceLower) {
        case 'p': {
            const dir = isWhite ? -1 : 1;
            const startRow = isWhite ? 6 : 1;
            // Avance de 1
            if (r + dir >= 0 && r + dir <= 7 && !boardState[r + dir][c]) {
                moves.push([r + dir, c]);
                // Avance inicial de 2
                if (r === startRow && !boardState[r + 2 * dir][c]) {
                    moves.push([r + 2 * dir, c]);
                }
            }
            // Capturas diagonales y captura al paso
            for (const dc of [-1, 1]) {
                const tr = r + dir, tc = c + dc;
                if (tr >= 0 && tr <= 7 && tc >= 0 && tc <= 7) {
                    const target = boardState[tr][tc];
                    if (target && isWhitePiece(target) !== isWhite) {
                        moves.push([tr, tc]);
                    } else if (!target && enPassantTarget &&
                               tr === enPassantTarget[0] && tc === enPassantTarget[1]) {
                        // Captura al paso: casilla vacía pero es el objetivo válido
                        moves.push([tr, tc]);
                    }
                }
            }
            break;
        }
        case 'n':
            for (const [dr, dc] of [[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]]) {
                addIfValid(r + dr, c + dc);
            }
            break;
        case 'b':
            addSliding([[-1,-1],[-1,1],[1,-1],[1,1]]);
            break;
        case 'r':
            addSliding([[-1,0],[1,0],[0,-1],[0,1]]);
            break;
        case 'q':
            addSliding([[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]]);
            break;
        case 'k': {
            for (const [dr, dc] of [[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]]) {
                addIfValid(r + dr, c + dc);
            }
            // Enroque: solo cuando no verificamos ataques (evita recursión infinita)
            if (!forAttack) {
                if (isWhite && r === 7 && c === 4) {
                    // Enroque corto blancas (O-O): rey e1→g1, torre h1→f1
                    if (castlingRights.wK &&
                        boardState[7][5] === '' && boardState[7][6] === '' &&
                        boardState[7][7] === 'R' &&
                        !isSquareAttackedBy(boardState, 7, 4, false) &&
                        !isSquareAttackedBy(boardState, 7, 5, false) &&
                        !isSquareAttackedBy(boardState, 7, 6, false)) {
                        moves.push([7, 6]);
                    }
                    // Enroque largo blancas (O-O-O): rey e1→c1, torre a1→d1
                    if (castlingRights.wQ &&
                        boardState[7][3] === '' && boardState[7][2] === '' && boardState[7][1] === '' &&
                        boardState[7][0] === 'R' &&
                        !isSquareAttackedBy(boardState, 7, 4, false) &&
                        !isSquareAttackedBy(boardState, 7, 3, false) &&
                        !isSquareAttackedBy(boardState, 7, 2, false)) {
                        moves.push([7, 2]);
                    }
                } else if (!isWhite && r === 0 && c === 4) {
                    // Enroque corto negras (O-O): rey e8→g8, torre h8→f8
                    if (castlingRights.bK &&
                        boardState[0][5] === '' && boardState[0][6] === '' &&
                        boardState[0][7] === 'r' &&
                        !isSquareAttackedBy(boardState, 0, 4, true) &&
                        !isSquareAttackedBy(boardState, 0, 5, true) &&
                        !isSquareAttackedBy(boardState, 0, 6, true)) {
                        moves.push([0, 6]);
                    }
                    // Enroque largo negras (O-O-O): rey e8→c8, torre a8→d8
                    if (castlingRights.bQ &&
                        boardState[0][3] === '' && boardState[0][2] === '' && boardState[0][1] === '' &&
                        boardState[0][0] === 'r' &&
                        !isSquareAttackedBy(boardState, 0, 4, true) &&
                        !isSquareAttackedBy(boardState, 0, 3, true) &&
                        !isSquareAttackedBy(boardState, 0, 2, true)) {
                        moves.push([0, 2]);
                    }
                }
            }
            break;
        }
    }

    return moves;
}

function applyMoveToBoard(boardState, fromR, fromC, toR, toC) {
    const newBoard = boardState.map(row => [...row]);
    let piece = newBoard[fromR][fromC];
    newBoard[toR][toC] = piece;
    newBoard[fromR][fromC] = '';
    // Promoción de peón
    if (piece === 'P' && toR === 0) newBoard[toR][toC] = 'Q';
    if (piece === 'p' && toR === 7) newBoard[toR][toC] = 'q';
    // Captura al paso: peón mueve en diagonal a casilla vacía
    if ((piece === 'P' || piece === 'p') && fromC !== toC && boardState[toR][toC] === '') {
        newBoard[fromR][toC] = ''; // eliminar el peón capturado (misma fila origen, columna destino)
    }
    // Enroque: mover la torre al otro lado del rey
    if (piece === 'K' && fromR === 7 && fromC === 4) {
        if (toC === 6) { newBoard[7][5] = 'R'; newBoard[7][7] = ''; } // O-O
        if (toC === 2) { newBoard[7][3] = 'R'; newBoard[7][0] = ''; } // O-O-O
    }
    if (piece === 'k' && fromR === 0 && fromC === 4) {
        if (toC === 6) { newBoard[0][5] = 'r'; newBoard[0][7] = ''; } // O-O
        if (toC === 2) { newBoard[0][3] = 'r'; newBoard[0][0] = ''; } // O-O-O
    }
    return newBoard;
}

function findKing(boardState, isWhite) {
    const king = isWhite ? 'K' : 'k';
    for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
            if (boardState[r][c] === king) return [r, c];
        }
    }
    return null;
}

function isSquareAttackedBy(boardState, r, c, byWhite) {
    for (let fr = 0; fr < 8; fr++) {
        for (let fc = 0; fc < 8; fc++) {
            const p = boardState[fr][fc];
            if (!p) continue;
            if (isWhitePiece(p) !== byWhite) continue;
            // forAttack=true: omite enroque para evitar recursión infinita
            const raw = getLegalMovesRaw(fr, fc, boardState, true);
            if (raw.some(([mr, mc]) => mr === r && mc === c)) return true;
        }
    }
    return false;
}

function isKingInCheck(boardState, isWhite) {
    const kingPos = findKing(boardState, isWhite);
    if (!kingPos) return false;
    return isSquareAttackedBy(boardState, kingPos[0], kingPos[1], !isWhite);
}

// Movimientos legales: filtrar los que dejan al propio rey en jaque
function getLegalMoves(r, c, boardState) {
    const piece = boardState[r][c];
    if (!piece) return [];
    const isWhite = isWhitePiece(piece);
    const raw = getLegalMovesRaw(r, c, boardState);
    return raw.filter(([tr, tc]) => {
        const newBoard = applyMoveToBoard(boardState, r, c, tr, tc);
        return !isKingInCheck(newBoard, isWhite);
    });
}

function hasAnyLegalMoves(boardState, isWhite) {
    for (let r = 0; r < 8; r++) {
        for (let c = 0; c < 8; c++) {
            const p = boardState[r][c];
            if (!p) continue;
            if (isWhitePiece(p) !== isWhite) continue;
            if (getLegalMoves(r, c, boardState).length > 0) return true;
        }
    }
    return false;
}

// --- Lógica del juego ---

function initBoard() {
    stopTimers();
    board = JSON.parse(JSON.stringify(INITIAL_LAYOUT));
    selectedSquare = null;
    legalMovesForSelected = [];
    moveHistory = [];
    currentTurn = 'white';
    gameResult = '*';
    gameStartDate = null;
    currentMoveNumber = 1;
    pendingWhiteMove = null;
    castlingRights = { wK: true, wQ: true, bK: true, bQ: true };
    enPassantTarget = null;
    gameOver = false;
    gameStarted = false;
    aiShouldMoveFirst = false;
    boardFlipped = false;
    document.getElementById('game-end-overlay').classList.add('hidden');
    updateTurnIndicator();
    renderBoard();
    updateHistoryUI();
}

function renderBoard() {
    boardElement.innerHTML = '';
    const legalSet = new Set(legalMovesForSelected.map(([r, c]) => `${r},${c}`));

    // Orden de filas y columnas según orientación
    const rowOrder = boardFlipped ? [7,6,5,4,3,2,1,0] : [0,1,2,3,4,5,6,7];
    const colOrder = boardFlipped ? [7,6,5,4,3,2,1,0] : [0,1,2,3,4,5,6,7];

    rowOrder.forEach((r, ri) => {
        colOrder.forEach((c, ci) => {
            const square = document.createElement('div');
            square.className = `square ${(r + c) % 2 === 0 ? 'white' : 'black'}`;
            square.dataset.row = r;
            square.dataset.col = c;

            const piece = board[r][c];
            if (piece) {
                const pieceEl = document.createElement('span');
                pieceEl.textContent = PIECES[piece] || '';
                square.appendChild(pieceEl);
            }

            if (selectedSquare && selectedSquare.r === r && selectedSquare.c === c) {
                square.style.backgroundColor = '#f1c40f';
            } else if (legalSet.has(`${r},${c}`)) {
                square.style.backgroundColor = piece ? '#e74c3c' : '#2ecc71';
            }

            // Etiqueta de número de fila (columna visual izquierda)
            if (ci === 0) {
                const lbl = document.createElement('span');
                lbl.className = 'coord-label coord-rank';
                lbl.textContent = String(8 - r);
                square.appendChild(lbl);
            }
            // Etiqueta de letra de columna (fila visual inferior)
            if (ri === 7) {
                const lbl = document.createElement('span');
                lbl.className = 'coord-label coord-file';
                lbl.textContent = 'abcdefgh'[c];
                square.appendChild(lbl);
            }

            square.onclick = () => handleSquareClick(r, c);
            boardElement.appendChild(square);
        });
    });
}

function handleSquareClick(r, c) {
    if (gameOver) return;
    if (!gameStarted) return;
    const clickedPiece = board[r][c];

    if (selectedSquare) {
        const { r: fromR, c: fromC } = selectedSquare;

        // Clic en la misma casilla: deseleccionar
        if (fromR === r && fromC === c) {
            selectedSquare = null;
            legalMovesForSelected = [];
            renderBoard();
            return;
        }

        // Clic en otra pieza propia: cambiar selección
        const isOwn = playerColor === 'white' ? isWhitePiece(clickedPiece) : isBlackPiece(clickedPiece);
        if (isOwn) {
            selectedSquare = { r, c };
            legalMovesForSelected = getLegalMoves(r, c, board);
            renderBoard();
            return;
        }

        // Intentar mover
        const isLegal = legalMovesForSelected.some(([lr, lc]) => lr === r && lc === c);
        if (isLegal) {
            executeMove(fromR, fromC, r, c);
        }

        selectedSquare = null;
        legalMovesForSelected = [];
    } else {
        if (!clickedPiece) return;
        const isOwn = playerColor === 'white' ? isWhitePiece(clickedPiece) : isBlackPiece(clickedPiece);
        if (!isOwn) return;

        selectedSquare = { r, c };
        legalMovesForSelected = getLegalMoves(r, c, board);
    }

    renderBoard();
}

function executeMove(fromR, fromC, toR, toC) {
    const colorThatJustMoved = currentTurn;
    const piece = board[fromR][fromC];
    const targetPiece = board[toR][toC];
    const isEnPassant = piece.toLowerCase() === 'p' && fromC !== toC && targetPiece === '';
    const isCapture = targetPiece !== '' || isEnPassant;

    // Actualizar derechos de enroque
    if (piece === 'K') { castlingRights.wK = false; castlingRights.wQ = false; }
    if (piece === 'k') { castlingRights.bK = false; castlingRights.bQ = false; }
    if (piece === 'R' && fromR === 7 && fromC === 7) castlingRights.wK = false;
    if (piece === 'R' && fromR === 7 && fromC === 0) castlingRights.wQ = false;
    if (piece === 'r' && fromR === 0 && fromC === 7) castlingRights.bK = false;
    if (piece === 'r' && fromR === 0 && fromC === 0) castlingRights.bQ = false;
    if (toR === 7 && toC === 7) castlingRights.wK = false;
    if (toR === 7 && toC === 0) castlingRights.wQ = false;
    if (toR === 0 && toC === 7) castlingRights.bK = false;
    if (toR === 0 && toC === 0) castlingRights.bQ = false;

    // Actualizar objetivo de captura al paso
    if (piece.toLowerCase() === 'p' && Math.abs(toR - fromR) === 2) {
        enPassantTarget = [(fromR + toR) / 2, fromC];
    } else {
        enPassantTarget = null;
    }

    board = applyMoveToBoard(board, fromR, fromC, toR, toC);

    // Detectar jaque / jaque mate al oponente para la notación
    const opponentIsWhite = (currentTurn !== 'white');
    const opponentInCheck = isKingInCheck(board, opponentIsWhite);
    const opponentHasMoves = hasAnyLegalMoves(board, opponentIsWhite);
    let suffix = '';
    if (opponentInCheck && !opponentHasMoves) suffix = '++';
    else if (opponentInCheck) suffix = '+';

    let notation = getMoveNotation(piece, fromR, fromC, toR, toC, isCapture) + suffix;

    if (currentTurn === 'white') {
        pendingWhiteMove = notation;
        currentTurn = 'black';
    } else {
        moveHistory.push({ num: currentMoveNumber, white: pendingWhiteMove, black: notation });
        currentMoveNumber++;
        pendingWhiteMove = null;
        currentTurn = 'white';
    }

    switchClock(colorThatJustMoved);
    updateHistoryUI();
    updateTurnIndicator();

    // Fin de partida
    if (!opponentHasMoves) {
        setTimeout(() => {
            if (opponentInCheck) {
                const winner = opponentIsWhite ? 'Las negras' : 'Las blancas';
                const pieceName = PIECE_NAME[piece] || 'Pieza';
                const square = getSquareName(toR, toC);
                const mateResult = winner === 'Las blancas' ? '1-0' : '0-1';
                showGameEnd('♟', `JAQUE MATE\n${pieceName} en ${square} da el golpe final.\n${winner} ganan.`, mateResult);
            } else {
                showGameEnd('🤝', 'TABLAS\nAhogado: el jugador no tiene movimientos legales.', '1/2-1/2');
            }
        }, 150);
    }
}

// --- Fin de partida y acciones del sidebar ---

function showGameEnd(icon, message, result = '*') {
    gameOver = true;
    gameResult = result;
    document.getElementById('game-end-icon').textContent = icon;
    document.getElementById('game-end-message').innerHTML = message.replace(/\n/g, '<br>');
    document.getElementById('game-end-overlay').classList.remove('hidden');
}

function handleResign() {
    if (gameOver) return;
    const resignColor = currentTurn === 'white' ? 'Las blancas' : 'Las negras';
    const winColor    = currentTurn === 'white' ? 'Las negras' : 'Las blancas';
    const resignResult = currentTurn === 'white' ? '0-1' : '1-0';
    showGameEnd('🏳️', `${resignColor} se rinden.\n${winColor} ganan.`, resignResult);
}

function handleDraw() {
    if (gameOver) return;
    showGameEnd('🤝', 'Tablas acordadas.\nLa partida termina en empate.', '1/2-1/2');
}

function saveGame() {
    const diffLabels = { easy:'Facil', medium:'Medio', hard:'Dificil', expert:'Experto', llm:'Claude AI' };
    const diffLabel  = diffLabels[difficulty] || difficulty;
    const isHumanWhite = (playerColor === 'white');
    const whitePlayer  = isHumanWhite ? 'Humano' : `IA (${diffLabel})`;
    const blackPlayer  = isHumanWhite ? `IA (${diffLabel})` : 'Humano';

    const d = gameStartDate || new Date();
    const dateStr = `${d.getFullYear()}.${String(d.getMonth()+1).padStart(2,'0')}.${String(d.getDate()).padStart(2,'0')}`;

    // Cabeceras PGN
    let pgn = `[Event "Partida Local"]\n`;
    pgn += `[Site "agenteIAlocal"]\n`;
    pgn += `[Date "${dateStr}"]\n`;
    pgn += `[White "${whitePlayer}"]\n`;
    pgn += `[Black "${blackPlayer}"]\n`;
    pgn += `[Result "${gameResult}"]\n\n`;

    // Movimientos
    const movePairs = moveHistory.map(({ num, white, black }) =>
        black ? `${num}. ${white} ${black}` : `${num}. ${white}`
    );
    if (pendingWhiteMove) movePairs.push(`${currentMoveNumber}. ${pendingWhiteMove}`);
    pgn += movePairs.join(' ');
    if (gameResult !== '*') pgn += ` ${gameResult}`;
    pgn += '\n';

    // Descargar
    const blob = new Blob([pgn], { type: 'text/plain' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `partida_${dateStr.replace(/\./g, '-')}.pgn`;
    a.click();
    URL.revokeObjectURL(url);
}

function updateTurnIndicator() {
    const el = document.getElementById('turn-indicator');
    if (!el) return;
    el.textContent = `Turno: ${currentTurn === 'white' ? 'Blancas' : 'Negras'}`;
    el.style.background = currentTurn === 'white' ? '#7f8c8d' : '#2c3e50';
}

function updateHistoryUI() {
    historyList.innerHTML = '';

    moveHistory.forEach(({ num, white, black }) => {
        const li = document.createElement('li');
        li.textContent = `${num}. ${white} — ${black}`;
        historyList.appendChild(li);
    });

    // Mostrar la jugada blanca pendiente mientras espera la respuesta negra
    if (pendingWhiteMove) {
        const li = document.createElement('li');
        li.textContent = `${currentMoveNumber}. ${pendingWhiteMove} — ...`;
        li.style.color = '#999';
        historyList.appendChild(li);
    }

    historyList.scrollTop = historyList.scrollHeight;
}

function resetGame() {
    initBoard();
    showLobby();
}

// --- Lobby ---
function selectLobbyOption(type, value, btn) {
    const groupId = { color: 'color-options', difficulty: 'difficulty-options', time: 'time-options' }[type];
    document.querySelectorAll(`#${groupId} .lobby-btn`).forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    if (type === 'color')      playerColor = value;
    if (type === 'difficulty') difficulty  = value;
    if (type === 'time')       gameTimeMinutes = parseInt(value);
}

function startGame() {
    document.getElementById('lobby-overlay').classList.add('hidden');
    gameStarted = true;
    aiShouldMoveFirst = (playerColor === 'black');
    boardFlipped = (playerColor === 'black'); // auto-girar si juegas con negras
    gameStartDate = new Date();
    startTimers();
    renderBoard();
}

function flipBoard() {
    boardFlipped = !boardFlipped;
    renderBoard();
}

function showLobby() {
    gameStarted = false;
    aiShouldMoveFirst = false;
    document.getElementById('lobby-overlay').classList.remove('hidden');
}

// --- Temporizador ---
function formatTime(ms) {
    if (ms <= 0) return '00:00';
    const totalSec = Math.ceil(ms / 1000);
    const m = Math.floor(totalSec / 60), s = totalSec % 60;
    return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}

function updateClockDisplay() {
    const wTime = document.getElementById('time-white');
    const bTime = document.getElementById('time-black');
    const wBox  = document.getElementById('clock-white');
    const bBox  = document.getElementById('clock-black');
    if (!wTime) return;
    wTime.textContent = formatTime(whiteTimeMs);
    bTime.textContent = formatTime(blackTimeMs);
    wBox.classList.toggle('active-clock', activeClockColor === 'white');
    bBox.classList.toggle('active-clock', activeClockColor === 'black');
    wBox.classList.toggle('urgent', whiteTimeMs > 0 && whiteTimeMs <= 30000);
    bBox.classList.toggle('urgent', blackTimeMs > 0 && blackTimeMs <= 30000);
}

function startTimers() {
    whiteTimeMs = blackTimeMs = gameTimeMinutes * 60 * 1000;
    activeClockColor = null;
    clocksStarted = false;
    updateClockDisplay();
}

function switchClock(colorThatJustMoved) {
    if (!clocksStarted) {
        clocksStarted = true;
        clockInterval = setInterval(tickClock, 100);
    }
    activeClockColor = (colorThatJustMoved === 'white') ? 'black' : 'white';
    updateClockDisplay();
}

function tickClock() {
    if (!activeClockColor || gameOver) return;
    if (activeClockColor === 'white') {
        whiteTimeMs -= 100;
        if (whiteTimeMs <= 0) {
            whiteTimeMs = 0; updateClockDisplay(); stopTimers();
            showGameEnd('⏰', 'TIEMPO AGOTADO\nLas negras ganan por tiempo.', '0-1');
            return;
        }
    } else {
        blackTimeMs -= 100;
        if (blackTimeMs <= 0) {
            blackTimeMs = 0; updateClockDisplay(); stopTimers();
            showGameEnd('⏰', 'TIEMPO AGOTADO\nLas blancas ganan por tiempo.', '1-0');
            return;
        }
    }
    updateClockDisplay();
}

function stopTimers() {
    clearInterval(clockInterval);
    clockInterval = null;
    activeClockColor = null;
}

initBoard();
showLobby();
