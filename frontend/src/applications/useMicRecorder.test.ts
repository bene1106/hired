import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useMicRecorder } from './useMicRecorder'

const origMediaDevices = Object.getOwnPropertyDescriptor(navigator, 'mediaDevices')
const origMediaRecorder = (globalThis as { MediaRecorder?: unknown }).MediaRecorder

function setMedia(getUserMedia: (() => Promise<MediaStream>) | undefined) {
  Object.defineProperty(navigator, 'mediaDevices', {
    value: getUserMedia ? { getUserMedia } : undefined,
    configurable: true,
  })
  ;(globalThis as { MediaRecorder?: unknown }).MediaRecorder = getUserMedia
    ? class {
        start() {}
        stop() {}
        state = 'inactive'
      }
    : undefined
}

afterEach(() => {
  if (origMediaDevices) Object.defineProperty(navigator, 'mediaDevices', origMediaDevices)
  ;(globalThis as { MediaRecorder?: unknown }).MediaRecorder = origMediaRecorder
  vi.restoreAllMocks()
})

describe('useMicRecorder', () => {
  it('reports unsupported when the APIs are absent', () => {
    setMedia(undefined)
    const { result } = renderHook(() => useMicRecorder())
    expect(result.current.supported).toBe(false)
  })

  it('moves to granted when permission is allowed', async () => {
    const fakeStream = { getTracks: () => [] } as unknown as MediaStream
    setMedia(() => Promise.resolve(fakeStream))
    const { result } = renderHook(() => useMicRecorder())
    expect(result.current.permission).toBe('idle')

    await act(async () => {
      await result.current.requestPermission()
    })
    expect(result.current.permission).toBe('granted')
  })

  it('moves to denied when permission is blocked', async () => {
    setMedia(() => Promise.reject(new Error('blocked')))
    const { result } = renderHook(() => useMicRecorder())

    await act(async () => {
      await result.current.requestPermission()
    })
    expect(result.current.permission).toBe('denied')
  })
})
