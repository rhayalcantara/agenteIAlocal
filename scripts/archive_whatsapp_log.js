/**
 * archive_whatsapp_log.js
 *
 * Toma snapshot gzip de los logs WhatsApp del día y los guarda en
 *   whatsapp_archive/YYYY-MM-DD/<nombre>.gz
 *
 * - NO trunca los logs originales (append-only continúa intacto).
 * - Idempotente: si la carpeta del día existe, sobrescribe los .gz.
 * - Imprime una línea JSON con el resumen al final.
 *
 * Uso: node scripts/archive_whatsapp_log.js
 */
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const ROOT = path.resolve(__dirname, '..');
const SOURCES = [
    path.join(ROOT, 'whatsapp_monitor.log'),
    path.join(ROOT, 'whatsapp_enviados.log'),
];

function todayStamp() {
    const d = new Date();
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
}

function gzipFileSync(src, dest) {
    const data = fs.readFileSync(src);
    const gz = zlib.gzipSync(data, { level: 9 });
    fs.writeFileSync(dest, gz);
    return gz.length;
}

function main() {
    const date = todayStamp();
    const outDir = path.join(ROOT, 'whatsapp_archive', date);
    fs.mkdirSync(outDir, { recursive: true });

    const files = [];
    for (const src of SOURCES) {
        const base = path.basename(src);
        if (!fs.existsSync(src)) {
            files.push({ name: base + '.gz', size: 0, skipped: 'source_missing' });
            continue;
        }
        const dest = path.join(outDir, base + '.gz');
        try {
            const size = gzipFileSync(src, dest);
            files.push({ name: base + '.gz', size });
        } catch (e) {
            files.push({ name: base + '.gz', size: 0, error: (e && e.message) || String(e) });
        }
    }

    const summary = { date, dir: outDir.replace(/\\/g, '/'), files };
    process.stdout.write(JSON.stringify(summary) + '\n');
}

main();
