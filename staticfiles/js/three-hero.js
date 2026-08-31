/**
 * Apex Horizon International Academy — 3D Three.js WebGL Hero Engine
 * Production-ready, performance-optimized, and accessible 3D interactive background.
 */

(function () {
  'use strict';

  const container = document.getElementById('three-hero-canvas');
  if (!container) return;

  // Check for Reduced Motion Preference
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  
  // Check for WebGL Support
  function hasWebGL() {
    try {
      const canvas = document.createElement('canvas');
      return !!(window.WebGLRenderingContext && (canvas.getContext('webgl') || canvas.getContext('experimental-webgl')));
    } catch (e) {
      return false;
    }
  }

  if (!hasWebGL() || prefersReducedMotion) {
    container.classList.add('three-fallback-mode');
    return;
  }

  // Load Three.js if not already present
  if (typeof THREE === 'undefined') {
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
    script.onload = initThreeHero;
    document.head.appendChild(script);
  } else {
    initThreeHero();
  }

  function initThreeHero() {
    let scene, camera, renderer;
    let mainMesh, particleSystem, ambientLight, pointLight1, pointLight2;
    let mouseX = 0, mouseY = 0;
    let targetX = 0, targetY = 0;
    let isVisible = true;

    const width = container.clientWidth || window.innerWidth;
    const height = container.clientHeight || window.innerHeight;

    // 1. Scene & Camera
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.z = 32;

    // 2. Renderer
    renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    container.appendChild(renderer.domElement);

    // 3. Lighting
    ambientLight = new THREE.AmbientLight(0x0f172a, 1.5);
    scene.add(ambientLight);

    pointLight1 = new THREE.PointLight(0x4f46e5, 3, 50);
    pointLight1.position.set(10, 15, 15);
    scene.add(pointLight1);

    pointLight2 = new THREE.PointLight(0x06b6d4, 2.5, 50);
    pointLight2.position.set(-15, -10, 10);
    scene.add(pointLight2);

    // 4. Centerpiece 3D Geometric Polyhedra (Academic Emblem / Icosahedron)
    const geometry = new THREE.IcosahedronGeometry(7, 1);
    
    // Wireframe Outer Mesh
    const wireMat = new THREE.MeshStandardMaterial({
      color: 0x818cf8,
      wireframe: true,
      roughness: 0.2,
      metalness: 0.8,
      transparent: true,
      opacity: 0.4
    });
    mainMesh = new THREE.Mesh(geometry, wireMat);
    scene.add(mainMesh);

    // Inner Solid Core with Iridescent Glow
    const coreGeo = new THREE.IcosahedronGeometry(4.5, 0);
    const coreMat = new THREE.MeshPhysicalMaterial({
      color: 0x0f172a,
      emissive: 0x1e1b4b,
      roughness: 0.1,
      metalness: 0.9,
      transmission: 0.6,
      transparent: true,
      opacity: 0.85
    });
    const coreMesh = new THREE.Mesh(coreGeo, coreMat);
    mainMesh.add(coreMesh);

    // Orbiting Ring (Celestial Horizon Ring)
    const ringGeo = new THREE.TorusGeometry(10, 0.08, 16, 100);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0xeab308, transparent: true, opacity: 0.6 });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.rotation.x = Math.PI / 3;
    mainMesh.add(ringMesh);

    // 5. Ambient Floating Particle Vortex
    const particleCount = 450;
    const particleGeo = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    const scales = new Float32Array(particleCount);

    for (let i = 0; i < particleCount * 3; i += 3) {
      positions[i] = (Math.random() - 0.5) * 60;
      positions[i + 1] = (Math.random() - 0.5) * 60;
      positions[i + 2] = (Math.random() - 0.5) * 40;
      scales[i / 3] = Math.random() * 2 + 0.5;
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    particleGeo.setAttribute('scale', new THREE.BufferAttribute(scales, 1));

    const particleMat = new THREE.PointsMaterial({
      color: 0x93c5fd,
      size: 0.35,
      transparent: true,
      opacity: 0.55,
      blending: THREE.AdditiveBlending
    });

    particleSystem = new THREE.Points(particleGeo, particleMat);
    scene.add(particleSystem);

    // 6. Interaction Listeners
    function onMouseMove(event) {
      const windowHalfX = window.innerWidth / 2;
      const windowHalfY = window.innerHeight / 2;
      targetX = (event.clientX - windowHalfX) * 0.0008;
      targetY = (event.clientY - windowHalfY) * 0.0008;
    }

    function onWindowResize() {
      const w = container.clientWidth || window.innerWidth;
      const h = container.clientHeight || window.innerHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    }

    window.addEventListener('mousemove', onMouseMove, { passive: true });
    window.addEventListener('resize', onWindowResize, { passive: true });

    // Intersection Observer to throttle rendering when offscreen
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        isVisible = entry.isIntersecting;
      });
    }, { threshold: 0.05 });
    observer.observe(container);

    // 7. Animation Loop with Spring Physics Damping
    let clock = new THREE.Clock();

    function animate() {
      requestAnimationFrame(animate);
      if (!isVisible) return;

      const elapsedTime = clock.getElapsedTime();

      // Smooth camera parallax
      mouseX += (targetX - mouseX) * 0.05;
      mouseY += (targetY - mouseY) * 0.05;

      camera.position.x = mouseX * 20;
      camera.position.y = -mouseY * 20;
      camera.lookAt(scene.position);

      // Rotate Main Geometric Emblem
      if (mainMesh) {
        mainMesh.rotation.y = elapsedTime * 0.25;
        mainMesh.rotation.x = Math.sin(elapsedTime * 0.15) * 0.2;
        ringMesh.rotation.z = -elapsedTime * 0.35;
      }

      // Rotate & Pulse Particle Vortex
      if (particleSystem) {
        particleSystem.rotation.y = elapsedTime * 0.04;
        particleSystem.rotation.x = elapsedTime * 0.02;
      }

      renderer.render(scene, camera);
    }

    animate();
  }
})();
