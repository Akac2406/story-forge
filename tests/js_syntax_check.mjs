// Every script in site/ must parse (catches a broken commit before a browser test does). Run: node tests/js_syntax_check.mjs
import fs from 'node:fs'; import path from 'node:path'; import vm from 'node:vm'; import { fileURLToPath } from 'node:url';
const site = path.join(path.dirname(fileURLToPath(import.meta.url)), '../site'); const bad = [];
for (const f of fs.readdirSync(site).filter(f => f.endsWith('.js'))) { try { new vm.Script(fs.readFileSync(path.join(site, f), 'utf8'), { filename: f }); } catch (e) { bad.push(f + ': ' + e.message); } }
const html = fs.readFileSync(path.join(site, 'index.html'), 'utf8'); [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].forEach((m, i) => { try { new vm.Script(m[1], { filename: 'index.html#' + i }); } catch (e) { bad.push('index.html inline script ' + i + ': ' + e.message); } });
if (bad.length) { console.error(bad.join('\n')); process.exit(1); } console.log('js syntax: all site scripts parse');
