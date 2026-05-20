/**
 * WhatsApp — Leer historial y descargar media de un chat.
 *
 * Uso:
 *   node whatsapp_leer_media.js "SISTEMA RAY" 5
 */
const { Client, LocalAuth } = require('whatsapp-web.js');
const fs = require('fs');
const path = require('path');

const args = process.argv.slice(2);
let LIMITE = 5;
let BUSCAR = 'SISTEMA RAY';
if (args.length > 0 && /^\d+$/.test(args[args.length - 1])) {
    LIMITE = parseInt(args.pop());
}
if (args.length > 0) {
    BUSCAR = args.join(' ');
}

const MEDIA_DIR = path.join(__dirname, 'whatsapp_media');
if (!fs.existsSync(MEDIA_DIR)) fs.mkdirSync(MEDIA_DIR, { recursive: true });

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './.wwebjs_auth' }),
    puppeteer: { headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox'] }
});

client.on('ready', async () => {
    console.log('READY. Buscando "' + BUSCAR + '"...');
    try {
        const chats = await client.getChats();
        const chat = chats.find(c => c.name && c.name.toLowerCase().includes(BUSCAR.toLowerCase()));
        if (!chat) {
            console.log('Chat no encontrado.');
            await client.destroy();
            process.exit(1);
        }
        console.log('Chat: ' + chat.name + ' (' + chat.id._serialized + ')');
        const messages = await chat.fetchMessages({ limit: LIMITE });

        for (const msg of messages) {
            const fecha = new Date(msg.timestamp * 1000).toISOString();
            let autor = msg.author || msg.from;
            try {
                const contact = await msg.getContact();
                autor = contact.pushname || contact.name || autor;
            } catch {}

            if (msg.hasMedia) {
                try {
                    const media = await msg.downloadMedia();
                    if (!media) {
                        console.log('[' + fecha + '] ' + autor + ' [MEDIA-FAILED] mimetype=' + (msg.type || '?'));
                        continue;
                    }
                    const ext = (media.mimetype || '').split('/').pop().split(';')[0] || 'bin';
                    const safeTs = fecha.replace(/[:.]/g, '-');
                    const filename = `${safeTs}_${autor.replace(/[^a-zA-Z0-9]/g, '_').substring(0, 30)}.${ext}`;
                    const fullPath = path.join(MEDIA_DIR, filename);
                    fs.writeFileSync(fullPath, Buffer.from(media.data, 'base64'));
                    const sizeKB = Math.round(fs.statSync(fullPath).size / 1024);
                    const caption = msg.body ? ' caption="' + msg.body.substring(0, 200) + '"' : '';
                    console.log('[' + fecha + '] ' + autor + ' [MEDIA] type=' + msg.type + ' mime=' + media.mimetype + ' size=' + sizeKB + 'KB file=' + fullPath + caption);
                } catch (e) {
                    console.log('[' + fecha + '] ' + autor + ' [MEDIA-ERROR] ' + e.message);
                }
            } else {
                const cuerpo = msg.body ? msg.body.substring(0, 300) : '(sin texto)';
                console.log('[' + fecha + '] ' + autor + ': ' + cuerpo);
            }
        }
        console.log('=== ' + messages.length + ' mensajes procesados ===');
    } catch (e) {
        console.error('Error:', e.message);
    }
    await client.destroy();
    process.exit(0);
});

client.on('qr', () => { console.log('QR_NEEDED (sesion expirada)'); process.exit(2); });
console.log('Conectando...');
client.initialize();
