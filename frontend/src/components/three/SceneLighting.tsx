export function SceneLighting() {
  return (
    <>
      <ambientLight intensity={1.6} />
      <directionalLight position={[10, 20, 10]} intensity={1.8} />
    </>
  )
}
