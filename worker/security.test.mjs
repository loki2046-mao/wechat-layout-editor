import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
const source = await readFile(new URL('./index.js', import.meta.url), 'utf8');
const { default: worker } = await import('data:text/javascript;base64,' + Buffer.from(source).toString('base64'));
let calls = 0;
globalThis.fetch = async () => { calls++; throw new Error('Unexpected upstream request'); };
for (const path of ['/api/doc?url=https://example.com/docx/synthetic', '/api/image?token=synthetic']) {
  assert.equal((await worker.fetch(new Request('https://proxy.example' + path), {})).status, 401);
  assert.equal((await worker.fetch(new Request('https://proxy.example' + path, { headers: { Authorization: 'Bearer wrong' } }), { PROXY_KEY: 'test' })).status, 401);
}
assert.equal((await worker.fetch(new Request('https://proxy.example/'), {})).status, 200);
assert.equal((await worker.fetch(new Request('https://proxy.example/api/doc', { headers: { Authorization: 'Bearer test' } }), { PROXY_KEY: 'test' })).status, 400);
assert.equal(calls, 0);
console.log('Security regression checks passed');
