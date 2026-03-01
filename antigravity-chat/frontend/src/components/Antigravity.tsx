import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface AntigravityProps {
    count?: number;
    magnetRadius?: number;
    ringRadius?: number;
    waveSpeed?: number;
    waveAmplitude?: number;
    particleSize?: number;
    lerpSpeed?: number;
    color?: string;
    autoAnimate?: boolean;
    particleVariance?: number;
    rotationSpeed?: number;
    depthFactor?: number;
    pulseSpeed?: number;
    particleShape?: 'sphere' | 'capsule' | 'cube';
    fieldStrength?: number;
}

const Particles = ({
    count = 300,
    magnetRadius = 6,
    ringRadius = 7,
    waveSpeed = 0.4,
    waveAmplitude = 1,
    particleSize = 1.5,
    lerpSpeed = 0.05,
    color = "#5227FF",
    autoAnimate = true,
    particleVariance = 1,
    rotationSpeed = 0,
    depthFactor = 1,
    pulseSpeed = 3,
    particleShape = "capsule",
    fieldStrength = 10,
}: AntigravityProps) => {
    const mesh = useRef<THREE.InstancedMesh>(null);
    const dummy = useMemo(() => new THREE.Object3D(), []);

    const particles = useMemo(() => {
        const temp = [];
        for (let i = 0; i < count; i++) {
            const theta = Math.random() * 2 * Math.PI;
            const phi = Math.random() * Math.PI;
            const r = ringRadius + (Math.random() - 0.5) * particleVariance;

            const x = r * Math.sin(phi) * Math.cos(theta);
            const y = r * Math.sin(phi) * Math.sin(theta);
            const z = r * Math.cos(phi) * depthFactor;

            temp.push({
                t: Math.random() * 100,
                factor: 20 + Math.random() * 100,
                speed: 0.01 + Math.random() / 200,
                x,
                y,
                z,
                mx: 0,
                my: 0,
            });
        }
        return temp;
    }, [count, ringRadius, particleVariance, depthFactor]);

    useFrame((state) => {
        if (!mesh.current) return;

        const time = state.clock.getElapsedTime();

        particles.forEach((particle, i) => {
            let { x, y, z, factor, speed } = particle;

            const t = (particle.t += speed * waveSpeed);

            // Wave motion
            const wave = Math.sin(t) * waveAmplitude;

            // Update position with wave and pulse
            const pulse = Math.sin(time * pulseSpeed) * 0.1;

            dummy.position.set(
                x + wave + pulse,
                y + Math.cos(t) * waveAmplitude + pulse,
                z + Math.sin(t * 0.5) * waveAmplitude
            );

            // Rotation
            if (rotationSpeed > 0) {
                dummy.rotation.set(time * rotationSpeed, time * rotationSpeed, t);
            } else {
                dummy.rotation.set(t, t, t);
            }

            // Scale
            const s = particleSize * (1 + Math.sin(t) * 0.2);
            dummy.scale.set(s, s, s);

            dummy.updateMatrix();
            mesh.current!.setMatrixAt(i, dummy.matrix);
        });

        mesh.current.instanceMatrix.needsUpdate = true;
    });

    return (
        <instancedMesh ref={mesh} args={[undefined, undefined, count]}>
            {particleShape === 'capsule' ? (
                <capsuleGeometry args={[0.1, 0.4, 4, 8]} />
            ) : particleShape === 'sphere' ? (
                <sphereGeometry args={[0.2, 16, 16]} />
            ) : (
                <boxGeometry args={[0.2, 0.2, 0.2]} />
            )}
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={2} toneMapped={false} />
        </instancedMesh>
    );
};

const Antigravity: React.FC<AntigravityProps> = (props) => {
    return (
        <Canvas camera={{ position: [0, 0, 15], fov: 50 }}>
            <ambientLight intensity={0.5} />
            <pointLight position={[10, 10, 10]} intensity={1} />
            <spotLight position={[-10, 10, 10]} angle={0.15} penumbra={1} />
            <Particles {...props} />
        </Canvas>
    );
};

export default Antigravity;
