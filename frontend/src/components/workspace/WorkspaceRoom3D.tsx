"use client";

import { Canvas, type ThreeEvent } from "@react-three/fiber";
import { Edges, OrbitControls, PerspectiveCamera } from "@react-three/drei";

type WorkspaceObstacleType = "window" | "door" | "column" | "pipe" | "shaft" | "utility" | "socket";
type RoomGeometryPreset = "flat" | "left_column" | "center_column" | "double_column";

type ModuleWarning = {
  outOfWall: boolean;
  overlap: boolean;
  obstacleIntersections: string[];
};

type ObstacleWarning = {
  outOfWall: boolean;
};

type WorkspaceRoom3DModule = {
  id: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  depth: number;
  selected: boolean;
  warning: ModuleWarning;
};

type WorkspaceRoom3DObstacle = {
  id: string;
  type: WorkspaceObstacleType;
  x: number;
  y: number;
  width: number;
  height: number;
  depth: number;
  selected: boolean;
  warning: ObstacleWarning;
};

type RoomGeometryBlock = {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  depth: number;
};

export type WorkspaceRoom3DPoint = {
  id: string;
  type: string;
  x: number;
  y: number;
};

type WorkspaceRoom3DProps = {
  wallWidth: number;
  wallHeight: number;
  roomDepth?: number;
  roomGeometryPreset?: RoomGeometryPreset;
  roomGeometryBlocks?: RoomGeometryBlock[];
  modules: WorkspaceRoom3DModule[];
  obstacles: WorkspaceRoom3DObstacle[];
  points?: WorkspaceRoom3DPoint[];
  onSelectModule: (moduleId: string) => void;
  onSelectObstacle: (obstacleId: string) => void;
  onWallPlace: (xMm: number, yMm: number) => void;
};

const OBSTACLE_COLOR: Record<WorkspaceObstacleType, string> = {
  window: "#a6d8ff",
  door: "#ce4a3f",
  column: "#d8b084",
  pipe: "#f5d46d",
  shaft: "#e8ba5f",
  utility: "#cbd5e1",
  socket: "#f3f4f6",
};

function wallXToWorld(xMm: number, wallWidthMm: number) {
  return -wallWidthMm / 2000 + xMm / 1000;
}

function wallYToWorld(yMm: number, wallHeightMm: number) {
  return -wallHeightMm / 2000 + yMm / 1000;
}

function ModuleMesh({
  item,
  wallWidth,
  wallHeight,
  backWallZ,
  onSelect,
}: {
  item: WorkspaceRoom3DModule;
  wallWidth: number;
  wallHeight: number;
  backWallZ: number;
  onSelect: () => void;
}) {
  const width = item.width / 1000;
  const height = item.height / 1000;
  const depth = Math.max(0.35, item.depth / 1000);
  const centerX = wallXToWorld(item.x + item.width * 0.5, wallWidth);
  const centerY = wallYToWorld(item.y + item.height * 0.5, wallHeight);
  const centerZ = backWallZ + depth * 0.5;
  const hasWarning = item.warning.outOfWall || item.warning.overlap || item.warning.obstacleIntersections.length > 0;
  const fill = item.selected ? "#f5d6a6" : hasWarning ? "#f1c7a8" : "#f4efe7";
  const edge = item.warning.outOfWall ? "#dc2626" : item.selected ? "#fb923c" : hasWarning ? "#f59e0b" : "#9ca3af";

  return (
    <group
      position={[centerX, centerY, centerZ]}
      onPointerDown={(event) => {
        event.stopPropagation();
        onSelect();
      }}
    >
      <mesh castShadow receiveShadow>
        <boxGeometry args={[width, height, depth]} />
        <meshStandardMaterial color={fill} />
        <Edges color={edge} />
      </mesh>
      <mesh position={[width * 0.35, 0, depth * 0.5 + 0.002]}>
        <boxGeometry args={[0.01, height * 0.5, 0.014]} />
        <meshStandardMaterial color="#8b5e3c" />
      </mesh>
      {hasWarning ? (
        <mesh position={[width * 0.48, height * 0.48, depth * 0.52]}>
          <sphereGeometry args={[0.05, 20, 20]} />
          <meshStandardMaterial color="#ef4444" emissive="#ef4444" emissiveIntensity={0.35} />
        </mesh>
      ) : null}
    </group>
  );
}

