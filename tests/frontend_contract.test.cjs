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
  const viewButtons = ['universe','map','structure','finance'].map(view=>{const el=new ElementStub(view);el.dataset.view=view;return el;});
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
  return {elements,context,
    clickDataset(dataset){const target={dataset,closest(selector){return selector==='[data-universe-chart]'?null:this;},hasAttribute(){return false;}};for(const callback of documentEvents.click||[])callback({target});},
    clickUniverse(clientX,clientY,rect){const chart={getBoundingClientRect(){return rect;}};const target={closest(selector){return selector==='[data-universe-chart]'?chart:null;}};for(const callback of documentEvents.click||[])callback({target,clientX,clientY});},
    run(code){return vm.runInContext(code,context,{timeout:2000});},value(code){return clone(vm.runInContext(code,context,{timeout:2000}));}};
}

test('app initializes against real template IDs and renders independently usable views',()=>{
  const app=boot();
  assert.match(app.elements.get('entity-list').innerHTML,/NIST/);
  for(const view of ['universe','map','structure','finance']) {
    app.run(`setView('${view}')`);
    assert.equal(app.elements.get(view+'-view').hidden,false);
    for(const other of ['universe','map','structure','finance'].filter(x=>x!==view)) assert.equal(app.elements.get(other+'-view').hidden,true);
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
    assert.equal(app.value('state.view'),'universe');
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

test('large financial diagrams retain intrinsic row height and every endpoint in a scrollable region',()=>{
  const data=fixture();
  for(let i=0;i<24;i++){
    const id='finance-endpoint-'+i;data.entities.push(entity(id,'finance','Financial endpoint '+i));
    data.flows.push({id:'extra-flow-'+i,source_id:'banks',target_id:id,kind:'loan',label:'Credit channel '+i,description:'Documented mechanism '+i,evidence_url:'https://example.gov/mechanism',as_of:'2026-10-24',basis:'mechanism',amount:null});
  }
  const app=boot(data);app.run("state.flowMode='all';setView('finance');chooseFlow('extra-flow-23')");
  const html=app.elements.get('finance-view').innerHTML;
  const dimensions=html.match(/<svg class="flow-diagram" width="810" height="(\d+)" viewBox="0 0 810 (\d+)"/);
  assert.ok(dimensions);assert.equal(dimensions[1],dimensions[2]);assert.ok(Number(dimensions[1])>310,'many rows must grow the SVG beyond the previous 310px cap');
  assert.match(html,/<div class="flow-diagram-scroll" tabindex="0" role="region"/);
  const expected=new Set(data.flows.flatMap(f=>[f.source_id,f.target_id]));
  const rendered=[...html.matchAll(/data-endpoint="([^"]+)"/g)].map(m=>m[1]);
  assert.deepEqual([...new Set(rendered)].sort(),[...expected].sort());
  assert.equal(rendered.length,expected.size);
  assert.match(html,/<div class="flow-detail">[\s\S]*Documented mechanism 23/);
  const css=fs.readFileSync(path.join(root,'web/style.css'),'utf8');
  assert.match(css,/\.flow-diagram-scroll \.flow-diagram\{[^}]*min-width:810px;[^}]*height:auto;[^}]*max-height:none/);
});

test('organization, governance, event and mechanism text stays escaped in generated markup',()=>{
  const data=fixture(),attack='<img src=x onerror="alert(1)">';
  data.entities[0].name_zh=attack;data.entities[0].mission=attack;
  data.entities[0].governance={apex:attack,mechanism:attack,evidence_url:'https://example.gov/charter'};
  data.events[0].title=attack;data.events[0].summary=attack;data.flows[0].description=attack;
  const app=boot(data);
  app.run("setView('map')");
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


test('universe is the default and all directory records render as points with bounded pages',()=>{
  const data=fixture();
  for(let i=0;i<105;i++){const n=entity('bulk-'+i,'enterprise','Issuer '+String(i).padStart(3,'0'));n.name_zh=null;n.record_kind='directory';n.official_url=null;n.registry_url='https://example.gov/directory';n.identifiers={ticker:'SYMB'+i};data.entities.push(n);}
  const app=boot(data);assert.equal(app.value('state.view'),'universe');
  assert.equal([...app.elements.get('universe-view').innerHTML.matchAll(/data-point-count="(\d+)"/g)].reduce((sum,m)=>sum+Number(m[1]),0),data.entities.length);
  assert.equal((app.elements.get('entity-list').innerHTML.match(/<button class="entity-item/g)||[]).length,40);
  app.run('state.page=2;renderDirectory()');assert.match(app.elements.get('directory-pagination').innerHTML,/3 \/ 3/);
  app.elements.get('search').emit('input',{target:{value:'SYMB104'}});assert.deepEqual(app.value('visibleNodes().map(n=>n.id)'),['bulk-104']);
  assert.equal(app.value('state.page'),0);app.run("selectEntity('bulk-104')");
  assert.doesNotMatch(app.elements.get('inspector-content').innerHTML,/href="null"/);assert.match(app.elements.get('inspector-content').innerHTML,/官方名录档案/);
});

test('education filters and selection preserve access to institutions without locations',()=>{
  const data=fixture();data.entities[4].source_fields={deggrant:'1'};
  const app=boot(data);app.run("state.subset='degree';render()");assert.deepEqual(app.value('visibleNodes().map(n=>n.id)'),['uc-system']);
  app.run("selectEntity('company')");assert.equal(app.value('state.subset'),'all');
  app.run("selectEntity('uc-system',{focusMap:true,view:'map'})");assert.equal(app.value('state.view'),'map');assert.equal(app.value('state.camera.k'),2.2);
});

test('map spatial clustering keeps every eligible located record exactly once at every zoom',()=>{
  const data=fixture();
  for(let i=0;i<600;i++) {
    const location={lat:25+(i%25)*.93,lon:-124+(Math.floor(i/25)%24)*2.4,state:'CA',city:'Catalog city',precision:'campus',evidence_url:'https://example.edu/location'};
    data.entities.push(entity('mapped-'+i,'university','Mapped institution '+i,location));
  }
  data.entities.push(entity('unmapped-directory','university','Unlocated institution'));
  const app=boot(data);
  for(const domain of ['all','university']) {
    const expected=data.entities.filter(n=>n.location&&(domain==='all'||n.domain===domain)).map(n=>n.id).sort();
    for(const zoom of [.75,.9,2.2,7]) {
      app.run(`state.domain='${domain}';state.camera.k=${zoom};renderMap()`);
      const groups=app.value('state.groups.map(g=>({x:g.x,y:g.y,ids:g.nodes.map(n=>n.id)}))');
      const ids=groups.flatMap(g=>g.ids);
      assert.equal(new Set(ids).size,ids.length,'no institution may appear in two clusters');
      assert.deepEqual(ids.sort(),expected,'zoom/domain changes must not drop or invent map members');
      assert.equal(app.value('state.groups.every(g=>g.nodes.every(n=>{const p=project(n.location);return Math.hypot(p.x-g.x,p.y-g.y)<24/state.camera.k+1e-8;}))'),true,'cluster radius must follow the selected zoom');
    }
  }
});

test('large map clusters expose every organization through bounded working pagination',()=>{
  const data=fixture(),location={lat:40.7,lon:-74,state:'NY',city:'New York',precision:'campus',evidence_url:'https://example.edu/location'};
  const expected=[];
  for(let i=0;i<107;i++){const id='cluster-'+i;expected.push(id);data.entities.push(entity(id,'university','Cluster institution '+String(i).padStart(3,'0'),location));}
  const app=boot(data);app.run("setView('map');openCluster(state.groups.findIndex(g=>g.nodes.some(n=>n.id==='cluster-0')))");
  const seen=[];
  for(let page=0;page<3;page++) {
    const html=app.elements.get('map-cluster').innerHTML;
    const ids=[...html.matchAll(/data-entity="([^"]+)"/g)].map(m=>m[1]);
    assert.equal(ids.length,page===2?27:40);
    assert.equal(app.value('state.clusterPage'),page);
    seen.push(...ids);
    if(page<2)app.clickDataset({clusterPage:String(page+1)});
  }
  assert.deepEqual(seen.sort(),expected.sort());
  assert.equal(new Set(seen).size,107);
  assert.match(app.elements.get('map-cluster').innerHTML,/data-cluster-page="3" disabled/);
  app.clickDataset({clusterPage:'0'});
  assert.match(app.elements.get('map-cluster').innerHTML,/data-cluster-page="-1" disabled/);
  app.clickDataset({clusterPage:'2'});app.clickDataset({entity:'cluster-106'});
  assert.equal(app.value('state.selected'),'cluster-106');
  assert.match(app.elements.get('inspector-content').innerHTML,/Cluster institution 106/);
});

test('batched universe keeps one dot per filtered record with bounded SVG DOM geometry',()=>{
  const data=fixture(),domainOrder=['government','university','enterprise','finance'];
  for(let i=0;i<12000;i++)data.entities.push(entity('universe-'+i,domainOrder[i%4],'Catalog '+i));
  const app=boot(data);
  for(const domain of ['all','university']) {
    app.run(`setDomain('${domain}')`);
    const html=app.elements.get('universe-view').innerHTML;
    const svg=html.match(/<svg\b[\s\S]*?<\/svg>/)[0];
    const paths=[...svg.matchAll(/<path class="universe-dots" data-universe-domain="([^"]+)" data-point-count="(\d+)" d="([^"]*)"/g)];
    assert.equal(paths.length,4,'one batched path per domain, including empty domains');
    assert.ok((svg.match(/<[a-z]+\b/g)||[]).length<=30,'SVG element count must stay independent of catalog size');
    assert.doesNotMatch(svg,/<title\b|data-universe-entity=/);
    const visible=data.entities.filter(n=>domain==='all'||n.domain===domain);
    assert.equal(paths.reduce((sum,p)=>sum+Number(p[2]),0),visible.length);
    for(const path of paths){
      assert.equal(Number(path[2]),visible.filter(n=>n.domain===path[1]).length);
      assert.equal((path[3].match(/M/g)||[]).length,Number(path[2]),'every recorded point must also be painted');
    }
    assert.equal(app.value('universeLayout().byId.size'),visible.length);
  }
});

test('universe hit testing selects first middle and last dots through horizontal and vertical SVG letterboxing',()=>{
  const data=fixture();
  for(let i=0;i<213;i++)data.entities.push(entity('hit-'+i,'enterprise','Hit issuer '+String(i).padStart(3,'0')));
  const app=boot(data);
  const rects=[{left:37,top:58,width:1200,height:400},{left:15,top:190,width:400,height:400}];
  const panels=app.value('universeLayout().panels.map(p=>({id:p.id,count:p.nodes.length}))');
  for(const rect of rects)for(const panel of panels){
    for(const index of [...new Set([0,Math.floor(panel.count/2),panel.count-1])]){
      const sample=app.value(`(()=>{const p=universeLayout().panels.find(p=>p.id==='${panel.id}');return {...universePoint(p,${index}),id:p.nodes[${index}].id};})()`);
      const scale=Math.min(rect.width/960,rect.height/478);
      const clientX=rect.left+(rect.width-960*scale)/2+sample.x*scale;
      const clientY=rect.top+(rect.height-478*scale)/2+sample.y*scale;
      assert.equal(app.value(`universeHit(${clientX},${clientY},${JSON.stringify(rect)})?.id`),sample.id);
      app.clickUniverse(clientX,clientY,rect);
      assert.equal(app.value('state.selected'),sample.id,'actual delegated click must select the same record');
      assert.match(app.elements.get('universe-view').innerHTML,/class="universe-selected"/);
    }
  }
});

test('universe hit testing rejects blank space, unused grid cells, gaps and letterbox margins',()=>{
  const app=boot(),rect={left:10,top:20,width:960,height:478};
  const blankPoints=[[0,0],[480,140],[36,43],[86,66],[41,71],[200,130],[959,477]];
  for(const [x,y] of blankPoints)assert.equal(app.value(`universeHit(${x+rect.left},${y+rect.top},${JSON.stringify(rect)})`),null);
  for(const letterbox of [{left:0,top:0,width:1200,height:400},{left:0,top:0,width:400,height:400}]){
    assert.equal(app.value(`universeHit(1,1,${JSON.stringify(letterbox)})`),null);
    const selected=app.value('state.selected');app.clickUniverse(1,1,letterbox);assert.equal(app.value('state.selected'),selected);
  }
  assert.equal(app.value('universeHit(1,1,{left:0,top:0,width:0,height:400})'),null);
  app.run("state.query='NO MATCH AT ALL';renderUniverse()");
  assert.equal(app.value(`universeHit(46,86,${JSON.stringify(rect)})`),null);
});
