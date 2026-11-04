// Generates tests/golden.json by running the reference WebUpdate.js.
// Usage: node tests/make_golden.mjs [path/to/WebUpdate.js] [path/to/FM-1_015.fwsc]
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';

const src = process.argv[2] || 'ref/fm1_open/sdk/WebUpdate.js';
const stock = process.argv[3] || 'ref/fm1_open/sdk/firmware/FM-1_015.fwsc';
const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(src, 'utf8'), ctx);
const W = ctx.FM1Web;
const hex = b => Buffer.from(b).toString('hex');
// Deterministic pseudo-random bytes.
let seed = 12345;
const rnd = n => Uint8Array.from({length: n}, () => (seed = (seed * 1103515245 + 12345) & 0x7fffffff) >> 16 & 255);

const out = {crc16: [], frame: [], parse_reject: []};
for (const n of [0, 1, 2, 7, 64, 513]) { const d = rnd(n); out.crc16.push([hex(d), W.crc16(d)]); }
for (const [cmd, n] of [[17, 0], [49, 0], [50, 38], [48, 8], [48, 520], [33, 5], [34, 520]]) {
  const p = rnd(n), f = W.frame(cmd, Array.from(p));
  const back = W.parse(f);
  out.frame.push({cmd, payload: hex(p), sysex: hex(f), parsed: back && {cmd: back.command, data: hex(back.data)}});
}
const good = W.frame(17, Array.from(rnd(27)));
const bad1 = Uint8Array.from(good); bad1[5] ^= 1;
out.parse_reject.push(hex(bad1));
out.parse_reject.push(hex(Uint8Array.from([...good.slice(0, -2), 247])));
const U8 = vm.runInContext('Uint8Array', ctx);  // instanceof is per-realm
const bytes = U8.from(fs.readFileSync(stock));
const pkg = W.inspectPackage(bytes, true);
out.stock = {
  product: pkg.product,
  image_len: pkg.image.length,
  image_sha256: crypto.createHash('sha256').update(pkg.image).digest('hex'),
  loader_sha256: crypto.createHash('sha256').update(pkg.loader).digest('hex'),
  factory_sha256: crypto.createHash('sha256').update(pkg.factory).digest('hex'),
};
fs.writeFileSync('tests/golden.json', JSON.stringify(out, null, 1) + '\n');
console.log('wrote tests/golden.json', out.stock);
