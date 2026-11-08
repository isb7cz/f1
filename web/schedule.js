/* Shared by the static website and Node tests. All dates are Prague dates. */
(function (root) {
  const zone = 'Europe/Prague';
  const dateFormat = new Intl.DateTimeFormat('sv-SE', {timeZone:zone, year:'numeric', month:'2-digit', day:'2-digit'});
  const timeFormat = new Intl.DateTimeFormat('cs-CZ', {timeZone:zone, hour:'2-digit', minute:'2-digit', hourCycle:'h23'});
  const weekdayFormat = new Intl.DateTimeFormat('cs-CZ', {timeZone:zone, weekday:'long'});
  const labelFormat = new Intl.DateTimeFormat('cs-CZ', {timeZone:zone, day:'numeric', month:'long', year:'numeric'});
  const unavailable = () => ({state:'unavailable', message:'Program nejbližšího víkendu F1 zatím není k dispozici. Jakmile ho Nova zveřejní, objeví se zde automaticky.'});
  function dateKey(value) {return dateFormat.format(new Date(value));}
  function select(snapshot, now = new Date()) {
    if (!snapshot || !Array.isArray(snapshot.programmes) || !Number.isFinite(Date.parse(snapshot.updated_at))) throw new Error('Invalid schedule');
    const rows = snapshot.programmes;
    for (const row of rows) {
      if (!Number.isFinite(Date.parse(row.start)) || !Number.isFinite(Date.parse(row.end)) || Date.parse(row.end) <= Date.parse(row.start) || typeof row.title !== 'string') throw new Error('Invalid programme');
    }
    const groups = new Map();
    for (const row of rows) {
      if (row.kind === 'intro') continue;
      if (!groups.has(row.grand_prix)) groups.set(row.grand_prix, []);
      groups.get(row.grand_prix).push(row);
    }
    const candidates = [];
    for (const [name, items] of groups) {
      const races = items.filter(p => p.kind === 'race');
      const end = Math.max(...(races.length ? races : items).map(p => Date.parse(p.end)));
      if (end > now.getTime()) candidates.push({name, items, races, first:Math.min(...items.map(p => Date.parse(p.start)))});
    }
    candidates.sort((a,b) => a.first-b.first);
    let result = unavailable();
    if (candidates.length) {
      const chosen = candidates[0];
      const items = [...chosen.items];
      for (const p of rows) {
        if (p.kind === 'intro' && chosen.races.some(r => Date.parse(r.start) >= Date.parse(p.end) && Date.parse(r.start)-Date.parse(p.end) <= 900000 && Date.parse(p.start)<Date.parse(r.start))) items.push(p);
      }
      items.sort((a,b) => Date.parse(a.start)-Date.parse(b.start));
      const days = new Map();
      const labels = {race:'Závod', intro:'Úvodní studio', sprint:'Sprint', sprint_qualifying:'Sprintová kvalifikace', qualifying:'Kvalifikace'};
      for (const p of items) {
        const key = dateKey(p.start);
        if (!days.has(key)) {
          const weekday = weekdayFormat.format(new Date(p.start));
          days.set(key, {date:key, weekday:weekday[0].toUpperCase()+weekday.slice(1), label:labelFormat.format(new Date(p.start)), items:[]});
        }
        const number = p.title.match(/(\d+)\.?\s*(?:volný\s+)?trénink/i);
        const label = labels[p.kind] || (number ? `${number[1]}. trénink` : 'Trénink');
        days.get(key).items.push({label, time:timeFormat.format(new Date(p.start)), start:p.start, end:p.end});
      }
      result = {state:'ready', title:chosen.name, days:[...days.values()], partial:!chosen.races.length};
    }
    return {...result, updated_at:snapshot.updated_at, source:snapshot.source === 'https://tv.seznam.cz/' ? snapshot.source : 'https://tv.nova.cz/program', stale:!!snapshot.fetch_failed_at || now.getTime()-Date.parse(snapshot.updated_at)>12*60*60*1000};
  }
  const api = {select, dateKey};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.F1Schedule = api;
})(typeof globalThis === 'undefined' ? this : globalThis);
