/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    rollupOptions: {
      output: {
        // MapLibre is most of the bundle and changes rarely: give it its own
        // long-cached chunk so app deploys don't re-download it.
        manualChunks: {
          maplibre: ['maplibre-gl'],
          react: ['react', 'react-dom']
        }
      }
    },
    chunkSizeWarningLimit: 1100
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.ts']
  }
});
