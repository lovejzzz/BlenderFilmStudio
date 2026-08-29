import { cpSync, existsSync, renameSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { build } from 'esbuild';

const repositoryRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const staticExportDirectory = join(repositoryRoot, 'out');
const serverDirectory = join(repositoryRoot, 'dist', 'server');
const clientDirectory = join(repositoryRoot, 'dist', 'client');
const workerEntry = join(serverDirectory, 'index.js');
const vinextEntry = join(serverDirectory, 'vinext-handler.js');
const ssrEntry = join(serverDirectory, 'ssr', 'index.js');
const bundledSsrEntry = join(serverDirectory, 'ssr', 'sites-ssr.js');

if (!existsSync(workerEntry)) {
  throw new Error(`Sites worker adapter: missing ${workerEntry}`);
}
if (!existsSync(staticExportDirectory)) {
  throw new Error(`Sites worker adapter: missing static export ${staticExportDirectory}`);
}
if (existsSync(vinextEntry)) {
  throw new Error(`Sites worker adapter: refusing to overwrite ${vinextEntry}`);
}
if (!existsSync(ssrEntry)) {
  throw new Error(`Sites worker adapter: missing ${ssrEntry}`);
}

cpSync(staticExportDirectory, clientDirectory, { recursive: true });

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
  entryPoints: [ssrEntry],
  outfile: bundledSsrEntry,
  bundle: true,
  conditions: ['workerd', 'worker', 'browser', 'import', 'module'],
  external: ['node:*', 'cloudflare:*'],
  format: 'esm',
  logLevel: 'warning',
  mainFields: ['module', 'main'],
  metafile: true,
  platform: 'neutral',
  plugins: [{
    name: 'preserve-worker-reentry',
    setup(esbuild) {
      esbuild.onResolve({ filter: /^\.\.\/index\.js$/ }, args => ({
        external: true,
        path: args.path,
      }));
    },
  }],
  target: 'es2022',
});
renameSync(bundledSsrEntry, ssrEntry);

const externalImports = Object.values(bundleResult.metafile.outputs)
  .flatMap(output => output.imports)
  .filter(importRecord => importRecord.external)
  .map(importRecord => importRecord.path);
const unsupportedBareImports = externalImports.filter(specifier =>
  !specifier.startsWith('node:') &&
  !specifier.startsWith('cloudflare:') &&
  !specifier.startsWith('.') &&
  !specifier.startsWith('/')
);
if (unsupportedBareImports.length > 0) {
  throw new Error(`Sites worker bundle retained bare imports: ${[...new Set(unsupportedBareImports)].join(', ')}`);
}

const bundledSsr = await import(`${pathToFileURL(ssrEntry).href}?sites-ssr-check=1`);
if (typeof bundledSsr.default?.fetch !== 'function') {
  throw new TypeError('Bundled Sites SSR module did not preserve default.fetch');
}

console.log('Sites worker adapter: default.fetch verified; lazy SSR runtime dependencies bundled');
