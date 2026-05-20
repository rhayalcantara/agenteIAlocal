/**
 * WhatsApp Monitor persistente — escribe mensajes nuevos a un archivo JSON.
 * El plugin Python del Monitor Hub lee este archivo para detectar actividad.
 */
const { Client, LocalAuth, MessageMedia } = require('whatsapp-web.js');
const QRCode = require('qrcode');
const { exec } = require('child_process');
const fs = require('fs');
const path = require('path');

const QR_PATH = path.join(__dirname, 'whatsapp_qr.png');
const OUTPUT_FILE = path.join(__dirname, 'whatsapp_nuevos.json');
const QUEUE_FILE = path.join(__dirname, 'whatsapp_enviar.json');
const SENT_LOG = path.join(__dirname, 'whatsapp_enviados.log');
const MONITOR_LOG = path.join(__dirname, 'whatsapp_monitor.log');  // append-only log de MSG|...
const WATCH_GROUPS = process.argv.slice(2);  // grupos a vigilar (opcional)
const QUEUE_POLL_MS = 2000;

// Inicializar archivos
if (!fs.existsSync(OUTPUT_FILE)) {
    fs.writeFileSync(OUTPUT_FILE, '[]', 'utf-8');
}
if (!fs.existsSync(QUEUE_FILE)) {
    fs.writeFileSync(QUEUE_FILE, '[]', 'utf-8');
}

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './.wwebjs_auth' }),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

client.on('qr', async (qr) => {
    console.log('QR recibido, generando imagen...');
    await QRCode.toFile(QR_PATH, qr, { width: 400, margin: 2 });
    exec(`start "" "${QR_PATH}"`);
    console.log('ESCANEA_QR');
});

client.on('authenticated', () => console.log('AUTHENTICATED'));
client.on('auth_failure', (msg) => console.log('AUTH_FAILED|' + msg));

client.on('ready', () => {
    console.log('WHATSAPP_READY');
    // Arranca el procesador de cola de envío.
    setInterval(procesarColaEnvio, QUEUE_POLL_MS);
});

let _enviando = false;
async function procesarColaEnvio() {
    if (_enviando) return;
    let pendientes = [];
    try {
        pendientes = JSON.parse(fs.readFileSync(QUEUE_FILE, 'utf-8'));
    } catch (e) { return; }
    if (!Array.isArray(pendientes) || pendientes.length === 0) return;

    _enviando = true;
    const restantes = [];
    for (const item of pendientes) {
        try {
            if (!item || !item.chat_id) continue;
            if (item.media_path) {
                // Envío con media (foto, doc, etc.). 'texto' es el caption opcional.
                if (!fs.existsSync(item.media_path)) {
                    throw new Error('media_path no existe: ' + item.media_path);
                }
                const media = MessageMedia.fromFilePath(item.media_path);
                const opts = item.texto ? { caption: item.texto } : {};
                await client.sendMessage(item.chat_id, media, opts);
                const tag = `MEDIA(${path.basename(item.media_path)})`;
                const linea = `${new Date().toISOString()}|OK|${item.chat_id}|${tag} ${(item.texto || '').substring(0,80)}\n`;
                fs.appendFileSync(SENT_LOG, linea, 'utf-8');
                console.log(`SENT|${item.chat_id}|${tag}`);
            } else if (item.texto) {
                await client.sendMessage(item.chat_id, item.texto);
                const linea = `${new Date().toISOString()}|OK|${item.chat_id}|${item.texto.substring(0,120)}\n`;
                fs.appendFileSync(SENT_LOG, linea, 'utf-8');
                console.log(`SENT|${item.chat_id}|${item.texto.substring(0,60)}`);
            } else {
                continue;
            }
        } catch (e) {
            const linea = `${new Date().toISOString()}|FAIL|${item.chat_id}|${(e && e.message) || e}\n`;
            fs.appendFileSync(SENT_LOG, linea, 'utf-8');
            console.log(`SEND_FAILED|${item.chat_id}|${(e && e.message) || e}`);
            // Reintento futuro: encolar de nuevo solo si fue error transitorio.
            // Política conservadora: descartar para no enviar duplicados.
        }
    }
    // Vaciar cola tras procesarla (sin importar éxito por mensaje)
    fs.writeFileSync(QUEUE_FILE, JSON.stringify(restantes, null, 2), 'utf-8');
    _enviando = false;
}

client.on('message', async (msg) => {
    try {
        const chat = await msg.getChat();
        const contact = await msg.getContact();
        const nombre = contact.pushname || contact.name || msg.from;
        const esGrupo = chat.isGroup;
        const grupo = esGrupo ? chat.name : 'DM';

        // Ignorar estados (status broadcast)
        if (msg.from === 'status@broadcast') return;

        const entry = {
            timestamp: new Date().toISOString(),
            channel: 'whatsapp',
            chat_id: chat.id._serialized,
            chat_name: grupo,
            user: nombre,
            text: (msg.body || '').substring(0, 5000),
            type: msg.hasMedia ? 'media' : 'text',
            is_group: esGrupo
        };

        // Escribir al archivo JSON (append)
        let data = [];
        try {
            data = JSON.parse(fs.readFileSync(OUTPUT_FILE, 'utf-8'));
        } catch (e) { data = []; }
        data.push(entry);
        // Mantener solo ultimos 100 mensajes
        if (data.length > 100) data = data.slice(-50);
        fs.writeFileSync(OUTPUT_FILE, JSON.stringify(data, null, 2), 'utf-8');

        // Tambien imprimir para stdout
        const msgLine = `MSG|${entry.chat_name}|${entry.user}|${entry.text.substring(0, 100)}`;
        console.log(msgLine);
        // Append directo al log persistente (no depende del redirect del shell)
        try {
            fs.appendFileSync(MONITOR_LOG, msgLine + '\n', 'utf-8');
        } catch (logErr) {
            // No abortar el handler por un fallo de escritura de log
        }
    } catch (e) {
        // Silenciar errores de mensajes individuales
    }
});

console.log('STARTING');
client.initialize();
