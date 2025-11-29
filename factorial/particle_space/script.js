// Escena, cámara y renderizador
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
document.getElementById('canvas-container').appendChild(renderer.domElement);

// Posición inicial de la cámara
camera.position.z = 30;

// Contenedor para las partículas
const particles = [];
const particleCount = 2000;
const colors = [
  0xff0000, 0x00ff00, 0x0000ff, 0xffff00, 0xff00ff, 0x00ffff,
  0xff6600, 0x6600ff, 0x0066ff, 0xff0066
];

// Crear partículas
for (let i = 0; i < particleCount; i++) {
  const geometry = new THREE.SphereGeometry(0.1, 8, 8);
  const material = new THREE.MeshBasicMaterial({ color: colors[Math.floor(Math.random() * colors.length)] });
  const particle = new THREE.Mesh(geometry, material);

  // Posición aleatoria en 3D
  particle.position.x = Math.random() * 100 - 50;
  particle.position.y = Math.random() * 100 - 50;
  particle.position.z = Math.random() * 100 - 50;

  // Velocidad de movimiento suave
  particle.userData = {
    speed: Math.random() * 0.02 + 0.01,
    angle: Math.random() * Math.PI * 2
  };

  scene.add(particle);
  particles.push(particle);
}

// Iluminación
const ambientLight = new THREE.AmbientLight(0x404040);
scene.add(ambientLight);

// Manejo del mouse para mover la cámara
let isDragging = false;
let previousMousePosition = { x: 0, y: 0 };

document.addEventListener('mousedown', (e) => {
  isDragging = true;
  previousMousePosition = { x: e.clientX, y: e.clientY };
});

document.addEventListener('mouseup', () => {
  isDragging = false;
});

document.addEventListener('mousemove', (e) => {
  if (isDragging) {
    const deltaMove = {
      x: e.clientX - previousMousePosition.x,
      y: e.clientY - previousMousePosition.y
    };

    // Rotación de la cámara
    camera.rotation.y += deltaMove.x * 0.005;
    camera.rotation.x += deltaMove.y * 0.005;

    previousMousePosition = { x: e.clientX, y: e.clientY };
  }
});

// Zoom con scroll
document.addEventListener('wheel', (e) => {
  const zoomSpeed = 0.1;
  camera.position.z += e.deltaY * zoomSpeed;
  camera.position.z = Math.max(1, Math.min(100, camera.position.z)); // Límites
});

// Botones de control
document.getElementById('zoom-in').addEventListener('click', () => {
  camera.position.z = Math.max(1, camera.position.z - 5);
});

document.getElementById('zoom-out').addEventListener('click', () => {
  camera.position.z = Math.min(100, camera.position.z + 5);
});

document.getElementById('reset-camera').addEventListener('click', () => {
  camera.position.set(0, 0, 30);
  camera.rotation.set(0, 0, 0);
});

// Animación principal
function animate() {
  requestAnimationFrame(animate);

  // Animar partículas (movimiento suave en espiral)
  particles.forEach(particle => {
    particle.userData.angle += particle.userData.speed;
    particle.position.x += Math.sin(particle.userData.angle) * 0.01;
    particle.position.y += Math.cos(particle.userData.angle) * 0.01;
    particle.position.z += Math.sin(particle.userData.angle * 0.5) * 0.005;
  });

  renderer.render(scene, camera);
}

// Redimensionar ventana
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

// Iniciar animación
animate();