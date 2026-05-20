#!/bin/bash
# Auto Deploy — Polling de git cada 30s
# Cuando detecta commits nuevos en main, ejecuta pull + build + reporta por Telegram
#
# Uso: bash auto_deploy.sh
# Detener: Ctrl+C o kill $(cat /tmp/auto_deploy.pid)

# Configuracion
REPO_DIR="${REPO_DIR:-$(pwd)}"
BRANCH="${BRANCH:-main}"
POLL_INTERVAL=30
RANGER_BOT_TOKEN="${RANGER_TELEGRAM_TOKEN:-8728278032:AAF9C-pPkQJ2ZCqXcF2JUO3lFQn0fxFvZSU}"
CLAUDY_BOT_TOKEN="${CLAUDY_TELEGRAM_TOKEN:-}"
GRUPO_ID="${TELEGRAM_GRUPO_ID:--5199025483}"

# Guardar PID
echo $$ > /tmp/auto_deploy.pid

# Funcion para enviar por Telegram
enviar_telegram() {
    local texto="$1"
    # Enviar por bot Ranger
    curl -s -X POST "https://api.telegram.org/bot${RANGER_BOT_TOKEN}/sendMessage" \
        -H "Content-Type: application/json" \
        -d "{\"chat_id\": ${GRUPO_ID}, \"text\": \"${texto}\"}" > /dev/null 2>&1
    # Enviar por bot Claudy (si tiene token)
    if [ -n "$CLAUDY_BOT_TOKEN" ]; then
        curl -s -X POST "https://api.telegram.org/bot${CLAUDY_BOT_TOKEN}/sendMessage" \
            -H "Content-Type: application/json" \
            -d "{\"chat_id\": ${GRUPO_ID}, \"text\": \"${texto}\"}" > /dev/null 2>&1
    fi
}

# Funcion de deploy
do_deploy() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] Nuevos commits detectados. Iniciando deploy..."
    enviar_telegram "🔄 [$timestamp] Nuevos commits detectados en ${BRANCH}. Iniciando deploy..."

    # Git pull
    cd "$REPO_DIR"
    PULL_OUTPUT=$(git pull origin "$BRANCH" 2>&1)
    PULL_EXIT=$?

    if [ $PULL_EXIT -ne 0 ]; then
        echo "ERROR: git pull fallo"
        echo "$PULL_OUTPUT"
        enviar_telegram "❌ Error en git pull:\\n${PULL_OUTPUT}"
        return 1
    fi

    # Archivos cambiados
    CHANGED=$(echo "$PULL_OUTPUT" | grep -E "^\s" | head -10)
    echo "Archivos cambiados:"
    echo "$CHANGED"

    # Build frontend (ajustar segun tu proyecto)
    if [ -f "package.json" ]; then
        echo "Ejecutando npm install..."
        npm install --production 2>&1 | tail -3

        if grep -q '"build"' package.json; then
            echo "Ejecutando npm run build..."
            BUILD_OUTPUT=$(npm run build 2>&1)
            BUILD_EXIT=$?

            if [ $BUILD_EXIT -ne 0 ]; then
                enviar_telegram "❌ Error en build:\\n$(echo "$BUILD_OUTPUT" | tail -5)"
                return 1
            fi
        fi
    fi

    # Si hay requirements.txt (Python)
    if [ -f "requirements.txt" ]; then
        echo "Instalando dependencias Python..."
        pip3 install -r requirements.txt -q 2>&1 | tail -3
    fi

    enviar_telegram "✅ Deploy exitoso en ${BRANCH}\\n📦 ${PULL_OUTPUT}"
    echo "Deploy completado!"
    return 0
}

# Main loop
echo "=== Auto Deploy ==="
echo "Repo: $REPO_DIR"
echo "Rama: $BRANCH"
echo "Intervalo: ${POLL_INTERVAL}s"
echo "Grupo Telegram: $GRUPO_ID"
echo "Vigilando..."

cd "$REPO_DIR"
LAST_HASH=$(git rev-parse HEAD 2>/dev/null)
enviar_telegram "🟢 Auto Deploy iniciado. Vigilando rama ${BRANCH} cada ${POLL_INTERVAL}s"

while true; do
    sleep $POLL_INTERVAL

    cd "$REPO_DIR"

    # Fetch sin merge
    git fetch origin "$BRANCH" 2>/dev/null

    # Comparar hash local vs remoto
    LOCAL_HASH=$(git rev-parse HEAD 2>/dev/null)
    REMOTE_HASH=$(git rev-parse "origin/${BRANCH}" 2>/dev/null)

    if [ "$LOCAL_HASH" != "$REMOTE_HASH" ] && [ -n "$REMOTE_HASH" ]; then
        do_deploy
        LAST_HASH=$(git rev-parse HEAD 2>/dev/null)
    fi
done
