import { chromium } from 'playwright';

const FRONTEND = 'http://localhost:4200';
const USER = 'admin';
const PASS = 'RHoss.1234';
const SHOT_DIR = 'C:/proyectos/agenteIAlocal/test_screenshots';

const fs = await import('node:fs');
fs.mkdirSync(SHOT_DIR, { recursive: true });

const browser = await chromium.launch({ headless: true });
const ctx = await browser.newContext({ viewport: { width: 1400, height: 900 } });
const page = await ctx.newPage();

const errors = [];
page.on('pageerror', e => errors.push(`pageerror: ${e.message}`));
page.on('console', m => { if (m.type() === 'error') errors.push(`console: ${m.text()}`); });

async function shot(name) {
  await page.screenshot({ path: `${SHOT_DIR}/${name}.png`, fullPage: true });
  console.log(`  shot: ${name}  (url=${page.url()})`);
}

async function dismissSidebar() {
  const overlay = page.locator('.sidebar-overlay.active');
  if (await overlay.count() > 0) {
    await overlay.first().click();
    await page.waitForTimeout(300);
  }
}

const results = {};

try {
  // LOGIN
  console.log('[LOGIN]');
  await page.goto(FRONTEND, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('input', { timeout: 15000 });
  await page.locator('input').nth(0).fill(USER);
  await page.locator('input[type="password"]').first().fill(PASS);
  await Promise.all([
    page.waitForURL(u => !u.toString().includes('/login'), { timeout: 20000 }),
    page.locator('button:has-text("Login")').first().click(),
  ]);
  await page.waitForLoadState('networkidle');
  await shot('A01_dashboard');

  // === MÓDULO 1: employee-form (lo que toqué) ===
  console.log('\n[MOD1] employee-form Ingresos/Descuentos Fijos');
  // Ir a Empleados via click directo en sidebar (page.goto puede ser bloqueado por guard timing)
  await page.locator('a[href="/employees"]').first().click();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(500);
  await page.waitForSelector('table tbody tr', { timeout: 10000 });
  await shot('B01_employees_list');

  // Dump structure of first row to find correct selectors
  const firstRowInfo = await page.locator('table tbody tr').first().evaluate(tr => {
    const buttons = tr.querySelectorAll('button');
    return Array.from(buttons).map(b => ({
      text: b.textContent?.trim() || '',
      title: b.getAttribute('title') || '',
      aria: b.getAttribute('aria-label') || '',
      class: b.className,
      icons: Array.from(b.querySelectorAll('mat-icon')).map(i => i.textContent?.trim()),
    }));
  });
  console.log('  first row buttons:', JSON.stringify(firstRowInfo, null, 2));

  await dismissSidebar();
  // Click el botón "Edit" en la primera fila
  await page.locator('table tbody tr').first().locator('button:has-text("Edit")').click();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(500);
  await dismissSidebar();
  await shot('B02_employee_edit');

  // Click tab "Ingresos/Descuentos Fijos" — programmatic click to bypass any overlay
  await page.locator('button.tab-button:has-text("Ingresos")').evaluate(b => b.click());
  await page.waitForTimeout(500);
  await shot('B03_tab_ingresos');

  // Click "Añadir Ingreso/Descuento" — programmatic
  await page.locator('button:has-text("Añadir Ingreso")').first().evaluate(b => b.click());
  await page.waitForSelector('mat-dialog-container, [role="dialog"]', { timeout: 5000 });
  await page.waitForTimeout(800);
  await shot('B04_dialog_open');

  const dialogText = await page.locator('mat-dialog-container, [role="dialog"]').first().innerText();
  console.log('  --- Dialog text (first 1200 chars) ---');
  console.log(dialogText.substring(0, 1200));

  const upper = dialogText.toUpperCase();
  results['MOD1 employee-form'] = {
    'COMIDA presente': upper.includes('COMIDA'),
    'CARNET presente': upper.includes('CARNET'),
    'SEGURO presente': upper.includes('SEGURO'),
    'UNIFORME presente': upper.includes('UNIFORME'),
    'AFP ausente (no debe aparecer)': !/\bAFP\b/.test(upper),
    'SFS ausente (no debe aparecer)': !/\bSFS\b/.test(upper),
  };

  // Cerrar dialog
  await page.keyboard.press('Escape');
  await page.waitForTimeout(300);

  // === MÓDULO 2: desc-cred-nomina (Ingresos/Descuentos Manuales del sidebar) ===
  console.log('\n[MOD2] /desc-cred-nomina Ingresos/Descuentos Manuales');
  await page.locator('a[href="/desc-cred-nomina"]').first().evaluate(a => a.click());
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(800);
  await dismissSidebar();
  await shot('C01_desc_cred_nomina');

  // Seleccionar una nómina del primer dropdown (programmatic)
  await page.locator('mat-select[formControlName="selectedNomina"]').evaluate(s => s.click());
  await page.waitForTimeout(500);
  await shot('C02_nomina_dropdown');
  await page.locator('mat-option').first().evaluate(o => o.click());
  await page.waitForTimeout(1500);
  await shot('C03_after_nomina_select');

  // Abrir el dropdown de "Ingreso/Descuento"
  const descCredSelect = page.locator('mat-select[formControlName="selectedDescCred"]');
  if (await descCredSelect.count() > 0) {
    await descCredSelect.evaluate(s => s.click());
    await page.waitForTimeout(500);
    await shot('C04_descCred_dropdown_open');
    // Capturar las opciones visibles
    const opts = await page.locator('mat-option').allInnerTexts();
    console.log('  --- mat-options visibles ---');
    console.log(opts.slice(0, 50).join('\n'));
    const upperOpts = opts.join(' ').toUpperCase();
    results['MOD2 desc-cred-nomina'] = {
      'COMIDA presente': upperOpts.includes('COMIDA'),
      'CARNET presente': upperOpts.includes('CARNET'),
      'AFP ausente (no debe aparecer)': !/\bAFP\b/.test(upperOpts),
      'SFS ausente (no debe aparecer)': !/\bSFS\b/.test(upperOpts),
      'Vacaciones ausente (no debe aparecer)': !upperOpts.includes('VACACIONES'),
      'Total opciones': opts.length,
    };
    await page.keyboard.press('Escape');
  } else {
    console.log('  WARN: dropdown selectedDescCred no encontrado en esta página');
    results['MOD2 desc-cred-nomina'] = { error: 'dropdown no encontrado' };
  }

  // === MÓDULO 3: Test del backend con POST inválido (intentar asignar AFP manualmente) ===
  console.log('\n[MOD3] Validación backend POST con id_desc_cred fijo');
  // Obtener token desde localStorage
  const token = await page.evaluate(() => {
    return localStorage.getItem('token') || sessionStorage.getItem('token');
  });
  console.log('  token presente:', token ? 'sí' : 'no');

  if (token) {
    // Buscar id de AFP
    const afpRes = await page.evaluate(async (tk) => {
      const r = await fetch('http://localhost:3333/api/no_desc_cred/selector', {
        headers: { 'Authorization': tk }
      });
      const data = await r.json();
      const afp = data.find(d => /^AFP$/i.test(d.descripcion));
      return afp;
    }, token);
    console.log('  AFP encontrado:', JSON.stringify(afpRes));

    if (afpRes) {
      // Intentar POST a /api/desc-cred-nomina con id_desc_cred = AFP
      const postRes = await page.evaluate(async (tk, idAfp) => {
        const r = await fetch('http://localhost:3333/api/desc-cred-nomina', {
          method: 'POST',
          headers: { 'Authorization': tk, 'Content-Type': 'application/json' },
          body: JSON.stringify({
            empleados: [27],
            id_nomina: 1,
            id_desc_cred: idAfp,
            valor: 100,
            fecha: '2026-05-13'
          })
        });
        return { status: r.status, body: await r.json() };
      }, token, afpRes.id_desc_cred);
      console.log('  POST AFP manual response:', JSON.stringify(postRes));
      results['MOD3 backend validation'] = {
        'POST con AFP rechazado (400)': postRes.status === 400,
        'Mensaje incluye "fijo" o "automáticamente"': /autom[aá]ticamente|fijo/i.test(JSON.stringify(postRes.body)),
        'Response status': postRes.status,
      };
    }
  }

  // REPORTE
  console.log('\n=== RESULTADOS ===');
  for (const [mod, checks] of Object.entries(results)) {
    console.log(`\n${mod}:`);
    for (const [k, v] of Object.entries(checks)) {
      const isBoolean = typeof v === 'boolean';
      console.log(`  ${isBoolean ? (v ? '✓' : '✗') : '·'} ${k}: ${v}`);
    }
  }

  if (errors.length) {
    console.log('\n--- BROWSER ERRORS ---');
    errors.slice(0, 20).forEach(e => console.log(e));
  }

  process.exit(0);

} catch (err) {
  console.error('FATAL:', err.message);
  try { await shot('99_fatal'); } catch (_) {}
  if (errors.length) errors.slice(0, 10).forEach(e => console.log(e));
  process.exit(2);
} finally {
  await browser.close();
}
