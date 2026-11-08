import { useFrame, useThree } from '@react-three/fiber'
import { useEffect, useRef } from 'react'
import { Vector3 } from 'three'
import { useCameraStore } from '../../store/useCameraStore'
import { SCENE_CENTERING_OFFSET, type RunNodeLayout } from '../../utils/coordinate-mapper'

const FOCUS_DISTANCE = 11
const FLIGHT_SPEED = 3.5
const ARRIVAL_THRESHOLD = 0.01

interface OrbitControlsLike {
  target: Vector3
  update: () => void
  addEventListener: (type: 'start', listener: () => void) => void
  removeEventListener: (type: 'start', listener: () => void) => void
}

interface Flight {
  position: Vector3
  lookAt: Vector3
}

/** Flies the camera to `useCameraStore.targetRunId`, keeping the current viewing angle. */
export function CameraController({ nodes }: { nodes: RunNodeLayout[] }) {
  const camera = useThree((state) => state.camera)
  const controls = useThree((state) => state.controls) as unknown as OrbitControlsLike | null
  const targetRunId = useCameraStore((state) => state.targetRunId)
  const requestId = useCameraStore((state) => state.requestId)
  const handledRequest = useRef(useCameraStore.getState().requestId)
  const flight = useRef<Flight | null>(null)

  useEffect(() => {
    if (!controls || requestId === handledRequest.current) return
    handledRequest.current = requestId
    const node = nodes.find((candidate) => candidate.run.id === targetRunId)
    if (!node) return

    const lookAt = new Vector3(...node.position).addScalar(SCENE_CENTERING_OFFSET)
    const direction = camera.position.clone().sub(controls.target).normalize()
    flight.current = {
      lookAt,
      position: lookAt.clone().addScaledVector(direction, FOCUS_DISTANCE),
    }
  }, [camera, controls, nodes, requestId, targetRunId])

  // The user grabbing the view always wins over an animation in progress.
  useEffect(() => {
    if (!controls) return
    const cancelFlight = () => {
      flight.current = null
    }
    controls.addEventListener('start', cancelFlight)
    return () => controls.removeEventListener('start', cancelFlight)
  }, [controls])

  useFrame((_, delta) => {
    const current = flight.current
    if (!current || !controls) return
    const step = 1 - Math.exp(-FLIGHT_SPEED * delta)
    camera.position.lerp(current.position, step)
    controls.target.lerp(current.lookAt, step)
    controls.update()
    if (camera.position.distanceTo(current.position) < ARRIVAL_THRESHOLD) flight.current = null
  })

  return null
}
