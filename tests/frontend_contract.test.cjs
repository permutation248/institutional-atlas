/* Pure Node VM contract tests. This does not launch or automate a browser. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'web/app.js'), 'utf8');
const template = fs.readFileSync(path.join(root, 'web/template.html'), 'utf8');
const clone = value => JSON.parse(JSON.stringify(value));

function entity(id, domain, name, location = null) {
  return {id, domain, name, name_zh:name, aliases:[], function:'Documented public function',
    parents:[], leader:null, employee_count:null, financial_profile:[], publications:[],
    verified_at:'2026-10-24', official_url:'https://example.gov/', website_type:'official',
    sources:[{url:'https://example.gov/about',description:'Official source'}], location};
}
function fixture() {
  const dc = {lat:38.9,lon:-77.04,state:'DC',city:'Washington',precision:'city',evidence_url:'https://example.gov/location'};
  const ca = {lat:37.4,lon:-122.1,state:'CA',city:'Example city',precision:'city',evidence_url:'https://example.edu/location'};
  const entities = [entity('us-federal-government','government','Federal system',dc),entity('us-treasury','government','Treasury',dc),
    entity('nist','government','NIST',dc),entity('nist-labs','government','NIST Labs',dc),
    entity('uc-system','university','Research University',ca),entity('company','enterprise','Research Company',ca),
    entity('us-fed','finance','Central bank',dc)];
  const makeEvent = (id,date,ids) => ({id,title:'Official release',summary:'Source-based announcement',date,entity_ids:ids,
    category:'research',source_url:'https://example.gov/news',source_name:'Official newsroom',reviewed_at:'2026-10-24'});
  const makeFlow = (id,source_id,target_id,kind,label) => ({id,source_id,target_id,kind,label,description:'Evidenced mechanism',
    evidence_url:'https://example.gov/mechanism',as_of:'2026-10-24',basis:'mechanism',amount:null});
  return {metadata:{snapshot_date:'2026-10-24'},entities,edges:[{child_id:'nist',parent_id:'us-federal-government',type:'PART_OF',evidence_url:'https://example.gov/structure'}],
    sectors:[{id:'households',name_zh:'Households',description:'Conceptual sector'},{id:'banks',name_zh:'Banks',description:'Conceptual sector'},
      {id:'investors',name_zh:'Investors',description:'Conceptual sector'},{id:'capital-markets',name_zh:'Markets',description:'Conceptual sector'}],
    events:[makeEvent('current-event','2026-10-24',['nist']),makeEvent('threshold-event','2026-09-24',['uc-system']),
      makeEvent('old-event','2026-09-23',['company']),makeEvent('shared-event','2026-10-01',['company','uc-system'])],
    flows:[makeFlow('deposits','households','banks','deposit','Deposits'),makeFlow('credit','banks','company','loan','Credit'),
      makeFlow('grant','us-treasury','uc-system','grant','Research funding'),makeFlow('shares','investors','capital-markets','equity','Equity')],
    geography:{states:[{id:'06',name:'California',region:'mainland',path:'M0,0L1,0L1,1Z'}]}};
}

class ElementStub {
  constructor(id) { this.id=id; this.innerHTML=''; this.textContent=''; this.hidden=false; this.checked=false; this.value=''; this.dataset={}; this.style={}; this.listeners={}; this.attributes={}; this.tagName='DIV'; this.classList={toggle(){},add(){},remove(){}}; }
  addEventListener(name, callback) { (this.listeners[name]??=[]).push(callback); }
  setAttribute(name,value) { this.attributes[name]=value; }
  getAttribute(name) { return this.attributes[name]; }
  hasAttribute(name) { return name in this.attributes; }
  emit(name,event={}) { for(const callback of this.listeners[name]||[]) callback({target:this,currentTarget:this,preventDefault(){},...event}); }
  focus() {} scrollIntoView() {} showModal() { this.open=true; } close() { this.open=false; }
  click() { this.emit('click'); }
}
function boot(data=fixture(),hash='') {
  const elements = new Map([...template.matchAll(/\bid="([^"]+)"/g)].map(match=>[match[1],new ElementStub(match[1])]));
  elements.get('event-period').value='90';
  elements.get('show-relations').checked=true; elements.get('show-events').checked=true;
  const directory = new ElementStub('directory');
  const viewButtons = ['map','structure','finance'].map(view=>{const el=new ElementStub(view);el.dataset.view=view;return el;});
  const documentEvents = {};
  const location = {hash};
  const context = vm.createContext({ATLAS_DATA:clone(data),console,URL,URLSearchParams,Intl,Date,Blob,
    location,history:{pushState(_state,_title,next){location.hash=next;}},setTimeout(){},
    document:{activeElement:{tagName:'BODY'},
      getElementById(id){assert.ok(elements.has(id),`app requested missing template ID: ${id}`);return elements.get(id);},
      querySelector(selector){assert.equal(selector,'.directory');return directory;},
      querySelectorAll(selector){assert.equal(selector,'[data-view]');return viewButtons;},
      addEventListener(name,callback){(documentEvents[name]??=[]).push(callback);},createElement(tag){const el=new ElementStub(tag);el.tagName=tag.toUpperCase();return el;}},
    window:{addEventListener(){}}});
  vm.runInContext(source,context,{filename:'web/app.js',timeout:2000});
  return {elements,context,run(code){return vm.runInContext(code,context,{timeout:2000});},value(code){return clone(vm.runInContext(code,context,{timeout:2000}));}};
}

test('app initializes against real template IDs and renders independently usable views',()=>{
  const app=boot();
  assert.match(app.elements.get('entity-list').innerHTML,/NIST/);
  for(const view of ['map','structure','finance']) {
    app.run(`setView('${view}')`);
    assert.equal(app.elements.get(view+'-view').hidden,false);
    for(const other of ['map','structure','finance'].filter(x=>x!==view)) assert.equal(app.elements.get(other+'-view').hidden,true);
  }
  assert.match(app.elements.get('finance-view').innerHTML,/机制示意/);
});

test('search prioritizes exact IDs and domain filters consistently constrain list and map',()=>{
  const app=boot();
  app.elements.get('search').emit('input',{target:{value:'  NIST  '}});
  assert.deepEqual(app.value('visibleNodes().map(n=>n.id)'),['nist','nist-labs']);
  app.run("setDomain('university'); state.query='research'; renderDirectory(); renderMap();");
  assert.deepEqual(app.value('visibleNodes().map(n=>n.id)'),['uc-system']);
  assert.deepEqual(app.value('state.groups.flatMap(g=>g.nodes.map(n=>n.id))'),['uc-system']);
  assert.doesNotMatch(app.elements.get('entity-list').innerHTML,/Research Company/);
});

test('event windows include cutoff date and respect selected organization and domain together',()=>{
  const app=boot();app.elements.get('event-period').value='30';
  assert.deepEqual(app.value('eventFiltered().map(e=>e.id)'),['current-event','shared-event','threshold-event']);
  app.run("state.domain='university'; state.selected='uc-system'");
  app.elements.get('events-selected').checked=true;
  assert.deepEqual(app.value('eventFiltered().map(e=>e.id)'),['shared-event','threshold-event']);
  app.elements.get('event-period').value='all';app.elements.get('events-selected').checked=false;app.run("state.domain='all'");
  assert.equal(app.value('eventFiltered().length'),4);
});

test('snapshot display follows mechanism-only updates rather than stale entity review dates',()=>{
  const data=fixture();data.metadata.snapshot_date='2026-10-25';data.flows[0].as_of='2026-10-25';
  const app=boot(data);
  assert.match(app.elements.get('snapshot-date').textContent,/2026-10-25/);
  assert.equal(app.value('latestReview'),'2026-10-25');
});

test('hash restoration validates view and domain, including prototype property attacks',()=>{
  const valid=boot(fixture(),'#uc-system?view=structure&domain=university');
  assert.equal(valid.value('state.selected'),'uc-system');assert.equal(valid.value('state.view'),'structure');
  assert.equal(valid.value('state.domain'),'university');
  for(const invalid of ['constructor','__proto__','toString','unknown']) {
    const app=boot(fixture(),`#nist?view=script&domain=${invalid}`);
    assert.equal(app.value('state.domain'),'all',`invalid domain ${invalid}`);
    assert.equal(app.value('state.view'),'map');
  }
});

test('map organization coordinates agree with documented mainland and inset transformations',()=>{
  const app=boot();
  assert.deepEqual(app.value('project({lon:-125,lat:50,state:"WA"})'),{x:0,y:0});
  assert.deepEqual(app.value('project({lon:-66,lat:24,state:"FL"})'),{x:1000,y:600});
  assert.deepEqual(app.value('project({lon:175,lat:60,state:"AK"})'),app.value('project({lon:-185,lat:60,state:"AK"})'));
  const hawaii=app.value('project({lon:-157.86,lat:21.31,state:"HI"})');
  assert.ok(Math.abs(hawaii.x-(285+(3.14/7)*130))<1e-8);
  assert.ok(Math.abs(hawaii.y-(490+(1.69/5)*85))<1e-8);
});

test('financial modes show real endpoints and preserve conceptual sectors outside organization tree',()=>{
  const app=boot();
  assert.deepEqual(app.value('routeFlows().map(f=>f.id)'),['deposits','credit']);
  app.run("chooseFlow('shares')");
  assert.equal(app.value('state.flowMode'),'all');assert.equal(app.value('state.flowId'),'shares');
  const html=app.elements.get('finance-view').innerHTML;
  assert.match(html,/data-endpoint="investors"/);assert.match(html,/data-endpoint="capital-markets"/);
  assert.match(html,/概念部门 · 非单一机构/);assert.match(html,/金额未量化/);
  assert.equal(app.value('byId.has("investors")'),false);
  assert.equal(app.value('edges.length'),1);
});

test('organization, governance, event and mechanism text stays escaped in generated markup',()=>{
  const data=fixture(),attack='<img src=x onerror="alert(1)">';
  data.entities[0].name_zh=attack;data.entities[0].mission=attack;
  data.entities[0].governance={apex:attack,mechanism:attack,evidence_url:'https://example.gov/charter'};
  data.events[0].title=attack;data.events[0].summary=attack;data.flows[0].description=attack;
  const app=boot(data);
  for(const id of ['inspector-content','entity-list','events-list','map-pins']) {
    assert.doesNotMatch(app.elements.get(id).innerHTML,/<img\b/);
    assert.match(app.elements.get(id).innerHTML,/&lt;img/);
  }
  app.run("setView('finance')");
  assert.doesNotMatch(app.elements.get('finance-view').innerHTML,/<img\b/);
  assert.match(app.elements.get('finance-view').innerHTML,/&lt;img/);
  assert.match(app.elements.get('inspector-content').innerHTML,/rel="noopener noreferrer"/);
});

test('selection clears incompatible filtering and zoom preserves the coordinate beneath its anchor',()=>{
  const app=boot();app.run("state.domain='university'; state.query='university'; selectEntity('nist')");
  assert.equal(app.value('state.domain'),'all');assert.equal(app.value('state.query'),'');
  const before=app.value('state.camera');const anchor={x:420,y:230};
  app.run('zoom(1.4,{x:420,y:230})');const after=app.value('state.camera');
  assert.ok(Math.abs((anchor.x-before.x)/before.k-(anchor.x-after.x)/after.k)<1e-8);
  assert.ok(Math.abs((anchor.y-before.y)/before.k-(anchor.y-after.y)/after.k)<1e-8);
});
