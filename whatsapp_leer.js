/**
 * WhatsApp — Leer historial de mensajes de un chat o grupo.
 *
 * Uso:
 *   node whatsapp_leer.js "SISTEMA RAY" 20
 *   node whatsapp_leer.js "nombre del grupo" [cantidad]
 */
const { Client, LocalAuth } = require('whatsapp-web.js');
const QRCode = require('qrcode');
const { exec } = require('child_process');
const path = require('path');

// Soporta: node whatsapp_leer.js "SISTEMA RAY" 20
//      o: node whatsapp_leer.js SISTEMA RAY 20 (sin comillas)
const args = process.argv.slice(2);
let LIMITE = 20;
let BUSCAR = 'SISTEMA RAY';

// El ultimo argumento numerico es el limite
if (args.length > 0 && /^\d+$/.test(args[args.length - 1])) {
    LIMITE = parseInt(args.pop());
}
// El resto es el nombre del chat
if (args.length > 0) {
    BUSCAR = args.join(' ');
}
const QR_PATH = path.join(__dirname, 'whatsapp_qr.png');

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
    console.log('=== ESCANEA EL QR ===');
});

client.on('authenticated', () => {
    console.log('Autenticado.');
});

client.on('ready', async () => {
    console.log('WhatsApp listo. Buscando chat: "' + BUSCAR + '"...');

    try {
        // Buscar el chat por nombre
        const chats = await client.getChats();
        const chat = chats.find(c =>
            c.name && c.name.toLowerCase().includes(BUSCAR.toLowerCase())
        );

        if (!chat) {
            console.log(`Chat "${BUSCAR}" no encontrado.`);
            console.log('Chats disponibles:');
            chats.filter(c => c.name).slice(0, 30).forEach(c => {
                const tipo = c.isGroup ? 'Grupo' : 'DM';
                console.log(`  [${tipo}] ${c.name} (${c.id._serialized})`);
            });
            await client.destroy();
            process.exit(0);
        }

        console.log(`Chat encontrado: "${chat.name}" (${chat.isGroup ? 'Grupo' : 'DM'})`);
        console.log(`ID: ${chat.id._serialized}`);
        console.log(`Leyendo ultimos ${LIMITE} mensajes...\n`);

        // Leer mensajes
        const messages = await chat.fetchMessages({ limit: LIMITE });

        for (const msg of messages) {
            const fecha = new Date(msg.timestamp * 1000);
            const hora = fecha.toLocaleString('es-DO', {
                day: '2-digit', month: '2-digit',
                hour: '2-digit', minute: '2-digit'
            });

            let autor = 'Desconocido';
            try {
                const contact = await msg.getContact();
                autor = contact.pushname || contact.name || msg.author || msg.from;
            } catch {
                autor = msg.author || msg.from;
            }

            const tipo = msg.hasMedia ? ' [MEDIA]' : '';
            const cuerpo = msg.body ? msg.body.substring(0, 300) : '(sin texto)';

            console.log(`[${hora}] ${autor}${tipo}: ${cuerpo}`);
        }

        console.log(`\n=== ${messages.length} mensajes leidos de "${chat.name}" ===`);
    } catch (e) {
        console.error('Error:', e.message);
    }

    await client.destroy();
    process.exit(0);
});

console.log('Conectando a WhatsApp...');
client.initialize();
