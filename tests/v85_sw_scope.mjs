// Runs service worker in a minimal Node VM to ensure private/dynamic URLs are never intercepted.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const source = fs.readFileSync(new URL('../site/sw.js', import.meta.url), 'utf8');
const handlers = {};
const scope = 'https://example.test/story/';
let networkCalls = 0, writes = 0;
const storage = new Map();
const cache = {
  addAll: async () => {},
  put: async (req, res) => { writes++; storage.set(req.url, res); },
  match: async req => storage.get(req.url),
};
let offline = false;
const context = {
  URL, Set,
  self: {registration:{scope}, location:{origin:'https://example.test'},
    addEventListener: (type, handler) => {handlers[type] = handler},
    skipWaiting: async () => {}, clients:{claim:async()=>{}}},
  caches: {open:async()=>cache, keys:async()=>[], delete:async()=>true},
  fetch: async () => {networkCalls++; if (offline) throw new Error('offline');
    return {ok:true, redirected:false, type:'basic', clone(){return this}, body:'network'}},
};
vm.runInNewContext(source, context);
function req(path, method='GET', range=false) {
  return {url:new URL(path,scope).href,method,headers:{has:k=>range&&k==='range'}};
}
async function visit(request) {
  let promise, pending=[];
  handlers.fetch({request,respondWith:p=>{promise=p},waitUntil:p=>pending.push(p)});
  if (!promise) return 'ignored';
  const result = await promise; await Promise.all(pending);
  return result.body;
}
assert.equal(await visit(req('index.html')), 'network');
assert.equal(writes, 1);
assert.equal(await visit(req('private/story.json')), 'ignored');
assert.equal(await visit(req('api/generate')), 'ignored');
assert.equal(await visit(req('index.html?token=secret')), 'ignored');
assert.equal(await visit(req('index.html','POST')), 'ignored');
assert.equal(await visit(req('index.html','GET',true)), 'ignored');
assert.equal(await visit(req('https://other.test/index.html')), 'ignored');
assert.equal(writes, 1);
offline = true;
assert.equal(await visit(req('index.html')), 'network');
assert.equal(writes, 1);
console.log('PASS v85 service worker: static shell cached, dynamic/private requests bypassed, offline fallback works');
