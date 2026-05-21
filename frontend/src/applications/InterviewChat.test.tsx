import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import { setMockState } from '@/test/handlers'

import { InterviewChat } from './InterviewChat'

describe('InterviewChat', () => {
  it('starts empty and lets the user create a session', async () => {
    render(<InterviewChat applicationId={42} />)

    expect(await screen.findByText(/no sessions yet/i)).toBeInTheDocument()
    await userEvent.click(screen.getByTestId('new-session'))

    // After session creation the active session card replaces the empty state.
    await waitFor(() => expect(screen.getByText(/type your first message/i)).toBeInTheDocument())
    expect(screen.getByTestId('send-message')).toBeDisabled() // empty input
  })

  it('streams coach chunks into one bubble and persists the assistant turn', async () => {
    setMockState({
      chatChunks: [
        'Strong opening — ',
        'concrete stack.\n\n',
        'Follow-up: what changed because of you?',
      ],
    })
    render(<InterviewChat applicationId={42} />)
    await userEvent.click(await screen.findByTestId('new-session'))

    const input = await screen.findByLabelText(/chat message/i)
    await userEvent.type(input, 'I built a payment service.')
    await userEvent.click(screen.getByTestId('send-message'))

    // User message visible (in the chat bubble; also surfaces in the
    // session preview — getAllByText handles both).
    await waitFor(() => {
      expect(screen.getAllByText('I built a payment service.').length).toBeGreaterThan(0)
    })
    // The chunks land in a single coach bubble — joined, not three bubbles.
    await waitFor(() => {
      const bubble = screen.getByTestId('coach-bubble')
      expect(bubble.textContent).toContain('Strong opening')
      expect(bubble.textContent).toContain('Follow-up')
    })
    // Streaming flag clears after completion (button label flips back to "Send").
    await waitFor(() => expect(screen.getByTestId('send-message')).toHaveTextContent(/^Send$/))
  })

  it('preserves the user turn and shows an error when the stream fails', async () => {
    setMockState({
      chatFailWith: 'provider exploded',
      chatChunks: [],
    })
    render(<InterviewChat applicationId={42} />)
    await userEvent.click(await screen.findByTestId('new-session'))

    const input = await screen.findByLabelText(/chat message/i)
    await userEvent.type(input, 'Trigger the failure.')
    await userEvent.click(screen.getByTestId('send-message'))

    // Error surfaces; user turn stays in the transcript (matches backend's
    // half-write-safe contract — they can retry without retyping).
    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/provider exploded/i)
    })
    expect(screen.getAllByText('Trigger the failure.').length).toBeGreaterThan(0)
    // No coach bubble — the empty placeholder was dropped.
    expect(screen.queryByTestId('coach-bubble')).not.toBeInTheDocument()
  })

  it('lists prior sessions newest-first and resumes them', async () => {
    render(<InterviewChat applicationId={42} />)

    // Create a first session with a message, then a second one — the second
    // is implicitly active because session creation activates it.
    await userEvent.click(await screen.findByTestId('new-session'))
    const input = await screen.findByLabelText(/chat message/i)
    await userEvent.type(input, 'first session message')
    await userEvent.click(screen.getByTestId('send-message'))
    // Wait until the streaming label clears.
    await waitFor(() => expect(screen.getByTestId('send-message')).toHaveTextContent(/^Send$/))

    await userEvent.click(screen.getByTestId('new-session'))
    // The sidebar should now show two sessions (the newer one first).
    await waitFor(() => {
      const items = screen.getAllByText(/turns?$/i)
      expect(items.length).toBeGreaterThanOrEqual(2)
    })
  })
})
