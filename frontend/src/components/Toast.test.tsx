import { act, render, renderHook, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { Toast, useToast } from './Toast'

describe('Toast', () => {
  it('renders nothing when message is null', () => {
    const { container } = render(<Toast message={null} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders the message with role="status" when set', () => {
    render(<Toast message="Cover letter saved" />)
    const status = screen.getByRole('status')
    expect(status).toHaveTextContent('Cover letter saved')
    expect(status).toHaveAttribute('aria-live', 'polite')
  })
})

describe('useToast', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('show sets the message and it auto-clears after the timeout', () => {
    const { result } = renderHook(() => useToast())
    expect(result.current.message).toBeNull()

    act(() => result.current.show('Saved'))
    expect(result.current.message).toBe('Saved')

    act(() => vi.advanceTimersByTime(2200))
    expect(result.current.message).toBeNull()
  })

  it('re-showing resets the auto-clear timer', () => {
    const { result } = renderHook(() => useToast())

    act(() => result.current.show('First'))
    act(() => vi.advanceTimersByTime(2000))
    expect(result.current.message).toBe('First')

    act(() => result.current.show('Second'))
    expect(result.current.message).toBe('Second')

    // 2000ms after the re-show is still before the new 2200ms deadline.
    act(() => vi.advanceTimersByTime(2000))
    expect(result.current.message).toBe('Second')

    act(() => vi.advanceTimersByTime(200))
    expect(result.current.message).toBeNull()
  })
})
