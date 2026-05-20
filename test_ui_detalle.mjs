import { chromium } from 'playwright';

const SHOT = 'C:/proyectos/agenteIAlocal/test_screenshots';
const fs = await import('node:fs'); fs.mkdirSync(SHOT, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await (await browser.newContext({ viewport: { width: 1400, height: 1000 } })).newPage();

async function dismiss() {
  const o = page.locator('.sidebar-overlay.active');
  if (await o.count()) { await o.first().click(); await page.waitForTimeout(300); }
}

async function shot(n) { await page.screenshot({ path: `${SHOT}/${n}.png`, fullPage: true }); }

try {
  await page.goto('http://localhost:4200', { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('input', { timeout: 15000 });
  await page.locator('input').nth(0).fill('admin');
  await page.locator('input[type="password"]').first().fill('RHoss.1234');
  await Promise.all([
    page.waitForURL(u => !u.toString().includes('/login'), { timeout: 20000 }),
    page.locator('button:has-text("Login")').first().click(),
  ]);
  await page.waitForLoadState('networkidle');

  await page.locator('a[href="/desc-cred-nomina"]').first().evaluate(a => a.click());
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(1000);
  await dismiss();
  await shot('D01_modulo_inicial');

  // Seleccionar nómina activa
  await page.locator('mat-select[formControlName="selectedNomina"]').evaluate(s => s.click());
  await page.waitForTimeout(400);
  await page.locator('mat-option').first().evaluate(o => o.click());
  await page.waitForTimeout(1500);
  await dismiss();
  await shot('D02_nomina_seleccionada');

  // Verificar que aparece el campo nuevo "Detalle"
  const detalleField = await page.locator('mat-form-field:has(input[formControlName="detalleConcepto"])').count();
  console.log('Campo "Detalle" presente:', detalleField > 0 ? 'SÍ ✓' : 'NO ✗');

  // Verificar columna nueva en tabla
  const headers = await page.locator('table thead th').allInnerTexts();
  console.log('Headers tabla:', headers);
  const hasDetalle = headers.some(h => /detalle/i.test(h));
  console.log('Columna "Detalle" en tabla:', hasDetalle ? 'SÍ ✓' : 'NO ✗');

  // Tomar screenshot enfocado en el formulario
  await page.locator('input[formControlName="detalleConcepto"]').first().evaluate(i => i.scrollIntoView());
  await page.waitForTimeout(300);
  await shot('D03_form_con_detalle');

  await browser.close();
  console.log('\n=== VERIFICACIÓN UI ===');
  console.log(detalleField > 0 && hasDetalle ? '✓ PASSED' : '✗ FAILED');
  process.exit((detalleField > 0 && hasDetalle) ? 0 : 1);
} catch (err) {
  console.error('FATAL:', err.message);
  try { await shot('D99_fatal'); } catch (_) {}
  await browser.close();
  process.exit(2);
}
