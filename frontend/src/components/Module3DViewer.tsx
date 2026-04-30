"use client";

import React, { useRef, useMemo, useState, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, PerspectiveCamera, Grid, Center, Text, ContactShadows } from "@react-three/drei";
import * as THREE from "three";

interface Obstacle {
  id: string;
  type: 'window' | 'door' | 'socket' | 'pipe';
  x: number;
  y: number;
  width: number;
  height: number;
  depth?: number;
}

interface Module3DProps {
  width: number;
  height: number;
  depth: number;
  color?: string;
  name?: string;
  // Advanced params
  legHeight?: number;
  legOffsetSide?: number;
  legOffsetFront?: number;
  legOffsetBack?: number;
  shelfCount?: number;
  showInterior?: boolean;
  modules?: any[];
  obstacles?: Obstacle[];
  // Etap 2: handles
  handleType?: 'none' | 'reling' | 'knob' | 'edge';
  handleLength?: number;
  handleOrientation?: 'horizontal' | 'vertical';
  handlePosX?: 'left' | 'center' | 'right';
  handlePosY?: 'top' | 'middle' | 'bottom';
  textureUrl?: string;
  highlightedPartId?: string;
  onPartClick?: (partId: string) => void;
  frontRadius?: number;
  frontMilling?: 'none' | 'rounded' | 'classic';
}

const Leg = ({ position, height }: { position: [number, number, number], height: number }) => {
  const h = height / 1000;
  return (
    <group position={position}>
      <mesh castShadow receiveShadow position={[0, h / 2, 0]}>
        <cylinderGeometry args={[0.02, 0.02, h, 16]} />
        <meshStandardMaterial color="#333333" metalness={0.8} roughness={0.2} />
      </mesh>
    </group>
  );
};
const isColliding = (
  mX: number, mY: number, mW: number, mH: number,
  obstacles: Obstacle[] = []
) => {
  return obstacles.some(obs => {
    const modLeft = mX;
    const modRight = mX + mW;
    const modBottom = mY;
    const modTop = mY + mH;

    const obsLeft = obs.x;
    const obsRight = obs.x + obs.width;
    const obsBottom = obs.y;
    const obsTop = obs.y + obs.height;

    const overlapX = modLeft < obsRight && modRight > obsLeft;
    const overlapY = modBottom < obsTop && modTop > obsBottom;

    return overlapX && overlapY;
  });
};

const Handle = ({ type, length = 128, orientation = 'horizontal', width, height, posX = 'center', posY = 'top' }: {
  type: string;
  length?: number;
  orientation?: string;
  width: number;
  height: number;
  posX?: string;
  posY?: string;
}) => {
  const L = length / 1000;
  const radius = 0.006;
  const depth = 0.03;

  // Calculate relative position
  let x = 0;
  if (posX === 'left') x = -width / 2 + 0.05;
  if (posX === 'right') x = width / 2 - 0.05;

  let y = height / 2;
  if (posY === 'top') y = height - 0.08;
  if (posY === 'bottom') y = 0.08;
  if (posY === 'middle') y = height / 2;

  const isVert = orientation === 'vertical';
  const rot: [number, number, number] = isVert ? [0, 0, Math.PI / 2] : [0, 0, 0];

  if (type === 'knob') {
    return (
      <mesh position={[x, y, depth/2]} rotation={[Math.PI/2, 0, 0]}>
        <cylinderGeometry args={[0.015, 0.01, 0.025, 16]} />
        <meshStandardMaterial color="#cccccc" metalness={0.9} roughness={0.1} />
      </mesh>
    );
  }

  if (type === 'reling') {
    return (
      <group position={[x, y, depth/2]}>
        {/* Main Bar */}
        <mesh rotation={rot}>
          <cylinderGeometry args={[radius, radius, L, 16]} />
          <meshStandardMaterial color="#cccccc" metalness={0.9} roughness={0.1} />
        </mesh>
        {/* Legs */}
        <mesh position={isVert ? [0, -L/2 + 0.01, -depth/4] : [-L/2 + 0.01, 0, -depth/4]}>
          <boxGeometry args={[0.01, 0.01, depth/2]} />
          <meshStandardMaterial color="#bbbbbb" metalness={0.9} roughness={0.1} />
        </mesh>
        <mesh position={isVert ? [0, L/2 - 0.01, -depth/4] : [L/2 - 0.01, 0, -depth/4]}>
          <boxGeometry args={[0.01, 0.01, depth/2]} />
          <meshStandardMaterial color="#bbbbbb" metalness={0.9} roughness={0.1} />
        </mesh>
      </group>
    );
  }

  if (type === 'edge') {
    const edgeY = height - 0.001;
    return (
      <mesh position={[0, edgeY, 0.005]}>
        <boxGeometry args={[width - 0.002, 0.002, 0.03]} />
        <meshStandardMaterial color="#999999" metalness={1} roughness={0.1} />
      </mesh>
    );
  }

  return null;
};

