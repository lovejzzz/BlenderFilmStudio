import { existsSync, renameSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';

const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const serverDirectory = join(repositoryRoot, 'dist', 'server');
const workerEntry = join(serverDirectory, 'index.js');
const vinextEntry = join(serverDirectory, 'vinext-handler.js');
const bundledEntry = join(serverDirectory, 'sites-worker.js');

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

const bundleResult = await build({
  entryPoints: [workerEntry],
  outfile: bundledEntry,
  bundle: true,
  conditions: ['workerd', 'worker', 'browser', 'import', 'module'],
  external: ['node:*', 'cloudflare:*'],
  format: 'esm',
  logLevel: 'warning',
  metafile: true,
  platform: 'neutral',
  target: 'es2022',
});
renameSync(bundledEntry, workerEntry);

const externalImports = Object.values(bundleResult.metafile.outputs)
  .flatMap(output => output.imports)
  .filter(importRecord => importRecord.external)
  .map(importRecord => importRecord.path);
const unsupportedBareImports = externalImports.filter(specifier =>
  !specifier.startsWith('node:') && !specifier.startsWith('cloudflare:')
);
if (unsupportedBareImports.length > 0) {
  throw new Error(`Sites worker bundle retained bare imports: ${[...new Set(unsupportedBareImports)].join(', ')}`);
}

const bundledWorker = await import(`${pathToFileURL(workerEntry).href}?sites-bundle-check=1`);
if (typeof bundledWorker.default?.fetch !== 'function') {
  throw new TypeError('Bundled Sites worker did not preserve default.fetch');
}

console.log('Sites worker adapter: default.fetch verified; runtime dependencies bundled');
