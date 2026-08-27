/**
 * Local static server for the console. Development only.
 *
 * GitHub Pages serves apps/console/ directly, so nothing here ships — this
 * exists so the console can be opened locally without a build step.
 */
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = resolve(fileURLToPath(new URL('.', import.meta.url)));
const PORT = Number(process.env.PORT ?? 8477);

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
};

const server = createServer((req, res) => {
  void (async () => {
    const url = new URL(req.url ?? '/', `http://localhost:${PORT}`);
    const requested = url.pathname === '/' ? '/index.html' : url.pathname;

    // Resolve inside ROOT only — a path that escapes it is a traversal attempt.
    const filePath = join(ROOT, normalize(requested).replace(/^(\.\.[/\\])+/, ''));
    if (!filePath.startsWith(ROOT)) {
      res.writeHead(403, { 'Content-Type': 'text/plain' });
      res.end('Forbidden');
      return;
    }

    try {
      const body = await readFile(filePath);
      res.writeHead(200, {
        'Content-Type': TYPES[extname(filePath)] ?? 'application/octet-stream',
        'Cache-Control': 'no-store',
      });
      res.end(body);
    } catch {
      res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
      res.end(`Not found: ${requested}`);
    }
  })();
});

server.listen(PORT, '127.0.0.1', () => {
  console.log(`BAi Console on http://127.0.0.1:${PORT}`);
});
