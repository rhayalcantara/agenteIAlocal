// Test directo: backend /api/desc_cred_nomina debe rechazar id_desc_cred fijo.

const API = 'http://localhost:3333';

async function login() {
  const r = await fetch(`${API}/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username: 'admin', password: 'RHoss.1234' })
  });
  const data = await r.json();
  if (!data.token) throw new Error('Login failed: ' + JSON.stringify(data));
  console.log('  login OK');
  return data.token;
}

async function getDescCreds(token) {
  const r = await fetch(`${API}/api/no_desc_cred/selector`, {
    headers: { 'Authorization': token }
  });
  return r.json();
}

async function postDescCredNomina(token, id_desc_cred) {
  const r = await fetch(`${API}/api/desc_cred_nomina`, {
    method: 'POST',
    headers: { 'Authorization': token, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      empleados: [27],
      id_nomina: 1,
      id_desc_cred,
      valor: 100,
      fecha: '2026-05-13'
    })
  });
  return { status: r.status, body: await r.json() };
}

const token = await login();
const descCreds = await getDescCreds(token);

const afp = descCreds.find(d => /^AFP$/i.test(d.descripcion?.trim()));
const sfs = descCreds.find(d => /^SFS$/i.test(d.descripcion?.trim()));
const comida = descCreds.find(d => /COMIDA/i.test(d.descripcion));

console.log('  AFP:', afp ? `id=${afp.id_desc_cred} fijo=${afp.fijo}` : 'no encontrado');
console.log('  SFS:', sfs ? `id=${sfs.id_desc_cred} fijo=${sfs.fijo}` : 'no encontrado');
console.log('  COMIDA:', comida ? `id=${comida.id_desc_cred} fijo=${comida.fijo}` : 'no encontrado');

console.log('\n--- Test 1: POST con AFP (debe ser rechazado 400) ---');
if (afp) {
  const res = await postDescCredNomina(token, afp.id_desc_cred);
  console.log(`  status=${res.status} body=${JSON.stringify(res.body)}`);
  const ok = res.status === 400 && /autom[aá]ticamente|fijo/i.test(JSON.stringify(res.body));
  console.log(`  ${ok ? 'PASS' : 'FAIL'}: rechazo correcto del fijo AFP`);
}

console.log('\n--- Test 2: POST con SFS (debe ser rechazado 400) ---');
if (sfs) {
  const res = await postDescCredNomina(token, sfs.id_desc_cred);
  console.log(`  status=${res.status} body=${JSON.stringify(res.body)}`);
  const ok = res.status === 400 && /autom[aá]ticamente|fijo/i.test(JSON.stringify(res.body));
  console.log(`  ${ok ? 'PASS' : 'FAIL'}: rechazo correcto del fijo SFS`);
}

console.log('\n--- Test 3: POST con COMIDA (debe pasar la validación) ---');
// Nota: puede fallar después por id_nomina no válido o fecha; nos basta con que
// el error NO sea "fijo / automáticamente". status 400 con mensaje distinto = OK también.
if (comida) {
  const res = await postDescCredNomina(token, comida.id_desc_cred);
  console.log(`  status=${res.status} body=${JSON.stringify(res.body)}`);
  const blocked = /autom[aá]ticamente|fijo/i.test(JSON.stringify(res.body));
  console.log(`  ${!blocked ? 'PASS' : 'FAIL'}: COMIDA no es bloqueada por validación de fijo`);
}
