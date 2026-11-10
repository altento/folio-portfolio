import { cp, mkdir, readdir, readFile, rm, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';

const here = path.dirname(fileURLToPath(import.meta.url));
const project = path.resolve(here, '..');
const root = path.resolve(project, '..');
const source = path.join(root, 'web');
const output = path.join(project, 'www');
await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
await cp(source, output, {
  recursive: true,
  filter: (entry) => !/[\\/](tests|node_modules)([\\/]|$)/.test(entry)
    && !/package(-lock)?\.json$/.test(entry)
    && !/Запустить веб-версию\.bat$/.test(entry)
});
await build({
  entryPoints: [path.join(source, 'app.js')],
  bundle: true,
  splitting: true,
  format: 'esm',
  platform: 'browser',
  target: ['chrome107'],
  outdir: output,
  entryNames: '[name]',
  nodePaths: [path.join(project, 'node_modules')],
  chunkNames: 'chunks/[name]-[hash]',
  sourcemap: false,
  minify: true
});

// esbuild splits native-only dynamic imports into hashed chunks. The app's
// service worker must precache those chunks as well: on a fresh offline launch
// the startup bridge is requested before runtime caching has seen it.
async function listJavaScriptFiles(directory, relativeTo = directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) files.push(...await listJavaScriptFiles(absolute, relativeTo));
    else if (entry.isFile() && entry.name.endsWith('.js')) {
      files.push(`./${path.relative(relativeTo, absolute).split(path.sep).join('/')}`);
    }
  }
  return files;
}

const generatedChunks = await listJavaScriptFiles(path.join(output, 'chunks'), output);
const serviceWorkerPath = path.join(output, 'sw.js');
const serviceWorker = await readFile(serviceWorkerPath, 'utf8');
const filesDeclaration = 'const FILES=[';
if (!serviceWorker.includes(filesDeclaration)) {
  throw new Error('Could not locate service worker precache list');
}
const chunkEntries = generatedChunks.map((file) => JSON.stringify(file)).join(',');
await writeFile(
  serviceWorkerPath,
  serviceWorker.replace(filesDeclaration, `${filesDeclaration}${chunkEntries}${chunkEntries ? ',' : ''}`),
  'utf8'
);
console.log(`Prepared offline Android web assets at ${output}`);

