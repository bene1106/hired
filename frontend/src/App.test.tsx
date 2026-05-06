import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import App from './App'

describe('App', () => {
  it('renders the title and the health check button', () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: /hired\./i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /run health check/i })).toBeInTheDocument()
  })
})