const SmartBoard = ({
  w, h, t,
  position, rotation = [0, 0, 0],
  color = "#ffffff",
  texture = null,
  edgebands = { top: false, bottom: false, left: false, right: false },
  edgeColor = "#dddddd",
  highlighted = false,
  radius = 0,
  onClick
}: {
  w: number, h: number, t: number,
  position: [number, number, number],
  rotation?: [number, number, number],
  color?: string,
  texture?: THREE.Texture | null,
  edgebands?: { top: boolean, bottom: boolean, left: boolean, right: boolean },
  edgeColor?: string,
  highlighted?: boolean,
  radius?: number,
  onClick?: (e: any) => void
}) => {
  const displayColor = highlighted ? "#fbbf24" : color;
  const emissive = highlighted ? "#fbbf24" : "#000000";
  const intensity = highlighted ? 0.5 : 0;

  const shape = useMemo(() => {
    if (radius <= 0) return null;
    const s = new THREE.Shape();
    const x = -w/2;
    const y = -h/2;
    const width = w;
    const height = h;
    const r = Math.min(radius, width/2, height/2);

    s.moveTo(x + r, y);
    s.lineTo(x + width - r, y);
    s.absarc(x + width - r, y + r, r, -Math.PI / 2, 0, false);
    s.lineTo(x + width, y + height - r);
    s.absarc(x + width - r, y + height - r, r, 0, Math.PI / 2, false);
    s.lineTo(x + r, y + height);
    s.absarc(x + r, y + height - r, r, Math.PI / 2, Math.PI, false);
    s.lineTo(x, y + r);
    s.absarc(x + r, y + r, r, Math.PI, Math.PI * 1.5, false);
    return s;
  }, [w, h, radius]);

  const extrudeSettings = useMemo(() => ({
    steps: 1,
    depth: t,
    bevelEnabled: true,
    bevelThickness: 0.002,
    bevelSize: 0.002,
    bevelOffset: 0,
    bevelSegments: 3
  }), [t]);

  return (
    <group position={position} rotation={rotation} onClick={onClick}>
      {/* Main Panel Body */}
      <mesh castShadow receiveShadow position={radius > 0 ? [0, 0, -t/2] : [0, 0, 0]}>
        {radius > 0 ? (
          <extrudeGeometry args={[shape!, extrudeSettings]} />
        ) : (
          <boxGeometry args={[w, h, t]} />
        )}
        <meshStandardMaterial
          color={displayColor}
          map={texture}
          roughness={highlighted ? 0.3 : 0.7}
          emissive={emissive}
          emissiveIntensity={intensity}
        />
      </mesh>

      {/* Edgeband Visuals - only rendered if active */}
      {/* Edgebands are thin strips (0.5mm - 2mm usually, 2mm here for visibility) on the 4 narrow sides */}
      {edgebands.top && (
        <mesh position={[0, h/2, 0]}>
          <boxGeometry args={[w, 0.002, t + 0.001]} />
          <meshStandardMaterial color={edgeColor} metalness={0.1} roughness={0.5} />
        </mesh>
      )}
      {edgebands.bottom && (
        <mesh position={[0, -h/2, 0]}>
          <boxGeometry args={[w, 0.002, t + 0.001]} />
          <meshStandardMaterial color={edgeColor} metalness={0.1} roughness={0.5} />
        </mesh>
      )}
      {edgebands.left && (
        <mesh position={[-w/2, 0, 0]}>
          <boxGeometry args={[0.002, h, t + 0.001]} />
          <meshStandardMaterial color={edgeColor} metalness={0.1} roughness={0.5} />
        </mesh>
      )}
      {edgebands.right && (
        <mesh position={[w/2, 0, 0]}>
          <boxGeometry args={[0.002, h, t + 0.001]} />
          <meshStandardMaterial color={edgeColor} metalness={0.1} roughness={0.5} />
        </mesh>
      )}
    </group>
  );
};

