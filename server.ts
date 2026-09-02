import express, { Request, Response } from 'express';
import path from 'path';
import { createServer as createViteServer } from 'vite';
import { apiRouter } from './src/server/routes/api';
import { logger } from './src/core/logging/Logger';

async function startServer() {
  const app = express();
  const PORT = 3000;

  // JSON Body parsing
  app.use(express.json({ limit: '50mb' }));
  app.use(express.urlencoded({ extended: true, limit: '50mb' }));

  // Request logging middleware
  app.use((req, res, next) => {
    logger.debug('HTTP', `${req.method} ${req.url}`);
    next();
  });

  // Mount API Routes
  app.use('/api', apiRouter);

  // Global Error Handler for API
  app.use('/api', (err: any, req: Request, res: Response, next: any) => {
    logger.error('API_HANDLER', 'Unhandled Express API error', err);
    res.status(500).json({
      success: false,
      error: err.message || 'Internal Server Error',
      timestamp: new Date().toISOString()
    });
  });

  // Vite middleware in dev / Static files in production
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa'
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    logger.info('SERVER', `STRUCTURE-X Foundation Server running on http://0.0.0.0:${PORT} (${process.env.NODE_ENV || 'development'})`);
  });
}

startServer().catch(err => {
  console.error('Fatal Server Startup Error:', err);
  process.exit(1);
});
