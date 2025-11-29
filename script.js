// Escena, cámara y renderizador
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('canvas'), antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);

// Cámara inicial
camera.position.z = 5;

// Control de cámara (arrastre)
let isDragging = false;
let previousMousePosition = { x: 0, y: 0 };

document.addEventListener('mousedown', (e) => {
  isDragging = true;
  previousMousePosition = { x: e.clientX, y: e.clientY };
});

document.addEventListener('mousemove', (e) => {
  if (!isDragging) return;
  const deltaMove = { x: e.clientX - previousMousePosition.x, y: e.clientY - previousMousePosition.y };
  camera.rotation.y += deltaMove.x * 0.01;
  camera.rotation.x += deltaMove.y * 0.01;
  previousMousePosition = { x: e.clientX, y: e.clientY };
});

document.addEventListener('mouseup', () => {
  isDragging = false;
});

// Zoom con scroll
document.addEventListener('wheel', (e) => {
  const zoomSpeed = 0.1;
  const direction = e.deltaY > 0 ? 1 : -1;
  camera.position.z += direction * zoomSpeed;
  camera.position.z = Math.max(1, Math.min(20, camera.position.z)); // Límites de zoom
});

// Generar partículas
const particleCount = 2000;
const particles = new THREE.BufferGeometry();
const positions = new Float32Array(particleCount * 3);
const colors = new Float32Array(particleCount * 3);

for (let i = 0; i < particleCount; i++) {
  // Posición aleatoria en 3D
  positions[i * 3 + 0] = (Math.random() - 0.5) * 20;
  positions[i * 3 + 1] = (Math.random() - 0.5) * 20;
  positions[i * 3 + 2] = (Math.random() - 0.5) * 20;

  // Color aleatorio (RGB)
  colors[i * 3 + 0] = Math.random();
  colors[i * 3 + 1] = Math.random();
  colors[i * 3 + 2] = Math.random();
}

particles.setAttribute('position', new THREE.BufferAttribute(positions, 3));
particles.setAttribute('color', new THREE.BufferAttribute(colors, 3));

const material = new THREE.PointsMaterial({
  size: 0.05,
  vertexColors: true,
  transparent: true,
  opacity: 0.9
});

const pointCloud = new THREE.Points(particles, material);
scene.add(pointCloud);

// Animación
function animate() {
  requestAnimationFrame(animate);
  pointCloud.rotation.x += 0.001;
  pointCloud.rotation.y += 0.001;
  renderer.render(scene, camera);
}

// Ajuste de tamaño de ventana
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// Iniciar animación
animate();

// Añadir información en pantalla
const info = document.createElement('div');
info.style.position = 'absolute';
info.style.top = '10px';
info.style.left = '10px';
info.style.color = 'white';
info.style.fontFamily = 'Arial, sans-serif';
info.style.fontSize = '14px';
info.style.pointerEvents = 'none';
info.textContent = 'Arrastre para rotar | Scroll para zoom';
document.body.appendChild(info);
