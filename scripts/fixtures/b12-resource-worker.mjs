import { mkdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const marker = process.argv.indexOf('--');
const args = marker >= 0 ? process.argv.slice(marker + 1) : process.argv.slice(2);
const option = name => {
  const index = args.indexOf(name);
  return index >= 0 ? args[index + 1] : null;
};
const mode = option('--mode');
const output = resolve(option('--output') ?? '.');
const wait = milliseconds => new Promise(resolvePromise => setTimeout(resolvePromise, milliseconds));
await mkdir(output, { recursive: true });

if (mode === 'OUTPUT_FILES') {
  for (let index = 0; index < 12; index += 1) await writeFile(resolve(output, `${String(index).padStart(2, '0')}.bin`), Buffer.from([index]));
  await wait(2000);
} else if (mode === 'OUTPUT_BYTES') {
  await writeFile(resolve(output, 'oversize.bin'), Buffer.alloc(262144, 1));
  await wait(2000);
} else if (mode === 'RSS') {
  const allocation = Buffer.alloc(134217728, 1);
  process.stdout.write(`allocated ${allocation.length}\n`);
  await wait(2000);
} else if (mode === 'NONZERO_EXIT') {
  process.stderr.write('intentional fixture failure\n');
  process.exitCode = 7;
} else {
  throw new Error(`Unknown B12 fixture mode: ${mode}`);
}