function ObstacleMesh({
  item,
  wallWidth,
  wallHeight,
  backWallZ,
  onSelect,
}: {
  item: WorkspaceRoom3DObstacle;
  wallWidth: number;
  wallHeight: number;
  backWallZ: number;
  onSelect: () => void;
}) {
  const width = item.width / 1000;
  const height = item.height / 1000;
  const depth = Math.max(0.025, item.depth / 1000 || 0.025);
  const centerX = wallXToWorld(item.x + item.width * 0.5, wallWidth);
  const centerY = wallYToWorld(item.y + item.height * 0.5, wallHeight);
  const centerZ = backWallZ + depth * 0.5 + 0.004;
  const edge = item.warning.outOfWall ? "#dc2626" : item.selected ? "#0ea5e9" : "#475569";

  return (
    <group
      position={[centerX, centerY, centerZ]}
      onPointerDown={(event) => {
        event.stopPropagation();
        onSelect();
      }}
    >
      <mesh castShadow receiveShadow>
        <boxGeometry args={[width, height, depth]} />
        <meshStandardMaterial
          color={OBSTACLE_COLOR[item.type]}
          transparent={item.type === "window" || item.type === "socket" || item.type === "utility"}
          opacity={item.type === "window" ? 0.6 : 0.95}
        />
        <Edges color={edge} />
      </mesh>
    </group>
  );
}

function UtilityPointMesh({
  item,
  wallWidth,
  wallHeight,
  backWallZ,
}: {
  item: WorkspaceRoom3DPoint;
  wallWidth: number;
  wallHeight: number;
  backWallZ: number;
}) {
  const centerX = wallXToWorld(item.x, wallWidth);
  const centerY = wallYToWorld(item.y, wallHeight);
  const centerZ = backWallZ + 0.02;

  let color = "#3b82f6"; // default blue
  if (item.type === "droplet") color = "#06b6d4"; // cyan
  if (item.type === "flame") color = "#f97316"; // orange

  return (
    <group position={[centerX, centerY, centerZ]}>
      <mesh castShadow receiveShadow>
        <boxGeometry args={[0.08, 0.08, 0.04]} />
        <meshStandardMaterial color={color} />
        <Edges color="#ffffff" />
      </mesh>
    </group>
  );
}

function RoomGeometryMesh({
  block,
  wallWidth,
  wallHeight,
  backWallZ,
}: {
  block: RoomGeometryBlock;
  wallWidth: number;
  wallHeight: number;
  backWallZ: number;
}) {
  const width = Math.max(0.08, block.width / 1000);
  const height = Math.max(0.35, block.height / 1000);
  const depth = Math.max(0.12, block.depth / 1000);
  const centerX = wallXToWorld(block.x + block.width * 0.5, wallWidth);
  const centerY = wallYToWorld(block.y + block.height * 0.5, wallHeight);
  const centerZ = backWallZ + depth * 0.5 + 0.001;

  return (
    <group position={[centerX, centerY, centerZ]}>
      <mesh castShadow receiveShadow>
        <boxGeometry args={[width, height, depth]} />
        <meshStandardMaterial color="#e5eaf0" roughness={0.72} />
        <Edges color="#a5afbb" />
      </mesh>
    </group>
  );
}

function WallPlacementPlane({
  wallWidth,
  wallHeight,
  backWallZ,
  onWallPlace,
}: {
  wallWidth: number;
  wallHeight: number;
  backWallZ: number;
  onWallPlace: (xMm: number, yMm: number) => void;
}) {
  return (
    <mesh
      position={[0, 0, backWallZ + 0.01]}
      onDoubleClick={(event: ThreeEvent<MouseEvent>) => {
        event.stopPropagation();
        const uv = event.uv;
        if (!uv) return;
        const xMm = Math.round(uv.x * wallWidth);
        const yMm = Math.round((1 - uv.y) * wallHeight);
        onWallPlace(xMm, yMm);
      }}
    >
      <planeGeometry args={[wallWidth / 1000, wallHeight / 1000]} />
      <meshBasicMaterial transparent opacity={0} />
    </mesh>
  );
}