const BoxModule = ({
  width, height, depth, color = "#ffffff", name,
  legHeight = 100,
  legOffsetSide = 50,
  legOffsetFront = 50,
  legOffsetBack = 50,
  shelfCount = 0,
  showInterior = true,
  isColliding: colliding = false,
  handleType = 'none',
  handleLength = 128,
  handleOrientation = 'horizontal',
  handlePosX = 'center',
  handlePosY = 'top',
  textureUrl,
  highlightedPartId,
  onPartClick,
  frontRadius = 0,
  frontMilling = 'none'
}: Module3DProps & { isColliding?: boolean }) => {
  const [texture, setTexture] = useState<THREE.Texture | null>(null);
  useEffect(() => {
    if (!textureUrl) { setTexture(null); return; }
    const loader = new THREE.TextureLoader();
    loader.load(textureUrl, (tex) => {
      tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
      tex.repeat.set(2, 2);
      setTexture(tex);
    });
  }, [textureUrl]);

  const w = width / 1000;
  const h = height / 1000;
  const d = depth / 1000;
  const lh = (legHeight || 0) / 1000;
  const thickness = 0.018; // 18mm standard

  const displayColor = colliding ? "#ef4444" : color;
  const emissiveColor = colliding ? "#ef4444" : "#000000";
  const emissiveIntensity = colliding ? 0.3 : 0;

  const los = (legOffsetSide || 50) / 1000;
  const lof = (legOffsetFront || 50) / 1000;
  const lob = (legOffsetBack || 50) / 1000;

  const getPartMaterial = (partId: string) => {
    const isHighlighted = highlightedPartId === partId;
    const pColor = isHighlighted ? "#fbbf24" : displayColor;
    const pEmissive = isHighlighted ? "#fbbf24" : emissiveColor;
    const pIntensity = isHighlighted ? 0.8 : emissiveIntensity;

    return (
        <meshStandardMaterial
          color={pColor}
          map={texture}
          roughness={isHighlighted ? 0.3 : 0.7}
          emissive={pEmissive}
          emissiveIntensity={pIntensity}
        />
    );
  };

  const shelves = useMemo(() => {
    const list = [];
    if (shelfCount > 0) {
      const spacing = (h - 2 * thickness) / (shelfCount + 1);
      for (let i = 1; i <= shelfCount; i++) {
        list.push(i * spacing);
      }
    }
    return list;
  }, [shelfCount, h]);

  return (
    <group position={[0, lh, 0]}>
      {/* Legs */}
      {lh > 0 && (
        <group position={[0, -lh, 0]}>
          <Leg position={[-w/2 + los, 0, d/2 - lof]} height={legHeight} />
          <Leg position={[w/2 - los, 0, d/2 - lof]} height={legHeight} />
          <Leg position={[-w/2 + los, 0, -d/2 + lob]} height={legHeight} />
          <Leg position={[w/2 - los, 0, -d/2 + lob]} height={legHeight} />
        </group>
      )}

      {showInterior ? (
        <group>
          {/* Left Side */}
          <SmartBoard
            w={thickness} h={h} t={d}
            position={[-w/2 + thickness/2, h/2, 0]}
            rotation={[0, 0, 0]}
            color={color}
            texture={texture}
            highlighted={highlightedPartId === "side_left"}
            edgebands={{ top: true, bottom: true, left: true, right: true }}
            onClick={(e: any) => { e.stopPropagation(); onPartClick?.("side_left"); }}
          />

          {/* Right Side */}
          <SmartBoard
            w={thickness} h={h} t={d}
            position={[w/2 - thickness/2, h/2, 0]}
            rotation={[0, 0, 0]}
            color={color}
            texture={texture}
            highlighted={highlightedPartId === "side_right"}
            edgebands={{ top: true, bottom: true, left: true, right: true }}
            onClick={(e: any) => { e.stopPropagation(); onPartClick?.("side_right"); }}
          />

          {/* Top */}
          <SmartBoard
            w={w - 2 * thickness} h={thickness} t={d}
            position={[0, h - thickness/2, 0]}
            color={color}
            texture={texture}
            highlighted={highlightedPartId === "top"}
            edgebands={{ top: false, bottom: false, left: true, right: true }}
            onClick={(e: any) => { e.stopPropagation(); onPartClick?.("top"); }}
          />

          {/* Bottom */}
          <SmartBoard
            w={w - 2 * thickness} h={thickness} t={d}
            position={[0, thickness/2, 0]}
            color={color}
            texture={texture}
            highlighted={highlightedPartId === "bottom"}
            edgebands={{ top: false, bottom: false, left: true, right: true }}
            onClick={(e: any) => { e.stopPropagation(); onPartClick?.("bottom"); }}
          />

          {/* Back HDF (simple) */}
          <mesh
            position={[0, h/2, -d/2 + 0.002]}
            onClick={(e: any) => { e.stopPropagation(); onPartClick?.("back"); }}
          >
            <boxGeometry args={[w - 0.004, h - 0.004, 0.003]} />
            {getPartMaterial("back")}
          </mesh>
          {/* Shelves */}
          {shelves.map((sh, i) => (
            <SmartBoard
              key={i}
              w={w - 2 * thickness - 0.002} h={thickness} t={d - 0.02}
              position={[0, sh + thickness/2, 0.005]}
              color={color}
              texture={texture}
              highlighted={highlightedPartId === `shelf_${i+1}`}
              edgebands={{ top: false, bottom: false, left: false, right: true }}
              onClick={(e: any) => { e.stopPropagation(); onPartClick?.(`shelf_${i+1}`); }}
            />
          ))}
        </group>
      ) : (
        <group>
           {/* Facade / Door */}
           <SmartBoard
             w={w - 0.004} h={h - 0.004} t={0.018}
             position={[0, h / 2, d / 2 + 0.009]}
             color={color}
             texture={texture}
             highlighted={highlightedPartId === "front"}
             edgebands={{ top: true, bottom: true, left: true, right: true }}
             radius={frontMilling === 'rounded' ? (frontRadius || 0.01) : 0}
             onClick={(e: any) => { e.stopPropagation(); onPartClick?.("front"); }}
           />
           {/* Handle */}
           {handleType !== 'none' && (
             <group position={[0, 0, d/2 + 0.018]}>
               <Handle
                  type={handleType}
                  length={handleLength}
                  orientation={handleOrientation}
                  width={w}
                  height={h}
                  posX={handlePosX}
                  posY={handlePosY}
               />
             </group>
           )}
           {/* Side Panels visible behind facade */}
           <mesh position={[-w/2 + thickness/2, h/2, 0]}>
             <boxGeometry args={[thickness, h, d]} />
             <meshStandardMaterial color={displayColor} roughness={0.8} />
           </mesh>
           <mesh position={[w/2 - thickness/2, h/2, 0]}>
             <boxGeometry args={[thickness, h, d]} />
             <meshStandardMaterial color={displayColor} roughness={0.8} />
           </mesh>
        </group>
      )}

      {/* Wireframe overlay for premium feel */}
      <mesh position={[0, h / 2, 0]}>
        <boxGeometry args={[w, h, d]} />
        <meshBasicMaterial color="#00ffff" wireframe transparent opacity={0.05} />
      </mesh>

      {/* Dimensions labels */}
      <group position={[0, h + 0.1, 0]}>
         <Text fontSize={0.045} color="#ffffff" anchorX="center" anchorY="bottom">
            {width} x {height} x {depth}
         </Text>
         <Text fontSize={0.02} color="#888888" anchorX="center" anchorY="top" position={[0, -0.01, 0]}>
            WYMIARY ZEWNETRZNE (MM)
         </Text>
      </group>
    </group>
  );
};

