import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  
  // Development server configuration
  server: {
    port: 5173,
    cors: true,
    proxy: {
      // Proxy API requests to Flask backend
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      },
      '/auth': {
        target: 'http://localhost:5000',
        changeOrigin: true,
      }
    }
  },
  
  // Build configuration
  build: {
    // Output directory (Flask will serve from here)
    outDir: 'dist',
    assetsDir: 'assets',
    
    // Generate manifest for asset paths
    manifest: true,
    
    rollupOptions: {
      input: './src/main.jsx'
    }
  }
})