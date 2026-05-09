import '@testing-library/jest-dom/vitest'

import { afterAll, afterEach, beforeAll, beforeEach } from 'vitest'

import { resetMockState } from './handlers'
import { server } from './server'

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
beforeEach(() => resetMockState())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