const Obstacle3D = ({ id, type, x, y, width, height, depth = 50 }: Obstacle) => {
  const w = width / 1000;
  const h = height / 1000;
  const d = (depth || 50) / 1000;
  const px = x / 1000;
  const py = y / 1000;

  let color = "#3b82f6"; // Window
  if (type === 'door') color = "#f59e0b";
  if (type === 'socket') color = "#8b5cf6";
  if (type === 'pipe') color = "#64748b";

  return (
    <group position={[px + w/2, py + h/2, -0.1]}>
       <mesh castShadow receiveShadow>
          <boxGeometry args={[w, h, d]} />
          <meshStandardMaterial
            color={color}
            transparent
            opacity={0.3}
            metalness={0.1}
            roughness={0.8}
          />
       </mesh>
       <mesh>
          <boxGeometry args={[w, h, d]} />
          <meshBasicMaterial color={color} wireframe transparent opacity={0.3} />
       </mesh>
       <Text
         position={[0, h/2 + 0.05, 0.05]}
         fontSize={0.03}
         color={color}
         anchorY="bottom"
       >
          {type.toUpperCase()}
       </Text>
    </group>
  );
};

const SceneModules = ({ principal, modules, obstacles }: { principal: Module3DProps, modules?: any[], obstacles?: Obstacle[] }) => {
  if (!modules || modules.length === 0) {
    return <BoxModule {...principal} />;
  }

  let cumulativeX = 0;
  let cumulativeX_mm = 0;
  const spacing = 0.05; // 5cm gap

  const totalWidth_mm = modules.reduce((acc, m) => acc + (m.width || m.width_mm || 600), 0) + (modules.length - 1) * 2; // tiny 2mm gap
  const globalOffsetX_mm = - (totalWidth_mm / 2);

  return (
    <group position={[globalOffsetX_mm / 1000, 0, 0]}>
      {/* Obstacles Rendering */}
      {obstacles?.map(obs => (
         <Obstacle3D key={obs.id} {...obs} />
      ))}

      {modules.map((m, idx) => {
        const w_mm = m.width || m.width_mm || 600;
        const w_m = w_mm / 1000;
        const h_mm = m.height || m.height_mm || 720;
        const xPos_relative_m = cumulativeX + (w_m / 2);

        // Absolute X/Y for collision check (in mm)
        const absX_mm = cumulativeX_mm;
        const absY_mm = m.y || 0;

        const colliding = isColliding(absX_mm, absY_mm, w_mm, h_mm, obstacles);

        cumulativeX += w_m + spacing;
        cumulativeX_mm += w_mm + 2; // 2mm spacing internal

        return (
          <group key={m.code || idx} position={[xPos_relative_m, (m.y || 0) / 1000, - (m.z || 0) / 1000]}>
             <BoxModule
                width={w_mm}
                height={h_mm}
                depth={m.depth || m.depth_mm || 560}
                showInterior={principal.showInterior}
                shelfCount={principal.shelfCount}
                isColliding={colliding}
                frontRadius={principal.frontRadius}
                frontMilling={principal.frontMilling}
             />
             <Text
                position={[0, -0.05, (m.depth || 560) / 2000 + 0.1]}
                fontSize={0.03}
                color="#ffffff"
             >
                {m.name || m.code}
             </Text>
          </group>
        );
      })}
    </group>
  );
};

