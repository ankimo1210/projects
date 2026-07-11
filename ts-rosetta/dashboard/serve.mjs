// Zero-dependency static server for the dashboard (port 8080).
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = dirname(fileURLToPath(import.meta.url));

createServer(async (req, res) => {
  try {
    const html = await readFile(join(root, 'index.html'));
    res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
    res.end(html);
  } catch {
    res.writeHead(404).end('not found');
  }
}).listen(8080, () => {
  console.log('[dashboard] http://localhost:8080');
});