export default function WorkspaceRoom3D({
  wallWidth,
  wallHeight,
  roomDepth,
  roomGeometryPreset,
  roomGeometryBlocks,
  modules,
  obstacles,
  points,
  onSelectModule,
  onSelectObstacle,
  onWallPlace,
}: WorkspaceRoom3DProps) {
  const safeRoomDepth = Math.max(2.8, (roomDepth ?? Math.max(3200, wallWidth * 0.78)) / 1000);
  const wallWidthM = wallWidth / 1000;
  const wallHeightM = wallHeight / 1000;
  const backWallZ = -safeRoomDepth * 0.5;
  const floorY = -wallHeightM * 0.5;
  const geometryBlocks = roomGeometryBlocks ?? [];
  const hasRoomGeometry = roomGeometryPreset && roomGeometryPreset !== "flat";

  return (
    <div className="h-full w-full">
      <Canvas shadows dpr={[1, 2]}>
        <color attach="background" args={["#eef3f8"]} />
        <PerspectiveCamera makeDefault position={[wallWidthM * 0.34, wallHeightM * 0.34, safeRoomDepth * 0.82]} fov={44} />
        <ambientLight intensity={1.15} />
        <directionalLight position={[3.5, 4.5, 4.5]} intensity={1.8} castShadow shadow-mapSize-width={2048} shadow-mapSize-height={2048} />
        <directionalLight position={[-3, 2.6, -1]} intensity={0.6} />

        <OrbitControls
          makeDefault
          enablePan
          enableZoom
          enableDamping
          dampingFactor={0.08}
          rotateSpeed={0.9}
          minDistance={1.8}
          maxDistance={10}
          minPolarAngle={0.12}
          maxPolarAngle={Math.PI * 0.93}
          target={[0, -wallHeightM * 0.15, backWallZ + safeRoomDepth * 0.12]}
        />

        <mesh position={[0, 0, backWallZ]} receiveShadow>
          <planeGeometry args={[wallWidthM, wallHeightM]} />
          <meshStandardMaterial color={hasRoomGeometry ? "#f8f2e8" : "#faf6ee"} />
        </mesh>

        <mesh position={[-wallWidthM * 0.5, 0, 0]} rotation={[0, Math.PI / 2, 0]} receiveShadow>
          <planeGeometry args={[safeRoomDepth, wallHeightM]} />
          <meshStandardMaterial color="#f3f7fb" />
        </mesh>

        <mesh position={[wallWidthM * 0.5, 0, 0]} rotation={[0, -Math.PI / 2, 0]} receiveShadow>
          <planeGeometry args={[safeRoomDepth, wallHeightM]} />
          <meshStandardMaterial color="#f3f7fb" />
        </mesh>

        <mesh position={[0, floorY, 0]} rotation={[-Math.PI / 2, 0, 0]} receiveShadow>
          <planeGeometry args={[wallWidthM + 1.6, safeRoomDepth + 1.2]} />
          <meshStandardMaterial color="#e7edf3" />
        </mesh>

        <gridHelper
          args={[Math.max(wallWidthM + 1.2, safeRoomDepth + 0.6), Math.round(Math.max(wallWidthM + 1.2, safeRoomDepth + 0.6) * 5), "#cbd5e1", "#dbe4ec"]}
          position={[0, floorY + 0.002, 0]}
        />

        {geometryBlocks.map((block) => (
          <RoomGeometryMesh
            key={block.id}
            block={block}
            wallWidth={wallWidth}
            wallHeight={wallHeight}
            backWallZ={backWallZ}
          />
        ))}

        <WallPlacementPlane wallWidth={wallWidth} wallHeight={wallHeight} backWallZ={backWallZ} onWallPlace={onWallPlace} />

        {obstacles.map((item) => (
          <ObstacleMesh
            key={item.id}
            item={item}
            wallWidth={wallWidth}
            wallHeight={wallHeight}
            backWallZ={backWallZ}
            onSelect={() => onSelectObstacle(item.id)}
          />
        ))}

        {modules.map((item) => (
          <ModuleMesh
            key={item.id}
            item={item}
            wallWidth={wallWidth}
            wallHeight={wallHeight}
            backWallZ={backWallZ}
            onSelect={() => onSelectModule(item.id)}
          />
        ))}

        {(points || []).map((point) => (
          <UtilityPointMesh
            key={point.id}
            item={point}
            wallWidth={wallWidth}
            wallHeight={wallHeight}
            backWallZ={backWallZ}
          />
        ))}
      </Canvas>
    </div>
  );
}
