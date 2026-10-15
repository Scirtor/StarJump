const {test} = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

function worker() {
  const handlers = {}, stores = new Map(), messages = [];
  let online = true, requests = 0;
  const scope = 'https://game.test/games/starjump/';
  const key = request => new URL(typeof request === 'string' ? request : request.url, scope).href;
  const caches = {
    async open(name) {
      if (!stores.has(name)) stores.set(name, new Map());
      const data = stores.get(name);
      return {
        async addAll(files) { for (const file of files) data.set(key(file), new Response(file)); },
        async match(request) { return data.get(key(request))?.clone(); },
        async put(request, response) { data.set(key(request), response.clone()); }
      };
    },
    async keys() { return [...stores.keys()]; },
    async delete(name) { return stores.delete(name); }
  };
  const self = {location:{origin:'https://game.test',hostname:'game.test'},registration:{scope},clients:{claim:async()=>{}},skipWaiting:async()=>{},addEventListener:(name,callback)=>handlers[name]=callback};
  vm.runInNewContext(fs.readFileSync('web/sw.js','utf8'), {self,caches,URL,Request,Response,console,Set,Promise,fetch:async request=>{
    requests++; if (!online) throw new Error('offline'); return new Response('network: '+key(request));
  }});
  async function event(name, extra={}) {
    const pending=[];let response;
    handlers[name]({...extra,waitUntil:p=>pending.push(p),respondWith:p=>response=p,source:{postMessage:m=>messages.push(m)}});
    const result = response ? await response : undefined;
    await Promise.all(pending); return result;
  }
  return {event,stores,messages,offline:()=>online=false,requests:()=>requests};
}

test('installs shell, preserves unrelated caches, serves cached game and runtime offline',async()=>{
  const w=worker();w.stores.set('unrelated',new Map());w.stores.set('starjump-shell-old',new Map());
  await w.event('install');await w.event('activate');
  assert(w.stores.has('unrelated'));assert(!w.stores.has('starjump-shell-old'));
  const runtime = {url:'https://pygame-web.github.io/cdn/0.9.3/cpython312/main.wasm',method:'GET',mode:'cors'};
  await w.event('fetch',{request:runtime});
  const count=w.requests();w.offline();
  assert.match(await (await w.event('fetch',{request:runtime})).text(),/^network:/);
  assert.equal(w.requests(),count);
  assert.equal(await (await w.event('fetch',{request:{url:'https://game.test/games/starjump/',method:'GET',mode:'navigate'}})).text(),'./');
  assert.equal(await (await w.event('fetch',{request:{url:'https://game.test/games/starjump/stage.tar.gz',method:'GET',mode:'cors'}})).text(),'./stage.tar.gz');
  await w.event('message',{data:{type:'READY'}});
  assert.equal(w.messages[0].type,'OFFLINE_READY');
});
