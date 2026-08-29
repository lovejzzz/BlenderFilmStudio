import { existsSync, renameSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const serverDirectory = join(repositoryRoot, 'dist', 'server');
const workerEntry = join(serverDirectory, 'index.js');
const vinextEntry = join(serverDirectory, 'vinext-handler.js');

if (!existsSync(workerEntry)) {
  throw new Error(`Sites worker adapter: missing ${workerEntry}`);
}
if (existsSync(vinextEntry)) {
  throw new Error(`Sites worker adapter: refusing to overwrite ${vinextEntry}`);
}

renameSync(workerEntry, vinextEntry);
writeFileSync(workerEntry, `import handler from './vinext-handler.js';
export * from './vinext-handler.js';

const fetchHandler = typeof handler === 'function'
  ? handler
  : handler && typeof handler.fetch === 'function'
    ? handler.fetch.bind(handler)
    : null;

if (!fetchHandler) {
  throw new TypeError('vinext default export must be callable or expose fetch');
}

export default {
  fetch(request, env, context) {
    return fetchHandler(request, env, context);
  },
};
`);

const worker = await import(`${pathToFileURL(workerEntry).href}?sites-adapter-check=1`);
if (typeof worker.default?.fetch !== 'function') {
  throw new TypeError('Sites worker adapter did not produce default.fetch');
}

console.log('Sites worker adapter: default.fetch verified');
