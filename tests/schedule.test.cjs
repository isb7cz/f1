const {test} = require('node:test');
const assert = require('node:assert/strict');
const {select, dateKey} = require('../web/schedule.js');
const p = (name, kind, start, end, title=name) => ({grand_prix:name, kind, start, end, title});
const snapshot = rows => ({updated_at:'2026-11-08T10:00:00Z', programmes:rows, fetch_failed_at:null});
const raceA = p('Velká cena A', 'race', '2026-11-08T17:50:00+01:00', '2026-11-08T19:50:00+01:00');
const raceB = p('Velká cena B', 'race', '2026-11-22T04:50:00+01:00', '2026-11-22T06:50:00+01:00');
test('ongoing weekend switches immediately after race end, without a new build', () => {
  const data = snapshot([raceA,raceB]);
  assert.equal(select(data,new Date('2026-11-08T18:00:00+01:00')).title,'Velká cena A');
  assert.equal(select(data,new Date(raceA.end)).title,'Velká cena B');
  assert.equal(select(data,new Date(raceB.end)).state,'unavailable');
});
test('overnight and DST use Prague regardless of device timezone', () => {
  assert.equal(dateKey('2026-07-01T22:30:00Z'),'2026-07-02');
  assert.equal(dateKey('2026-11-01T22:30:00Z'),'2026-11-01');
  const data = snapshot([raceB]);
  const result = select(data,new Date('2026-11-10T00:00:00Z'));
  assert.equal(result.days[0].date,'2026-11-22');
  assert.equal(result.days[0].items[0].time,'04:50');
});
test('sprint, partial programme, and studio association', () => {
  const sprint = p('Velká cena A', 'sprint', '2026-11-07T11:00:00Z','2026-11-07T12:00:00Z');
  const qualifying = {...sprint,kind:'sprint_qualifying',start:'2026-11-06T11:00:00Z',end:'2026-11-06T12:00:00Z'};
  const studio = p(null,'intro','2026-11-08T17:00:00+01:00',raceA.start,'Úvodní studio');
  const data=snapshot([sprint,qualifying,studio,raceA,raceB]);
  const result=select(data,new Date('2026-11-05T00:00:00Z'));
  assert.equal(result.days[0].items[0].label,'Sprintová kvalifikace');
  assert.equal(result.days[1].items[0].label,'Sprint');
  assert.equal(result.days[2].items[0].label,'Úvodní studio');
  assert.equal(select(snapshot([sprint]),new Date('2026-11-05T00:00:00Z')).partial,true);
});
test('empty, stale, failed, and malformed data are handled honestly', () => {
  assert.equal(select(snapshot([]),new Date('2026-11-08T10:00:00Z')).state,'unavailable');
  assert.equal(select(snapshot([raceA]),new Date('2026-11-08T23:00:01Z')).stale,true);
  assert.equal(select({...snapshot([raceA]),fetch_failed_at:'2026-11-08T10:01:00Z'},new Date('2026-11-08T10:02:00Z')).stale,true);
  assert.throws(()=>select({programmes:[],updated_at:null}));
});
