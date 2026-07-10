import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { visualizer } from 'rollup-plugin-visualizer'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    visualizer({
      open:true, //打包完成自动打开页面
      filename:'dist/stats.html'
    })
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:4231',
        changeOrigin: true,
      },
      '/admin': {
        target: 'http://localhost:4231',
        changeOrigin: true,
      },
    }
  }
})
