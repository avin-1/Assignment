import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/upload-candidates': 'http://127.0.0.1:5000',
      '/start-session': 'http://127.0.0.1:5000',
      '/responses': 'http://127.0.0.1:5000',
      '/chat': 'http://127.0.0.1:5000',
      '/api': 'http://127.0.0.1:5000',
    }
  }
})
