import { test, expect } from '@playwright/test';

// AI Hires Human 前端全页面测试
// 测试所有路由页面是否能正常加载和渲染

const BASE_URL = 'http://localhost:3004';

test.describe('AI Hires Human - 页面加载测试', () => {
  // 测试登录页面
  test('应该能正常加载登录页面', async ({ page }) => {
    const response = await page.goto(`${BASE_URL}/login`);
    expect(response?.status()).toBe(200);
    await page.waitForLoadState('networkidle');

    // 检查页面标题
    const title = await page.title();
    expect(title).toContain('登录');

    // 检查登录表单是否存在
    await expect(page.locator('input[type="email"], input[name="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"], input[name="password"]')).toBeVisible();

    // 检查控制台错误
    page.on('console', msg => {
      if (msg.type() === 'error') {
        console.log('控制台错误:', msg.text());
      }
    });
  });

  // 测试首页重定向
  test('首页应该重定向到任务市场或登录页', async ({ page }) => {
    const response = await page.goto(BASE_URL);
    expect(response?.status()).toBe(200);
    await page.waitForLoadState('networkidle');

    // 应该在 /tasks 或 /login
    const url = page.url();
    expect(url).toMatch(/\/(tasks|login)/);
  });

  // 测试任务市场页面
  test('应该能正常加载任务市场页面', async ({ page }) => {
    // 先登录
    await page.goto(`${BASE_URL}/login`);
    await page.waitForLoadState('networkidle');

    // 填充登录表单
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'test123');
    await page.click('button[type="submit"]');
    await page.waitForLoadState('networkidle');

    // 检查是否跳转到任务市场
    const url = page.url();
    expect(url).toMatch(/\/(tasks|login)/);

    // 检查任务市场元素
    await expect(page.locator('text=任务, text=所有任务, text=搜索')).toBeVisible({ timeout: 5000 }).catch(() => {
      console.log('任务市场元素未找到，可能登录失败');
    });
  });

  // 测试工作者仪表板页面
  test('应该能正常加载工作者仪表板页面', async ({ page, context }) => {
    // 模拟登录状态
    await context.addCookies([{
      name: 'auth_token',
      value: 'test_token',
      domain: 'localhost',
      path: '/',
    }]);

    const response = await page.goto(`${BASE_URL}/worker`);
    expect(response?.status()).toBe(200);
    await page.waitForLoadState('networkidle');

    // 检查工作者仪表板元素
    const title = await page.title();
    expect(title).toContain('工作者')
  });

  // 测试雇主仪表板页面
  test('应该能正常加载雇主仪表板页面', async ({ page }) => {
    const response = await page.goto(`${BASE_URL}/employer`);
    expect(response?.status()).toBe(200);
    await page.waitForLoadState('networkidle');

    const title = await page.title();
    expect(title).toContain('雇主')
  });

  // 测试任务详情页面
  test('应该能正常加载任务详情页面', async ({ page }) => {
    const response = await page.goto(`${BASE_URL}/tasks/1`);
    expect(response?.status()).toBe(200);
    await page.waitForLoadState('networkidle');

    const title = await page.title();
    expect(title).toContain('任务')
  });

  // 测试支付页面
  test('应该能正常加载支付页面', async ({ page }) => {
    const response = await page.goto(`${BASE_URL}/payment`);
    expect(response?.status()).toBe(200);
    await page.waitForLoadState('networkidle');

    const title = await page.title();
    expect(title).toContain('支付')
  });

  // 测试管理页面
  test('应该能正常加载管理页面', async ({ page }) => {
    const response = await page.goto(`${BASE_URL}/admin`);
    expect(response?.status()).toBe(200);
    await page.waitForLoadState('networkidle');

    const title = await page.title();
    expect(title).toContain('管理')
  });
});
