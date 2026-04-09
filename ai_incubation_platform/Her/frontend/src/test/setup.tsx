/**
 * Jest 测试设置文件
 */
import '@testing-library/jest-dom'

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
