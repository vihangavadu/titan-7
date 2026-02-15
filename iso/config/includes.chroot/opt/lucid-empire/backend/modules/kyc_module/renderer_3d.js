// LUCID TITAN KYC MODULE :: 3D ID RENDERER
// Authority: Dva.12 | Status: TITAN_ACTIVE
// Purpose: Renders a physics-based 3D ID card with holographic simulation and gyroscopic control.

import * as THREE from 'three';

export class IDRenderer {
    constructor(canvasId) {
        this.scene = new THREE.Scene();
        this.camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
        this.renderer = new THREE.WebGLRenderer({ canvas: document.getElementById(canvasId), alpha: true });
        this.cardMesh = null;
        
        this.init();
    }

    init() {
        // Section 4.1.1: The Scene Graph
        const geometry = new THREE.PlaneGeometry(8.56, 5.398); // ID-1 Dimensions (cm)
        
        // Section 4.1.2: Holographic Shader Implementation
        // Custom GLSL shaders to simulate Fresnel interference patterns
        const vertexShader = `
            varying vec3 vNormal;
            varying vec3 vViewPosition;
            varying vec2 vUv;
            void main() {
                vUv = uv;
                vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
                vViewPosition = -mvPosition.xyz;
                vNormal = normalize(normalMatrix * normal);
                gl_Position = projectionMatrix * mvPosition;
            }
        `;

        const fragmentShader = `
            uniform sampler2D baseTexture;
            uniform sampler2D hologramTexture;
            uniform float intensity;
            varying vec3 vNormal;
            varying vec3 vViewPosition;
            varying vec2 vUv;

            void main() {
                vec3 normal = normalize(vNormal);
                vec3 viewDirection = normalize(vViewPosition);

                // Calculating the Fresnel effect for holographic iridescence
                float fresnel = dot(viewDirection, normal);
                fresnel = clamp(1.0 - fresnel, 0.0, 1.0);
                float fresnelPower = 2.0;
                fresnel = pow(fresnel, fresnelPower);

                vec4 baseColor = texture2D(baseTexture, vUv);
                vec3 hologramColor = texture2D(hologramTexture, vUv).rgb; // Placeholder texture

                // Mixing base color with holographic gradient
                gl_FragColor = vec4(mix(baseColor.rgb, hologramColor, fresnel * intensity), 1.0);
            }
        `;

        const material = new THREE.ShaderMaterial({
            uniforms: {
                baseTexture: { value: new THREE.TextureLoader().load('id_front.png') },
                hologramTexture: { value: new THREE.TextureLoader().load('holo_mask.png') },
                intensity: { value: 0.5 }
            },
            vertexShader: vertexShader,
            fragmentShader: fragmentShader
        });

        this.cardMesh = new THREE.Mesh(geometry, material);
        this.scene.add(this.cardMesh);

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        this.scene.add(ambientLight);
        
        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(0, 0, 5);
        this.scene.add(directionalLight);

        this.camera.position.z = 10;
        
        this.setupGyroscope();
        this.animate();
    }

    setupGyroscope() {
        // Section 4.2.1: Device Orientation API Integration
        window.addEventListener('deviceorientation', (event) => {
            const alpha = event.alpha ? THREE.MathUtils.degToRad(event.alpha) : 0;
            const beta = event.beta ? THREE.MathUtils.degToRad(event.beta) : 0;
            const gamma = event.gamma ? THREE.MathUtils.degToRad(event.gamma) : 0;

            // Apply rotation to the ID card mesh
            if (this.cardMesh) {
                // Section 4.2.2: Micro-Tremor Simulation (Ghost Motor)
                // Injecting physiological tremor (8-12Hz)
                const time = Date.now() * 0.001;
                const tremorX = Math.sin(time * 10) * 0.02; // 10Hz
                const tremorY = Math.cos(time * 12) * 0.02; // 12Hz

                this.cardMesh.rotation.set(beta + tremorX, gamma + tremorY, alpha);
            }
        });
    }

    animate() {
        requestAnimationFrame(() => this.animate());
        this.renderer.render(this.scene, this.camera);
    }
}

// Initialize on load
// new IDRenderer('kycCanvas');
