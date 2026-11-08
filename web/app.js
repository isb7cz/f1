const content = document.querySelector('#content');
const pragueDate = date => new Intl.DateTimeFormat('sv-SE', {timeZone: 'Europe/Prague'}).format(date);
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text) node.textContent = text;
  return node;
}
function render(data) {
  const sourceLink = document.querySelector('footer a');
  const backup = data.source === 'https://tv.seznam.cz/';
  sourceLink.href = backup ? data.source : 'https://tv.nova.cz/program';
  sourceLink.textContent = backup ? 'Zdroj: Seznam TV ↗' : 'Zdroj: TV Nova ↗';
  const fragment = document.createDocumentFragment();
  const intro = el('section', 'intro');
  intro.append(el('p', 'eyebrow', 'FORMULE 1 · ŽIVÉ PŘENOSY'));
  if (data.state === 'ready') {
    intro.append(el('h1', '', data.title));
    fragment.append(intro);
    if (data.stale) fragment.append(el('p', 'notice', 'Aktualizace se opozdila. Zobrazujeme poslední dostupný program; časy se mohly změnit.'));
    if (data.partial) fragment.append(el('p', 'notice', 'Program víkendu se ještě doplňuje. Zobrazujeme pouze potvrzené přenosy.'));
    const schedule = el('div', 'schedule');
    for (const day of data.days) {
      const section = el('section', 'day' + (day.date === pragueDate(new Date()) ? ' today' : ''));
      const heading = el('header', 'day-heading');
      const h2 = el('h2', '', day.weekday);
      h2.id = 'day-' + day.date;
      section.setAttribute('aria-labelledby', h2.id);
      const date = el('time', 'date', day.label);
      date.dateTime = day.date;
      heading.append(h2, date);
      const list = el('ul', 'broadcasts');
      for (const item of day.items) {
        const row = el('li', 'broadcast' + (item.label === 'Závod' ? ' race' : ''));
        const time = el('time', '', item.time);
        time.dateTime = item.start;
        row.append(time, el('span', 'broadcast-label', item.label));
        list.append(row);
      }
      section.append(heading, list);
      schedule.append(section);
    }
    fragment.append(schedule);
  } else {
    intro.classList.add('empty');
    const title = data.state === 'loading' ? 'Víkend už je na cestě.' : data.state === 'error' ? 'Program se teď nenačetl.' : 'Na další víkend si počkáme.';
    intro.append(el('h1', '', title));
    intro.append(el('p', 'message', data.message));
    fragment.append(intro);
    if (data.stale) fragment.append(el('p', 'notice', 'Zdroj se nepodařilo aktualizovat. Další přenosy proto zatím nemůžeme potvrdit.'));
  }
  if (data.updated_at) {
    const formatted = new Intl.DateTimeFormat('cs-CZ', {timeZone:'Europe/Prague', day:'numeric', month:'numeric', hour:'2-digit', minute:'2-digit'}).format(new Date(data.updated_at));
    fragment.append(el('p', 'update', 'Program ověřen ' + formatted + ' · Nova Sport 5'));
  }
  content.replaceChildren(fragment);
  content.setAttribute('aria-busy', data.state === 'loading' ? 'true' : 'false');
}
let timer;
let lastSnapshot;
async function load() {
  clearTimeout(timer);
  let delay = 60000;
  try {
    const response = await fetch('./schedule.json', {cache:'no-store', signal:AbortSignal.timeout(12000)});
    if (!response.ok) throw new Error('Network error');
    const snapshot = await response.json();
    const data = F1Schedule.select(snapshot);
    lastSnapshot = snapshot;
    render(data);
    if (data.state === 'loading') delay = 2000;
  } catch (_) {
    render(lastSnapshot ? {...F1Schedule.select(lastSnapshot), stale:true} : {state:'error', message:'Program se nepodařilo načíst. Připojení ověříme znovu automaticky.'});
  } finally {
    timer = setTimeout(load, delay);
  }
}
document.addEventListener('visibilitychange', () => {if (!document.hidden) load();});
load();
