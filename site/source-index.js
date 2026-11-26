/* Local source analysis. All inputs are user-supplied data. */
(function (root) {
"use strict";
const normalize = text => String(text || "").normalize("NFKC").toLowerCase();
const words = text => normalize(text).match(/[\p{L}\p{N}]+/gu) || [];
const stop = new Set("a an and are as at be been but by can could for from had has have he her him his i if in into is it its may me my of on or our said she so than that the their them then there these they this those to too up was we were what when where which who will with would you your".split(" "));
const terms = text => [...new Set(words(text).filter(word => word.length >= 3 && !stop.has(word)))];
const clean = (value, max) => typeof value === "string" ? value.trim().slice(0, max) : "";

function candidates(chapters) {
  const mentions = new Map();
  const pattern = /\b(?:[A-Z][a-z’'-]{1,})(?:[ \t]+[A-Z][a-z’'-]{1,}){0,2}/g;
  for (const chapter of chapters) {
    for (const match of chapter.text.matchAll(pattern)) {
      const name = match[0].split(/\s+/).filter(word => !stop.has(normalize(word)) &&
        !/^(Chapter|Part|Lord|Lady|Sir|Master|However|Meanwhile|Suddenly|Today|Tomorrow|Yesterday|Finally|Perhaps|Afterward)$/i.test(word)).join(" ").replace(/[’']s$/, "");
      if (!name || name.length > 75) continue;
      const row = mentions.get(name) || {name, count:0, chapters:new Set(), firstCh:chapter.n, lastCh:chapter.n, aliases:[], internal:0};
      row.count++;
      row.chapters.add(chapter.n);
      row.firstCh = Math.min(row.firstCh, chapter.n);
      row.lastCh = Math.max(row.lastCh, chapter.n);
      if (!/(?:^|[.!?]\s*)$/.test(chapter.text.slice(Math.max(0, match.index - 8), match.index))) row.internal++;
      mentions.set(name, row);
    }
  }
  const fullNames = new Map();
  for (const row of mentions.values()) {
    if (!row.name.includes(" ") || row.count < 2) continue;
    for (const part of new Set(row.name.split(" "))) {
      const list = fullNames.get(part) || [];
      list.push(row);
      fullNames.set(part, list);
    }
  }
  for (const [name, row] of mentions) {
    const choices = fullNames.get(name);
    if (choices?.length !== 1) continue;
    const primary = choices[0];
    primary.aliases.push(name);
    primary.count += row.count;
    row.chapters.forEach(n => primary.chapters.add(n));
    primary.firstCh = Math.min(primary.firstCh,row.firstCh);
    primary.lastCh = Math.max(primary.lastCh,row.lastCh);
    primary.internal += row.internal;
    mentions.delete(name);
  }
  return [...mentions.values()].filter(row => row.count >= 2)
    .sort((a,b) => (b.count + b.chapters.size * 2) - (a.count + a.chapters.size * 2) || a.name.localeCompare(b.name))
    .slice(0,400).map(row => ({
      name:row.name, count:row.count, aliases:row.aliases, firstCh:row.firstCh,
      kind:!row.internal || /\b(house|clan|city|mount|kingdom|empire|academy|guild|forest|river|valley|sword|order)\b/i.test(row.name) ? "candidate" : "character",
      stats:{mentions:row.count, first:row.firstCh, last:row.lastCh, chapters:row.chapters.size}
    }));
}

function search(chapters, query, options = {}) {
  const limit = Math.max(1,Math.min(40,Number(options.limit) || 8));
  const perChapter = Math.max(1,Math.min(4,Number(options.perChapter) || 2));
  const max = options.maxChapter == null || options.maxChapter === "" ? Infinity : Number(options.maxChapter);
  const queryWords = terms(query).slice(0,45);
  if (!queryWords.length || Number.isNaN(max)) return [];
  const phrase = normalize(query).trim();
  const eligible = chapters.filter(ch => ch.n <= max);
  const freq = new Map(queryWords.map(word => [word,0]));
  for (const ch of eligible) {
    const tokens = new Set(words(ch.text));
    for (const word of queryWords) if (tokens.has(word)) freq.set(word,freq.get(word)+1);
  }
  const result = [];
  for (const ch of eligible) {
    const best = [];
    for (let start=0; start<ch.text.length; start+=300) {
      const excerpt = ch.text.slice(start,start+390).trim();
      const tokens = new Set(words(excerpt));
      const rank = queryWords.reduce((sum,word) => sum+(tokens.has(word)?1+Math.log((1+eligible.length)/(1+freq.get(word))):0),0);
      if (!rank) continue;
      const score = rank + (phrase.length >= 5 && normalize(excerpt).includes(phrase)?5:0);
      best.push({chapter:ch.n,title:ch.title,sourceId:ch.sourceId,sourceTitle:ch.sourceTitle,excerpt,score,offset:start});
    }
    result.push(...best.sort((a,b)=>b.score-a.score||a.offset-b.offset).slice(0,perChapter));
  }
  const seen = new Map();
  return result.sort((a,b)=>b.score-a.score||a.chapter-b.chapter||a.offset-b.offset)
    .filter(row => {const n=seen.get(row.chapter)||0;seen.set(row.chapter,n+1);return n<perChapter}).slice(0,limit);
}

function batches(chapters, from, to, ceiling = 22000) {
  const out = [];
  let batch = [], size = 0;
  for (const chapter of chapters) {
    if (chapter.n < from || chapter.n > to) continue;
    const segments = [];
    for (let start=0; start<chapter.text.length; start+=ceiling-400)
      segments.push({n:chapter.n,title:chapter.title,offset:start,text:chapter.text.slice(start,start+ceiling-400)});
    for (const segment of segments) {
      const weight = JSON.stringify(segment).length;
      if (batch.length && size+weight > ceiling) {out.push(batch);batch=[];size=0}
      batch.push(segment);size+=weight;
    }
  }
  if (batch.length) out.push(batch);
  return out;
}

function evidenceMatch(text,evidence) {
  const exact=text.indexOf(evidence);
  if(exact>=0)return {offset:exact,length:evidence.length};
  // EPUB formatting can split a quotation across lines or use typographic punctuation.
  const pattern=evidence.split(/(\s+)/u).map(part=>/^\s+$/u.test(part)?"\\s+":Array.from(part,char=>{
      if(/['‘’]/u.test(char))return "['‘’]";
      if(/["“”]/u.test(char))return '["“”]';
      return char.replace(/[.*+?^${}()|[\]\\]/g,"\\$&");
    }).join("")).join("");
  const match=new RegExp(pattern,"u").exec(text);
  return match?{offset:match.index,length:match[0].length}:null;
}
function reviewExtraction(raw,batch) {
  if (!raw || !Array.isArray(raw.entries)) throw Error("Expected an entries array.");
  if (raw.entries.length > 120) throw Error("Too many extracted entries.");
  const entries=[], rejected=[];
  const kinds=new Set(["summary","event","character","relationship","power","term","location","faction","style"]);
  for(const item of raw.entries){
    const chapter=Number(item?.chapter), kind=clean(item?.kind,30);
    const title=clean(item?.title,120), text=clean(item?.text,800), evidence=typeof item?.evidence==="string"?item.evidence.trim():"";
    const parts=batch.filter(part=>part.n===chapter);
    let why;
    if(!parts.length)why="chapter outside the requested text";
    else if(!title||!text||!kinds.has(kind))why="missing or invalid fields";
    else if(evidence.length<8||evidence.length>180)why="missing or invalid evidence quote";
    else {
      const match=parts.map(part=>({part,span:evidenceMatch(part.text,evidence)})).find(result=>result.span);
      if(!match)why="evidence quote absent from its chapter";
      else if(text.length>=60&&normalize(match.part.text).includes(normalize(text)))why="entry text copied from the source";
      else {
        entries.push({chapter,kind,title,text,private:item.private!==false,length:match.span.length,offset:match.part.offset+match.span.offset,
          aliases:Array.isArray(item.aliases)?[...new Set(item.aliases.map(value=>clean(value,80)).filter(Boolean))].slice(0,8):[]});
        continue;
      }
    }
    rejected.push({chapter:parts.length?chapter:null,why});
  }
  return {entries,rejected};
}

root.SFSource = Object.freeze({candidates,search,batches,reviewExtraction,terms,normalize});
})(globalThis);
