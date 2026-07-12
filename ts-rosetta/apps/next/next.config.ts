import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // @rosetta/core ships TypeScript source; let Next transpile it.
  transpilePackages: ['@rosetta/core'],
};

export default nextConfig;
