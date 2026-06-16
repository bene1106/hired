import '@testing-library/jest-dom/vitest'

import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest'

import { resetMockState } from './handlers'
import { server } from './server'

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
beforeEach(() => resetMockState())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

const store = new Map()
const localStorageMock = {
  getItem: vi.fn((key: string) => store.get(key) || null),
  setItem: vi.fn((key: string, value: string) => store.set(key, value.toString())),
  removeItem: vi.fn((key: string) => store.delete(key)),
  clear: vi.fn(() => store.clear()),
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
})
Object.defineProperty(global, 'localStorage', {
  value: localStorageMock,
  writable: true,
})
