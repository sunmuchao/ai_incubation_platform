/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  images: {
    domains: ['localhost'],
  },
  env: {
    API_BASE_URL: process.env.API_BASE_URL || 'http://localhost:8004',
  },
  // 开发服务器端口
  experimental: {
    // Next.js 14 使用 server 配置端口
  },
}

module.exports = nextConfig
