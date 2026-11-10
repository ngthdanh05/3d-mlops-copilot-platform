import { useEffect, useState, type RefObject } from 'react'

/**
 * Expands an element over the window, and asks the browser for real full-screen on top.
 * The state does not wait for the browser: iPhones lack the API, and embedded browsers may
 * never answer the request.
 */
export function useFullscreen(elementRef: RefObject<HTMLElement>) {
  const [isFullscreen, setFullscreen] = useState(false)

  useEffect(() => {
    if (!isFullscreen) return
    const exitOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setFullscreen(false)
    }
    const followBrowser = () => {
      if (!document.fullscreenElement) setFullscreen(false)
    }
    document.addEventListener('keydown', exitOnEscape)
    document.addEventListener('fullscreenchange', followBrowser)
    return () => {
      document.removeEventListener('keydown', exitOnEscape)
      document.removeEventListener('fullscreenchange', followBrowser)
    }
  }, [isFullscreen])

  const toggleFullscreen = () => {
    setFullscreen(!isFullscreen)
    const request = document.fullscreenElement
      ? document.exitFullscreen()
      : isFullscreen
        ? undefined
        : elementRef.current?.requestFullscreen?.()
    void request?.catch(() => undefined) // the element is already expanded either way
  }

  return { isFullscreen, toggleFullscreen }
}
