// Test: crear descuento manual con campo "detalle" (texto libre)
// y verificar que se guarda y se devuelve en el GET.

const API = 'http://localhost:3333';

async function login() {
  const r = await fetch(`${API}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: 'RHoss.1234' })
  });
  return (await r.json()).token;
}

const token = await login();
console.log('  login OK');

// Obtener una nómina activa
const nominasRes = await fetch(`${API}/api/no_nomina/activas`, {
  headers: { 'Authorization': token }
}).then(r => r.json()).catch(() => null);

// Probamos con id_nomina = 1 (la que sabemos que existe)
const id_nomina = 1;

// Obtener id de COMIDA
const dc = await fetch(`${API}/api/no_desc_cred/selector`, {
  headers: { 'Authorization': token }
}).then(r => r.json());
const comida = dc.find(d => /^COMIDA$/i.test(d.descripcion?.trim()));
console.log('  COMIDA id:', comida.id_desc_cred);

// --- Test 1: POST con descripcion ---
console.log('\n--- Test 1: POST con descripcion (detalle libre) ---');
const detalleTexto = `TEST_${Date.now()} - Comida del 03/05 — texto libre`;
const postRes = await fetch(`${API}/api/desc_cred_nomina`, {
  method: 'POST',
  headers: { 'Authorization': token, 'Content-Type': 'application/json' },
  body: JSON.stringify({
    empleados: [27],
    id_nomina,
    id_desc_cred: comida.id_desc_cred,
    valor: 250,
    fecha: '2026-05-13',
    descripcion: detalleTexto
  })
});
const postBody = await postRes.json();
console.log(`  status=${postRes.status}`);
console.log(`  body.data[0]:`, JSON.stringify(postBody.data?.[0]));
const created = postBody.data?.[0];
const idCreated = created?.id;
const detalleEnRespuesta = created?.descripcion;
const test1Pass = postRes.status === 201 && detalleEnRespuesta === detalleTexto;
console.log(`  ${test1Pass ? 'PASS' : 'FAIL'}: POST devuelve descripcion`);

// --- Test 2: GET /:nominaId verifica que detalle aparece ---
console.log('\n--- Test 2: GET registros incluyen "detalle" ---');
const getRes = await fetch(`${API}/api/desc_cred_nomina/${id_nomina}?page=1&limit=50&searchTerm=`, {
  headers: { 'Authorization': token }
}).then(r => r.json());
const found = getRes.detalles?.find(d => d.id === idCreated);
console.log(`  encontrado:`, JSON.stringify(found));
const test2Pass = found?.detalle === detalleTexto;
console.log(`  ${test2Pass ? 'PASS' : 'FAIL'}: GET devuelve campo detalle="${detalleTexto}"`);

// --- Test 3: PUT actualiza descripcion ---
console.log('\n--- Test 3: PUT actualiza descripcion ---');
const nuevoDetalle = `${detalleTexto} (ACTUALIZADO)`;
const putRes = await fetch(`${API}/api/desc_cred_nomina/${idCreated}`, {
  method: 'PUT',
  headers: { 'Authorization': token, 'Content-Type': 'application/json' },
  body: JSON.stringify({
    valor: 250,
    fecha: '2026-05-13',
    id_desc_cred: comida.id_desc_cred,
    descripcion: nuevoDetalle
  })
});
console.log(`  status=${putRes.status} body=${JSON.stringify(await putRes.json())}`);

// Re-GET para confirmar
const getRes2 = await fetch(`${API}/api/desc_cred_nomina/${id_nomina}?page=1&limit=50&searchTerm=`, {
  headers: { 'Authorization': token }
}).then(r => r.json());
const found2 = getRes2.detalles?.find(d => d.id === idCreated);
const test3Pass = found2?.detalle === nuevoDetalle;
console.log(`  ${test3Pass ? 'PASS' : 'FAIL'}: PUT persiste descripcion = "${nuevoDetalle}"`);

// --- Cleanup ---
console.log('\n--- Cleanup ---');
const delRes = await fetch(`${API}/api/desc_cred_nomina/${idCreated}`, {
  method: 'DELETE',
  headers: { 'Authorization': token }
});
console.log(`  DELETE status=${delRes.status}`);

console.log('\n=== RESUMEN ===');
console.log(`  Test 1 (POST guarda descripcion): ${test1Pass ? 'PASS' : 'FAIL'}`);
console.log(`  Test 2 (GET devuelve detalle):    ${test2Pass ? 'PASS' : 'FAIL'}`);
console.log(`  Test 3 (PUT actualiza):           ${test3Pass ? 'PASS' : 'FAIL'}`);
const allPass = test1Pass && test2Pass && test3Pass;
console.log(`\n=== ${allPass ? 'TEST PASSED' : 'TEST FAILED'} ===`);
process.exit(allPass ? 0 : 1);
