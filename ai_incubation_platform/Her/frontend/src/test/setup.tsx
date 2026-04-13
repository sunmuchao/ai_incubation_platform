/**
 * Jest 测试设置文件
 */
import '@testing-library/jest-dom'

// Mock global fetch
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    status: 200,
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
    headers: new Headers(),
  })
) as any

// Mock Headers
global.Headers = class Headers {
  private headers: Record<string, string> = {}
  append(name: string, value: string) { this.headers[name] = value }
  get(name: string) { return this.headers[name] || null }
  set(name: string, value: string) { this.headers[name] = value }
}

// Mock Response
global.Response = class Response {
  ok = true
  status = 200
  headers = new Headers()
  json() { return Promise.resolve({}) }
  text() { return Promise.resolve('') }
} as any

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
})

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
}
Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

// Mock Ant Design 组件
jest.mock('antd', () => {
  const actualAntd = jest.requireActual('antd')
  return {
    ...actualAntd,
    Spin: ({ children, tip }) => (
      <div data-testid="spin" data-tip={tip}>
        {children}
      </div>
    ),
    Empty: ({ description, image }) => (
      <div data-testid="empty">{description}</div>
    ),
    Modal: ({ children, open, title, onCancel }) =>
      open ? (
        <div data-testid="modal" onClick={onCancel}>
          {title}
          {children}
        </div>
      ) : null,
  }
})
