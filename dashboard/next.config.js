/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  typescript: { ignoreBuildErrors: true },
  eslint: { ignoreDuringBuilds: true },

  // Proxy /api/* to the backend — works both server-side and client-side
  async rewrites() {
    const backend = process.env.API_URL || 'http://localhost:8001'
    return [
      {
        source: '/api/:path*',
        destination: `${backend}/api/:path*`,
      },
    ]
  },
}
module.exports = nextConfig
