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

  // ---- v0.3.2 hotfix regression tests ------------------------------------
  // These guard the three UI bugs the v0.3.1 Tauri smoke surfaced:
  //   Bug 1: user bubble rendered invisible (`text-bg` was an invalid
  //          Tailwind class, text fell back to inherited dark-on-dark)
  //   Bug 2: long session previews overflowed the sidebar (flex-1 without
  //          min-w-0 doesn't allow truncate to engage)
  //   Bug 3: confidence slider lacked an actionable label / helper copy
  //          so users couldn't tell it was an input
  // The asserts target the structural fix (class name / DOM presence)
  // rather than visual rendering, because jsdom doesn't compute CSS.

  it('user bubble carries the inverted text colour (Bug 1 regression)', async () => {
    setMockState({ chatChunks: ['ok'] })
    render(<InterviewChat applicationId={42} />)
    await userEvent.click(await screen.findByTestId('new-session'))
    const input = await screen.findByLabelText(/chat message/i)
    await userEvent.type(input, 'visible user text')
    await userEvent.click(screen.getByTestId('send-message'))

    const bubble = await screen.findByTestId('user-bubble')
    expect(bubble).toHaveTextContent('visible user text')
    // The dark bubble (`bg-ink`) needs the inverted foreground or it
    // renders dark-on-dark. `text-paper` is the design token for that.
    expect(bubble.className).toContain('text-paper')
    expect(bubble.className).toContain('bg-ink')
  })

  it('session title truncates instead of overflowing the sidebar (Bug 2 regression)', async () => {
    setMockState({ chatChunks: ['ok'] })
    render(<InterviewChat applicationId={42} />)
    await userEvent.click(await screen.findByTestId('new-session'))
    const input = await screen.findByLabelText(/chat message/i)
    await userEvent.type(
      input,
      'Ask me a behavioural question about a time I had to push back on a tech decision under a tight deadline',
    )
    await userEvent.click(screen.getByTestId('send-message'))

    // After the turn lands the preview is wired up. Find any session-N-title;
    // the latest session has the long preview we just typed.
    const titles = await screen.findAllByTestId(/^session-\d+-title$/)
    const titleEl = titles[0]
    expect(titleEl.className).toContain('truncate')
    // The button row needs min-w-0 so truncate engages — without it the
    // long string forces the flex item past the container width and the
    // text spills out instead of getting an ellipsis.
    const sessionButton = titleEl.closest('button')
    expect(sessionButton).not.toBeNull()
    expect(sessionButton!.className).toContain('min-w-0')
  })

  it('confidence slider has a visible prompt and per-session helper copy (Bug 3 regression)', async () => {
    render(<InterviewChat applicationId={42} />)
    await userEvent.click(await screen.findByTestId('new-session'))

    const slider = await screen.findByTestId('confidence-slider')
    // The new label is body-sized and label-shaped, not a tiny mono
    // caption you'd miss.
    expect(slider).toHaveTextContent(/how confident do you feel/i)
    // Honest copy: tell the user it's per-session and not graded.
    expect(slider).toHaveTextContent(/resets when you switch sessions/i)
    // The five segments are real radios the user can click; clicking a
    // segment changes the live label.
    const segment4 = screen.getByRole('radio', { name: /confidence 4/i })
    expect(segment4).toHaveAttribute('aria-checked', 'false')
    await userEvent.click(segment4)
    expect(screen.getByRole('radio', { name: /confidence 4/i })).toHaveAttribute(
      'aria-checked',
      'true',
    )
    expect(slider).toHaveTextContent(/Solid/) // CONFIDENCE_LABELS[3]
  })
})