export default function Module3DViewer(props: Module3DProps) {
  return (
    <div className="w-full h-full min-h-[600px] bg-[#18191c] overflow-hidden relative group">
      <Canvas shadows gl={{ antialias: true }} style={{ background: "#18191c" }}>
        <PerspectiveCamera makeDefault position={[1.8, 1.2, 1.8]} fov={45} />
        <OrbitControls
          enableDamping
          dampingFactor={0.05}
          minDistance={0.5}
          maxDistance={10}
          makeDefault
          target={[0, 0.4, 0]}
        />

        {/* LIGHTS */}
        <ambientLight intensity={0.6} />
        <pointLight position={[5, 8, 5]} intensity={2.0} castShadow />
        <pointLight position={[-5, 5, -3]} intensity={1.0} />
        <directionalLight position={[3, 6, 3]} intensity={1.2} />

        {/* SCENE */}
        <SceneModules
          principal={props}
          modules={props.modules}
          obstacles={props.obstacles}
        />

        {/* FLOOR & GRID */}
        <Grid
          infiniteGrid
          fadeDistance={20}
          fadeStrength={5}
          cellSize={0.1}
          sectionSize={1}
          sectionColor="#222222"
          cellColor="#050505"
          position={[0, -0.001, 0]}
        />

        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.01, 0]} receiveShadow>
          <planeGeometry args={[100, 100]} />
          <shadowMaterial opacity={0.3} />
        </mesh>

        <ContactShadows
          position={[0, 0, 0]}
          opacity={0.4}
          scale={15}
          blur={2.5}
          far={2}
        />
      </Canvas>

      {/* UI OVERLAYS */}
      <div className="absolute bottom-8 right-8 p-6 bg-black/40 backdrop-blur-xl rounded-[2rem] border border-white/10 text-white pointer-events-none transition-all duration-500 group-hover:bg-black/60 shadow-brand-glow/10">
         <div className="flex items-center gap-3 mb-2">
            <div className="w-2 h-2 rounded-full bg-brand-hover animate-pulse" />
            <p className="text-[10px] uppercase font-black tracking-[0.2em] text-brand-hover">Rendering Engine Active</p>
         </div>
         <p className="text-sm font-bold font-mono tracking-tight text-slate-200">3D KONSTRUKTOR v1.1</p>
         <div className="h-px w-full bg-white/10 my-3" />
         <p className="text-[9px] text-slate-400 leading-relaxed uppercase font-bold tracking-widest">Orbit: Lewy przycisk<br/>Zoom: Scroll<br/>Pan: Prawy przycisk</p>
      </div>

      <div className="absolute top-8 left-8 flex flex-col gap-3">
         <div className="px-5 py-2 bg-brand/10 backdrop-blur-md border border-brand/20 rounded-2xl text-white text-[10px] font-black uppercase tracking-widest flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-brand shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
            Tryb: Geometria Parametryczna
         </div>
         <div className="px-5 py-2 bg-white/5 backdrop-blur-md border border-white/10 rounded-2xl text-slate-300 text-[10px] font-black uppercase tracking-widest">
            {props.name || "Nowy Modu"}
         </div>
      </div>
    </div>
  );
}
