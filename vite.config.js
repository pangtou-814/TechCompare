import { defineConfig } from 'vite';

export default defineConfig(({ command }) => ({
  base: command === 'serve' && process.env.npm_lifecycle_event === 'dev' ? '/' : '/TechCompare/',
}));
