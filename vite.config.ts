import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import electron from 'vite-plugin-electron'
import renderer from 'vite-plugin-electron-renderer'
import path from 'path'
import { createRequire } from 'module'

const require = createRequire(import.meta.url)
const pkg = require('./package.json')

export default defineConfig({
  plugins: [
    react(),
    electron([
      {
        entry: 'src/main/index.ts',
        vite: {
          build: {
            outDir: 'dist-electron/main',
            rollupOptions: {
              external: ['electron'],
            },
          },
        },
      },
      {
        entry: 'src/main/preload.ts',
        onstart(args) {
          args.reload()
        },
        vite: {
          build: {
            outDir: 'dist-electron/preload',
          },
        },
      },
    ]),
    renderer(),
  ],
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },
  // Pre-bundle the GIF snapshot deps (CommonJS) so they resolve reliably in the
  // renderer without a mid-session re-optimize (which can break the first import).
  optimizeDeps: {
    include: ['gifuct-js', 'gifenc'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src/renderer'),
    },
  },
})
