import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Stage, useGLTF } from "@react-three/drei";

type ModelProps = {
  url: string;
};

function LoadedModel({ url }: ModelProps) {
  const asset = useGLTF(url);
  return <primitive object={asset.scene} />;
}

type ModelViewerProps = {
  modelUrl: string | null;
};

export function ModelViewer({ modelUrl }: ModelViewerProps) {
  if (!modelUrl) {
    return <div className="viewer-empty">Run a job to load a GLB preview here.</div>;
  }

  return (
    <div className="viewer-shell">
      <Canvas camera={{ position: [2.5, 2, 2.5], fov: 45 }}>
        <color attach="background" args={["#0b1017"]} />
        <ambientLight intensity={0.8} />
        <Suspense fallback={null}>
          <Stage intensity={0.9} environment="city">
            <LoadedModel url={modelUrl} />
          </Stage>
        </Suspense>
        <OrbitControls makeDefault />
      </Canvas>
    </div>
  );
}
