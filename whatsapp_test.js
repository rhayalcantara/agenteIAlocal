/**
 * WhatsApp Web.js — Test de conexion via QR
 * Escanea el QR con tu telefono para conectar.
 * Los mensajes del grupo aparecen en la terminal.
 */
const { Client, LocalAuth } = require('whatsapp-web.js');
const QRCode = require('qrcode');
const { exec } = require('child_process');
const path = require('path');

const QR_PATH = path.join(__dirname, 'whatsapp_qr.png');

const client = new Client({
    authStrategy: new LocalAuth({ dataPath: './.wwebjs_auth' }),
    puppeteer: {
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    }
});

// Guardar QR como imagen y abrir automaticamente
client.on('qr', async (qr) => {
    console.log('QR recibido, generando imagen...');
    await QRCode.toFile(QR_PATH, qr, { width: 400, margin: 2 });
    console.log(`QR guardado: ${QR_PATH}`);
    console.log('Abriendo imagen...');
    exec(`start "" "${QR_PATH}"`);
    console.log('=== ESCANEA EL QR QUE SE ABRIO EN PANTALLA ===');
});

client.on('ready', () => {
    console.log('=== WHATSAPP CONECTADO ===');
    console.log('Escuchando mensajes de todos los chats...');
});

client.on('authenticated', () => {
    console.log('Autenticado! Sesion guardada para proximas veces.');
});

client.on('auth_failure', (msg) => {
    console.error('Error de autenticacion:', msg);
});

// Escuchar mensajes entrantes
client.on('message', async (msg) => {
    const chat = await msg.getChat();
    const contact = await msg.getContact();
    const nombre = contact.pushname || contact.name || msg.from;
    const esGrupo = chat.isGroup;
    const grupo = esGrupo ? chat.name : 'DM';

    console.log(`[${grupo}] ${nombre}: ${msg.body.substring(0, 200)}`);

    // Si es un grupo, mostrar info extra
    if (esGrupo) {
        console.log(`  -> Grupo ID: ${chat.id._serialized}`);
    }
});

console.log('Iniciando WhatsApp Web...');
client.initialize();
