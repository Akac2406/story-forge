import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import vm from "node:vm";

const read = path => readFileSync(new URL(path, import.meta.url), "utf8");
const html = read("../site/index.html");
const script = html.match(/<script>\s*"use strict";[\s\S]*?<\/script>/)[0].slice(8, -9);
new vm.Script(script, {filename: "index.html"});
const section = (start, end) => {
  const from = script.indexOf(start);
  assert.notEqual(from, -1, start);
  const to = script.indexOf(end, from);
  assert.notEqual(to, -1, end);
  return script.slice(from, to);
};
const ctx = vm.createContext({console});
ctx.window = ctx;
vm.runInContext(read("../site/canon-engine.js"), ctx);
vm.runInContext(section("const CANON_MODES=", "function ideaSheet("), ctx);
vm.runInContext(section("function chapterReplayActions(", "function chapSheet("), ctx);
vm.runInContext(section("const pendingChapterRewrites=", "function idbOpen("), ctx);
vm.runInContext(section("const WORLD_SHARE_FIELDS=", "function makeWorldPackage("), ctx);
vm.runInContext(section("const STYLE_SAMPLE_LIMIT=", "function vEdit("), ctx);
const run = code => vm.runInContext(code, ctx);

assert.match(run("canonModePrompt({canonMode:'au'}, {follow:'strict'})"), /Alternate universe.*locked.*world era/);
assert.match(run("canonModePrompt({follow:'custom request'}, {})"), /Adaptive/);
assert.match(run("paceAgencyPrompt({ctl:{pace:4},agency:'player'})"), /deadline.*dialogue/s);
assert.equal(run("paceAgencyPrompt({})"), "");

run(`
  const st={id:"world",kind:"story",title:"Harbor",canonMode:"strict",worldEra:{era:"Medieval"},
    styleSamples:[{id:"voice",text:"The old tide turns again.",src:"Harbor Notes"}],
    entries:[{id:"ship",k:"Ship",t:"The ship is moored.",lock:true}]};
  const original={id:"original",storyId:"world",notes:[{id:"note",text:"Present tense",pri:"style"}],canonMode:"au",agency:"player",ctl:{pace:1},
    turns:[{role:"user",text:"Open"},{role:"ai",text:"Opening.",tid:"before"},
      {role:"user",text:"Walk",worldDays:1},{role:"ai",text:"Dock.",tid:"visible",ps:{}},
      {role:"user",text:"Wait"},{role:"ai",text:"A ship."}],
    divergences:[{turn:3,tid:"visible",entry:"Ship"},{turn:3,tid:"older-version",entry:"Ship"},{turn:1,tid:"before",entry:"Harbor"}]};
  const DB={sessions:[original],stories:[st]};
  let view={n:"chat",id:"original"}, busy=false, ADV={on:false}, saved=[], outputs=[], messages=[], replies=[];
  const hasKey=()=>true, uid=()=>"copy";
  const save=()=>saved.push(JSON.stringify(savedDB()));
  const toast=s=>messages.push(s);
  const go=v=>{view=v};
  const rerender=()=>{};
  const refs=[{for:["original"]}];
  const refsFor=id=>refs.filter(r=>r.for.includes(id));
  const chapsOf=s=>s.chaps;
  const branchAt=(s,k,o)=>{
    const n=JSON.parse(JSON.stringify(s));n.id="draft";
    n.turns=n.turns.slice(0,k+1);n.chaps=[{i:0,t:"Opening"}];
    o.prep(n);DB.sessions.push(n);go({n:"chat",id:n.id});return n;
  };
  const send=async (text,hide,show,days,opts)=>{
    const n=DB.sessions.at(-1);
    outputs.push({text,days,opts});
    if(opts.chapterStart)n.chaps.push({i:n.turns.length,t:""});
    n.turns.push({role:"user",text},{role:"ai",text:"New reply."});
    save();
    return replies.shift();
  };
  const target={i:2,t:"The docks"}, actions=chapterReplayActions(original,2,6);
  const originalBytes=JSON.stringify(original);
`);
assert.equal(run("visibleCanonWarnings(original).length"), 2);
assert.equal(run("visibleCanonWarnings(original).some(e=>e.tid==='older-version')"), false);
assert.equal(run("actions.length"), 2);
assert.equal(run("actions[0].worldDays"), 1);
run("replies=[true,false]");
await run("replayChapter(original,target,1,actions)");
assert.equal(run("DB.sessions.length"), 1);
assert.equal(run("view.id"), "original");
assert.ok(run("saved.every(s=>JSON.parse(s).sessions.length===1)"));
assert.equal(run("JSON.stringify(original)===originalBytes"), true);
assert.equal(run("refs[0].for.length"), 1);

run("replies=[true,true];saved=[];outputs=[]");
await run("replayChapter(original,target,1,actions)");
assert.equal(run("DB.sessions.length"), 2);
assert.equal(run("JSON.stringify(original)===originalBytes"), true);
assert.equal(run("DB.sessions[1].chaps[1].t"), "The docks");
assert.equal(run("outputs[0].opts.chapterStart&&!outputs[1].opts.chapterStart"), true);
assert.equal(run("saved.slice(0,-1).every(s=>JSON.parse(s).sessions.length===1)"), true);
assert.equal(run("JSON.parse(saved.at(-1)).sessions.length"), 2);
assert.equal(run("refs[0].for.includes('draft')"), true);

run(`const roundTrip=importSharedWorld({format:"story-forge-world",version:1,story:portableStory(st),playthroughs:[portablePlaythrough(original)]});`);
assert.equal(run("roundTrip.story.entries[0].lock"), true);
assert.equal(run("roundTrip.story.worldEra.era"), "Medieval");
assert.equal(run("roundTrip.story.canonMode"), "strict");
assert.equal(run("roundTrip.copies[0].notes[0].id"), "note");
assert.equal(run("roundTrip.copies[0].canonMode"), "au");
assert.equal(run("roundTrip.copies[0].agency"), "player");
assert.equal(run("roundTrip.copies[0].divergences.length"), 3);
assert.equal(run("roundTrip.story.styleSamples[0].src"), "Harbor Notes");
assert.equal(run("styleSamplesFor({styleSamples: [{text: ' '}, ...Array.from({length:4}, (_,i)=>({id:String(i), text:'x'.repeat(1600)}))]}).length"), 3);
assert.equal(run("styleSamplesFor({styleSamples: [{id: 'voice', text:'x'.repeat(1600)}]})[0].text.length"), 1500);
assert.match(read("../site/sw.js"), /"sf-v\d+"[\s\S]*"canon-engine.js"/);
console.log("PASS: v87 canon controls, visible warning versions, staged chapter replay, and world backup round trip.");
