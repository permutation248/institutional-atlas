/* Organization World Model. All facts come from the embedded, validated dataset. */
'use strict';
const DATA = ATLAS_DATA;
const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const link = (url, label, cls = '') => `<a class="${cls}" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${esc(label)}</a>`;
const nodes = DATA.entities;
const byId = new Map(nodes.map(n => [n.id, n]));
const sectors = new Map((DATA.sectors || []).map(s => [s.id, s]));
const edges = DATA.edges;
const events = [...(DATA.events || [])].sort((a,b) => b.date.localeCompare(a.date) || a.id.localeCompare(b.id));
const flows = DATA.flows || [];
const domains = {all:{name:'全部组织',en:'ALL INSTITUTIONS',color:'#9cb7c6'},government:{name:'政府与公共机构',en:'GOVERNMENT',color:'#66b7f3'},university:{name:'高等与职业教育',en:'UNIVERSITY',color:'#c0a1f9'},enterprise:{name:'上市与企业',en:'ENTERPRISE',color:'#f2bb77'},finance:{name:'金融与资本',en:'FINANCE',color:'#66dcc6'}};
const relNames = {PART_OF:'正式组成',REPORTS_TO:'正式汇报',CONTROLLED_BY:'控制关系',FUNCTION_DELEGATED_BY:'职能授权',FINANCIALLY_DEPENDENT_ON:'持续资金依赖'};
const statusNames = {serving:'官网列示现任',confirmed:'已确认任职',acting:'代理',performing_duties:'履行职责',vacant:'职位空缺',interim:'临时',ex_officio:'当然任职',unknown:'状态待核验'};
const metrics = {authorized_budget:'预算授权',appropriation:'拨款',obligation:'支出承诺',outlay:'实际支出',contract_value:'合同金额',recognized_revenue:'确认收入',net_income:'净利润',cash_flow:'现金流'};
const state = {domain:'all',query:'',selected:byId.has('us-federal-government')?'us-federal-government':nodes[0].id,view:'universe',page:0,overviewPage:0,subset:'all',profile:'overview',camera:{k:.9,x:45,y:30},flowMode:'monetary',flowId:flows[0]?.id || null,eventId:null,groups:[],drag:null};
const snapshot = DATA.metadata.snapshot_date;
const latestReview = DATA.metadata.snapshot_date;
const shortName = n => n.name_zh || n.name;
const color = n => domains[n.domain]?.color || '#9cb7c6';
const dot = d => `<i class="domain-dot" style="--dot:${domains[d]?.color || domains.all.color}"></i>`;
const sourceLink = (url,label='查看官方依据 ↗') => url ? link(url,label,'source-link') : '';
const section = (title,body) => `<section class="profile-section"><h3>${esc(title)}</h3>${body}</section>`;
const directoryStatus = n => n.source_fields?.current_status==='not_verified_includes_historical'?'可能为历史机构 · 当前存续状态待核验':n.source_fields?.current_status==='listed_in_usagov_snapshot_not_independently_verified'?'USA.gov 名录所列 · 现行状态未逐项复核':'';
const textOrUnknown = (value,unknown='尚未核验记录') => `<p${value?'':' class="muted"'}>${esc(value || unknown)}</p>`;
const uniqueNodes = ids => [...new Set(ids)].map(id=>byId.get(id)).filter(Boolean);
const childNodes = id => uniqueNodes(edges.filter(e=>e.parent_id===id).map(e=>e.child_id));
const parentEdges = id => edges.filter(e=>e.child_id===id);
const sectorName = id => byId.has(id) ? shortName(byId.get(id)) : sectors.get(id)?.name_zh || id;
const searchIndex=new Map(nodes.map(n=>[n.id,[n.id,n.name,n.name_zh,n.city,n.state,...(n.aliases||[]),...Object.values(n.identifiers||{})].filter(Boolean).map(x=>String(x).toLowerCase())]));
const nameOrder=new Intl.Collator('en',{numeric:true,sensitivity:'base'});
function searchScore(n,q){
  if(!q) return 1;
  const fields=searchIndex.get(n.id);
  if(fields.some(x=>x===q)) return 100;
  if(fields.some(x=>x.startsWith(q))) return 50;
  if(fields.some(x=>x.includes(q))) return 20;
  return 0;
}
function matchesSubset(n){return state.subset==='all'||(state.subset==='curated'?n.record_kind!=='directory':state.subset==='mapped'?!!n.location:state.subset==='degree'?n.source_fields?.deggrant==='1':state.subset==='nondegree'?n.source_fields?.deggrant==='2':true);}
let visibleCacheKey='',visibleCache=[];
function visibleNodes(){const key=[state.domain,state.query,state.subset].join('|');if(key!==visibleCacheKey){visibleCacheKey=key;visibleCache=nodes.filter(n=>(state.domain==='all'||n.domain===state.domain)&&matchesSubset(n)).map(n=>({n,score:searchScore(n,state.query)})).filter(r=>r.score>0).sort((a,b)=>b.score-a.score||nameOrder.compare(a.n.name,b.n.name)).map(r=>r.n);}return visibleCache;}
const number = n => new Intl.NumberFormat('zh-CN').format(n);
const PAGE_SIZE=40, OVERVIEW_PAGE_SIZE=12;
function pagination(page,total,size,kind){const pages=Math.max(1,Math.ceil(total/size));return `<button data-${kind}="${page-1}" ${page===0?'disabled':''} aria-label="上一页">‹</button><span>${page+1} / ${number(pages)} 页</span><button data-${kind}="${page+1}" ${page>=pages-1?'disabled':''} aria-label="下一页">›</button>`;}

function entityButton(n){return `<button class="entity-item${state.selected===n.id?' selected':''}" data-entity="${esc(n.id)}" aria-pressed="${state.selected===n.id}"><span class="entity-item-top">${dot(n.domain)}${esc(shortName(n))}</span><small>${esc(n.aliases?.[0] || n.name)}</small></button>`;}
const UNIVERSE_WIDTH=960, UNIVERSE_HEIGHT=478;
const universePanels=[{id:'government',x:18,y:18,w:459,h:120},{id:'finance',x:489,y:18,w:453,h:120},{id:'university',x:18,y:150,w:459,h:310},{id:'enterprise',x:489,y:150,w:453,h:310}];
let universeCache={list:null,panels:[],byId:new Map()};
function universePoint(panel,index){return {x:Number((panel.x+18+(index%panel.cols)*panel.spacing).toFixed(1)),y:Number((panel.y+48+Math.floor(index/panel.cols)*panel.spacing).toFixed(1))};}
function universeLayout(list=visibleNodes()){
  if(universeCache.list===list)return universeCache;
  const lookup=new Map(),groups=new Map(universePanels.map(p=>[p.id,[]]));
  for(const n of list)groups.get(n.domain).push(n);
  const panels=universePanels.map(p=>{
    const group=groups.get(p.id),availableH=p.h-66,availableW=p.w-36;
    const spacing=Math.min(10,Math.sqrt(availableH*availableW/Math.max(1,group.length))*.92),cols=Math.max(1,Math.floor(availableW/spacing));
    const panel={...p,nodes:group,spacing,cols,radius:Number(Math.max(.65,Math.min(2.5,spacing*.28)).toFixed(2))};
    // One tiny round-capped segment paints each dot. Four paths replace one
    // circle/title DOM pair per record; the complete ID order stays in memory.
    panel.path=group.map((n,i)=>{const point=universePoint(panel,i);lookup.set(n.id,{panel,index:i});return `M${point.x},${point.y}h.01`;}).join('');
    return panel;
  });
  universeCache={list,panels,byId:lookup};return universeCache;
}
function universeViewportPoint(clientX,clientY,rect){
  if(!rect||rect.width<=0||rect.height<=0||!Number.isFinite(clientX)||!Number.isFinite(clientY))return null;
  // SVG uses xMidYMid meet: account for horizontal AND vertical letterboxing.
  const scale=Math.min(rect.width/UNIVERSE_WIDTH,rect.height/UNIVERSE_HEIGHT);
  const x=(clientX-rect.left-(rect.width-UNIVERSE_WIDTH*scale)/2)/scale;
  const y=(clientY-rect.top-(rect.height-UNIVERSE_HEIGHT*scale)/2)/scale;
  return x<0||y<0||x>UNIVERSE_WIDTH||y>UNIVERSE_HEIGHT?null:{x,y};
}
function universeHit(clientX,clientY,rect){
  const point=universeViewportPoint(clientX,clientY,rect);if(!point)return null;
  for(const panel of universeLayout().panels){
    const column=Math.round((point.x-panel.x-18)/panel.spacing),row=Math.round((point.y-panel.y-48)/panel.spacing);
    if(column<0||column>=panel.cols||row<0)continue;
    const index=row*panel.cols+column;if(index>=panel.nodes.length)continue;
    const center=universePoint(panel,index);
    if(Math.hypot(point.x-center.x,point.y-center.y)<=panel.radius+.01)return panel.nodes[index];
  }
  return null;
}
function hideUniverseHover(){$('universe-hover').hidden=true;}
function renderUniverse(){
  const list=visibleNodes(),layout=universeLayout(list);hideUniverseHover();
  const chart=layout.panels.map(p=>{
    const d=domains[p.id];
    return `<g><rect class="universe-panel" x="${p.x}" y="${p.y}" width="${p.w}" height="${p.h}" rx="6" style="stroke:${d.color}33"/><text x="${p.x+18}" y="${p.y+25}" fill="${d.color}" class="universe-label">${esc(d.name)} <tspan fill="#d9e6ee">${number(p.nodes.length)}</tspan></text><text x="${p.x+p.w-18}" y="${p.y+25}" text-anchor="end" class="universe-en">${d.en}</text><path class="universe-dots" data-universe-domain="${p.id}" data-point-count="${p.nodes.length}" d="${p.path}" stroke="${d.color}" stroke-width="${p.radius*2}"/></g>`;
  }).join('');
  const selected=layout.byId.get(state.selected),selectedPoint=selected?universePoint(selected.panel,selected.index):null;
  const selectedMarker=selectedPoint?`<circle class="universe-selected" cx="${selectedPoint.x}" cy="${selectedPoint.y}" r="${selected.panel.radius+2}"/>`:'';
  state.overviewPage=Math.min(state.overviewPage,Math.max(0,Math.ceil(list.length/OVERVIEW_PAGE_SIZE)-1));
  const slice=list.slice(state.overviewPage*OVERVIEW_PAGE_SIZE,(state.overviewPage+1)*OVERVIEW_PAGE_SIZE);
  const options={all:'全部收录',curated:'已有研究档案',mapped:'已有地图位置',degree:'授予学位的教育机构',nondegree:'非学位教育机构'};
  $('universe-view').innerHTML=`<div class="universe-intro"><div><span class="eyebrow">ONE INSTITUTION · ONE POINT</span><h3>把组织放进同一幅图景。</h3><p>每个光点对应一条组织记录。选择光点或下方卡片，查看身份、治理与金融关系。</p></div><label class="catalog-filter-label">收录范围<select id="catalog-filter" aria-label="收录范围">${Object.entries(options).map(([v,t])=>`<option value="${v}"${v===state.subset?' selected':''}>${t}</option>`).join('')}</select></label></div><svg class="universe-chart" data-universe-chart viewBox="0 0 960 478" preserveAspectRatio="xMidYMid meet" role="img" aria-label="全部已筛选组织总览，${list.length} 个光点，按领域排列；可使用下方组织列表访问相同记录">${chart}${selectedMarker}</svg><div class="universe-chart-note"><span>按领域编排 · 图块面积不代表组织规模 · 光点不是隶属连线</span><span>${number(list.filter(n=>n.location).length)} 个可定位 / ${number(list.length)} 个组织</span></div><div class="universe-directory-head"><div><h3>${state.query?'搜索结果':domains[state.domain].name} <span>${number(list.length)}</span></h3><p>完整目录按名称排序，可逐页浏览；左侧搜索支持名称、简称、证券代码与编号。</p></div><div class="overview-pagination">${pagination(state.overviewPage,list.length,OVERVIEW_PAGE_SIZE,'overview-page')}</div></div><div class="universe-cards">${slice.map(n=>`<article class="universe-card${n.id===state.selected?' selected':''}" style="--card-color:${color(n)}"><button data-entity="${esc(n.id)}"><span class="universe-card-type">${dot(n.domain)}${esc(n.institution_type||domains[n.domain].name)}</span><strong>${esc(shortName(n))}</strong><small>${esc(n.listings?.map(l=>l.ticker).join(' / ')||n.aliases?.[0]||n.id)}</small></button><div><span>${n.record_kind==='directory'?'名录记录':'研究档案'}</span>${n.location?`<button data-locate="${esc(n.id)}" aria-label="在地图上定位${esc(shortName(n))}">⌖ ${esc(n.location.state)} ↗</button>`:'<span>坐标待补充</span>'}</div></article>`).join('')||'<div class="empty-state">没有符合当前条件的组织；可清除搜索或切换收录范围。</div>'}</div>`;
  $('view-count').textContent=`${number(list.length)} / ${number(nodes.length)} ORGANIZATIONS`;
  $('view-note').textContent='总览 → 组织档案 → 层级 / 金融 / 地图';
}
function renderCoverage(){
  const scopeText={ipeds:'美国 50 州与 DC 的活跃教学机构，涵盖大学、两年制学院及职业教育。可筛选 3,877 个学位授予机构。',agencies:'联邦机构与公共组织的官方索引，保留历史条目。尚未覆盖全部州和地方机构。',nasdaq:'美国交易所上市发行人，包含外国公司、封闭式基金及 SPAC；ETF 与测试证券已排除。名称组仍需法律身份核对。'};
  const catalogs=DATA.metadata.catalogs||[];
  $('catalog-coverage').innerHTML=`<div class="coverage-heading"><div><span class="eyebrow">SOURCE COVERAGE</span><h2>系统收录，边界透明。</h2></div><span>${number(nodes.filter(n=>n.record_kind!=='directory').length)} 份研究档案 · ${catalogs.length} 个官方名录</span></div><div class="coverage-grid">${catalogs.map(c=>`<article class="coverage-card"><div><span>${esc(c.id.toUpperCase())}</span><strong>${number(c.included_count)}</strong></div><h3>${esc(c.title)}</h3><p>${esc(scopeText[c.id]||c.scope)}</p><small>${esc((c.id==='nasdaq'?'证券目录 2026-10-23':c.id==='ipeds'?'2025–26 教育目录':null)||c.source_period||'官方目录快照')}<br>采集 ${esc(c.retrieved_at)} · ${number(c.matched_curated_count||0)} 个与研究档案合并</small><details><summary>覆盖口径与排除项</summary><p>原始 ${number(c.raw_count)} 条；纳入 ${number(c.included_count)} 个目录身份；排除 ${number(c.excluded_count)} 条，跨源/证券类别归并另计。详细口径见下文。</p>${(Array.isArray(c.coverage_notes)?c.coverage_notes:[c.coverage_notes]).filter(Boolean).map(t=>`<p>${esc(t)}</p>`).join('')}</details>${sourceLink(c.source_url,'官方完整数据源 ↗')}</article>`).join('')}</div><p class="coverage-note">名录回答“有哪些组织”，研究档案回答“组织如何运转”。未查明的隶属、负责人、现金流和总部位置保留为空；当前政府来源不覆盖美国所有州、市及特殊地方机构。美国上市不等于美国注册公司。发行人名称分组不保证唯一法人，跨源身份仍在完善。</p>`;
}

function renderDirectory(){
  $('domain-nav').innerHTML=Object.entries(domains).map(([id,d])=>`<button class="domain-button${id===state.domain?' active':''}" data-domain="${id}" aria-pressed="${id===state.domain}">${dot(id)}<span>${d.name}</span><span>${id==='all'?nodes.length:nodes.filter(n=>n.domain===id).length}</span></button>`).join('');
  const result=visibleNodes();
  $('directory-count').textContent=`${result.length} ENTITIES`;
  state.page=Math.min(state.page,Math.max(0,Math.ceil(result.length/PAGE_SIZE)-1));
  $('directory-pagination').innerHTML=pagination(state.page,result.length,PAGE_SIZE,'directory-page');
  $('entity-list').innerHTML=result.slice(state.page*PAGE_SIZE,(state.page+1)*PAGE_SIZE).map(entityButton).join('') || '<div class="empty-state">没有匹配的组织。试试简称，或切换到全部组织。</div>';
  document.querySelector('.directory').classList.toggle('searching',!!state.query);
}
function syncHash(){
  const params=new URLSearchParams();
  if(state.view!=='universe') params.set('view',state.view);
  if(state.subset!=='all') params.set('subset',state.subset);
  if(state.domain!=='all') params.set('domain',state.domain);
  const hash=`#${state.selected}${params.size?'?'+params:''}`;
  if(location.hash!==hash) history.pushState(null,'',hash);
}
function readHash(){
  const [id,query='']=location.hash.slice(1).split('?');
  if(byId.has(id)) state.selected=id;
  const p=new URLSearchParams(query);
  state.view=['universe','map','structure','finance'].includes(p.get('view'))?p.get('view'):'universe';
  state.subset=['all','curated','mapped','degree','nondegree'].includes(p.get('subset'))?p.get('subset'):'all';
  state.domain=Object.keys(domains).includes(p.get('domain'))?p.get('domain'):'all';
}
function selectEntity(id,{focusMap=false,view=null}={}){
  if(!byId.has(id)) return;
  state.selected=id;
  if(!matchesSubset(byId.get(id)))state.subset='all';
  if(view) state.view=view;
  if(state.domain!=='all'&&byId.get(id).domain!==state.domain) state.domain='all';
  if(state.query&&!searchScore(byId.get(id),state.query)){state.query='';$('search').value='';}
  $('map-cluster').hidden=true;
  if(focusMap&&byId.get(id).location){const p=project(byId.get(id).location);state.camera={k:2.2,x:500-p.x*2.2,y:310-p.y*2.2};}
  syncHash();render();
  $('announcement').textContent=`已选择${shortName(byId.get(id))}`;
}
function project(loc){
  let lon=loc.lon,lat=loc.lat;
  if(loc.state==='AK'||lat>53){if(lon>0)lon-=360;return{x:20+(lon+190)/60*230,y:480+(72-lat)/22*105};}
  if(loc.state==='HI'||(lat<24&&lon<-150)) return{x:285+(lon+161)/7*130,y:490+(23-lat)/5*85};
  return{x:(lon+125)/59*1000,y:(50-lat)/26*600};
}
function renderMapBase(){
  const geo=DATA.geography;
  if(!geo?.states?.length){$('map-land').innerHTML='<text x="500" y="300" fill="#8ba9ba" text-anchor="middle">州界数据尚未载入</text>';return;}
  const labels=[['CA',-120,37],['TX',-99.3,31],['FL',-82.4,28],['WA',-120.5,47.4],['NY',-75.5,43],['CO',-105.5,39],['MT',-110,47],['NV',-116.5,39],['AZ',-111.7,34],['NM',-106,34],['UT',-111.5,39.4],['WY',-107.5,43.2],['ID',-114,44],['OR',-120.5,44],['ND',-100,47.4],['SD',-100,44.4],['NE',-99.5,41.5],['KS',-98.5,38.5],['OK',-97.7,35.5],['MN',-94.5,46],['IA',-93.5,42],['MO',-92.5,38.4],['AR',-92.5,34.8],['LA',-92,31],['WI',-90,44.5],['IL',-89,40.2],['MS',-89.8,32.6],['AL',-86.8,32.5],['GA',-83.3,32.6],['SC',-80.9,33.6],['NC',-79,35.6],['TN',-86,35.8],['KY',-85.5,37.5],['IN',-86,40],['MI',-84.5,44],['OH',-82.8,40.2],['VA',-79,37.7],['PA',-77.5,41],['ME',-69,45.2]];
  $('map-land').innerHTML=geo.states.map(s=>`<path class="state-path" d="${esc(s.path)}"><title>${esc(s.name)}</title></path>`).join('')+labels.map(([label,lon,lat])=>{const p=project({lon,lat});return `<text class="state-label" x="${p.x}" y="${p.y}">${label}</text>`;}).join('')+'<text class="map-region-label" x="60" y="612">ALASKA</text><text class="map-region-label" x="305" y="612">HAWAII</text>';
}
function eventFiltered({selectedOnly=$('events-selected').checked}={}){
  const period=$('event-period').value;
  const cutoff=period==='all'?-Infinity:new Date(latestReview+'T00:00:00Z').getTime()-Number(period)*86400000;
  return events.filter(e=>new Date(e.date+'T00:00:00Z').getTime()>=cutoff && (!selectedOnly||e.entity_ids.includes(state.selected)) && (state.domain==='all'||e.entity_ids.some(id=>byId.get(id)?.domain===state.domain)));
}
function renderMap(){
  const list=visibleNodes().filter(n=>n.location);
  const groups=[],grid=new Map();const threshold=24/state.camera.k,thresholdSquared=threshold*threshold;
  for(const n of list){
    const p=project(n.location),gx=Math.floor(p.x/threshold),gy=Math.floor(p.y/threshold);let g=null;
    for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++)for(const candidate of grid.get(`${gx+dx},${gy+dy}`)||[]){if((p.x-candidate.x)**2+(p.y-candidate.y)**2<thresholdSquared&&(!g||candidate.index<g.index))g=candidate;}
    if(!g){g={x:p.x,y:p.y,nodes:[],index:groups.length};groups.push(g);const key=`${gx},${gy}`;if(!grid.has(key))grid.set(key,[]);grid.get(key).push(g);}g.nodes.push(n);
  }
  state.groups=groups;
  const eventIds=new Set(eventFiltered({selectedOnly:false}).flatMap(e=>e.entity_ids));
  const selected=byId.get(state.selected);
  const relationPaths=[];
  if($('show-relations').checked&&selected.location){
    const allowed=new Set(list.map(n=>n.id));const p=project(selected.location);
    edges.filter(e=>e.parent_id===selected.id||e.child_id===selected.id).forEach(e=>{
      const other=byId.get(e.parent_id===selected.id?e.child_id:e.parent_id);
      if(!other?.location||!allowed.has(other.id))return;
      const q=project(other.location);if(Math.hypot(p.x-q.x,p.y-q.y)<3)return;
      const a=e.parent_id===selected.id?p:q,b=e.parent_id===selected.id?q:p;
      const height=Math.min(65,Math.hypot(a.x-b.x,a.y-b.y)*.2);
      relationPaths.push(`<path class="map-edge" d="M${a.x},${a.y} Q${(a.x+b.x)/2},${(a.y+b.y)/2-height} ${b.x},${b.y}" marker-end="url(#map-arrow)"><title>${esc(shortName(byId.get(e.parent_id)))} → ${esc(shortName(byId.get(e.child_id)))} · ${esc(relNames[e.type])}（展示方向）</title></path>`);
    });
  }
  if($('show-funding').checked){
    const allowed=new Set(list.map(n=>n.id));
    for(const flow of flows){
      const from=byId.get(flow.source_id),to=byId.get(flow.target_id);
      if(!from?.location||!to?.location||!allowed.has(from.id)||!allowed.has(to.id))continue;
      const a=project(from.location),b=project(to.location);
      if(Math.hypot(a.x-b.x,a.y-b.y)<3)continue;
      relationPaths.push(`<path class="map-edge funding-edge" d="M${a.x},${a.y} Q${(a.x+b.x)/2+28},${(a.y+b.y)/2-30} ${b.x},${b.y}" marker-end="url(#funding-arrow)"><title>${esc(flow.label)} · ${esc(shortName(from))} → ${esc(shortName(to))} · 机制示意，无金额</title></path>`);
    }
  }
  $('map-lines').innerHTML=relationPaths.join('');
  $('map-pins').innerHTML=groups.map((g,i)=>{
    const chosen=g.nodes.some(n=>n.id===state.selected),hasEvents=$('show-events').checked&&g.nodes.some(n=>eventIds.has(n.id));
    const single=g.nodes.length===1;
    const n=chosen?selected:g.nodes[0];const c=single?color(n):'#82c9d0';
    const r=single?4.5:Math.min(13,7+Math.log2(g.nodes.length)*1.3);
    const city=g.nodes[0].location.city;
    const label=chosen||g.nodes.length>=3?city:'';
    return `<g class="map-pin" transform="translate(${g.x} ${g.y}) scale(${1/state.camera.k})" style="color:${c}" tabindex="0" role="button" data-cluster="${i}" aria-label="${esc(single?shortName(n):`${city}附近 ${g.nodes.length} 个组织`)}">${hasEvents?`<circle class="pin-event" r="${r+14}"/>`:''}<circle class="pin-ring" r="${r+6}"/>${chosen?`<circle class="pin-selected" r="${r+10}"/>`:''}<circle class="pin-core" fill="${c}" r="${r}"/>${single?'':`<text class="pin-count">${g.nodes.length}</text>`}${label?`<text class="pin-label" x="${r+9}" y="3">${esc(label)}</text>`:''}<title>${esc(g.nodes.slice(0,5).map(shortName).join(' / '))}${g.nodes.length>5?' …':''}</title></g>`;
  }).join('');
  const {k,x,y}=state.camera;$('map-camera').setAttribute('transform',`translate(${x} ${y}) scale(${k})`);
  if(state.view==='map'){
    $('view-count').textContent=`${list.length} MAPPED / ${visibleNodes().length} ENTITIES`;
    $('view-note').textContent=`${visibleNodes().length-list.length} 个待定位 · 校园 / 总部 / 城市位置 · ${Math.round(k/.9*100)}%`;
  }
}
function openCluster(index,page=0){
  const group=state.groups[index];if(!group)return;
  if(group.nodes.length===1){selectEntity(group.nodes[0].id);return;}
  state.clusterIndex=index;state.clusterPage=Math.max(0,Math.min(page,Math.ceil(group.nodes.length/PAGE_SIZE)-1));
  $('map-cluster').innerHTML=`<div class="cluster-head"><strong>${esc(group.nodes[0].location.city)}附近 · ${group.nodes.length} 个组织</strong><button data-close-cluster aria-label="关闭地点列表">×</button></div>${group.nodes.slice(state.clusterPage*PAGE_SIZE,(state.clusterPage+1)*PAGE_SIZE).map(entityButton).join('')}<div class="overview-pagination">${pagination(state.clusterPage,group.nodes.length,PAGE_SIZE,'cluster-page')}</div>`;
  $('map-cluster').hidden=false;
}
function treeCard(n,label,cls=''){return `<button class="tree-card ${cls}" data-entity="${n.id}"><small>${esc(label)}</small><strong>${esc(shortName(n))}</strong><span>${esc(n.aliases?.[0] || n.name)}</span></button>`;}
function renderStructure(){
  const n=byId.get(state.selected);const parents=parentEdges(n.id),children=childNodes(n.id);
  let ancestors=[],current=n,visited=new Set([n.id]);
  while(parentEdges(current.id).length){const p=byId.get(parentEdges(current.id)[0].parent_id);if(!p||visited.has(p.id))break;ancestors.unshift(p);visited.add(p.id);current=p;}
  const breadcrumbs=`<nav class="structure-breadcrumb" aria-label="组织层级路径"><span>美国 / ${domains[n.domain].name}</span>${ancestors.map(p=>`<span>›</span><button data-entity="${p.id}">${esc(shortName(p))}</button>`).join('')}<span>›</span><span>${esc(shortName(n))}</span></nav>`;
  const parentCards=parents.map(e=>treeCard(byId.get(e.parent_id),relNames[e.type]+' · 上级或依赖对象')).join('');
  const childrenCards=children.map(c=>{const types=edges.filter(e=>e.parent_id===n.id&&e.child_id===c.id).map(e=>relNames[e.type]);return treeCard(c,types.join(' / '));}).join('');
  const note=n.id==='us-federal-government'?'三个分支并立、相互制衡。国会与司法分支均不向总统汇报。':children.length?'点击组织继续下钻。连线显示已记录的正式关系，详细证据见右侧档案。':'本数据集中尚未记录该组织的下级；这不代表现实中没有下设单位。';
  $('structure-view').innerHTML=breadcrumbs+`<div class="structure-tree">${parentCards?`<div class="tree-parent-row">${parentCards}</div><div class="tree-trunk"></div>`:''}${treeCard(n,'当前组织','current')}${childrenCards?`<div class="tree-trunk"></div><div class="tree-children">${childrenCards}</div>`:''}<p class="tree-note">${esc(note)}</p></div>`;
  $('view-count').textContent=`${parents.length} PARENTS / ${children.length} CHILDREN`;
  $('view-note').textContent='上 → 下为展示方向；资金往来单独展示';
}
function renderProfile(){
  const n=byId.get(state.selected),d=domains[n.domain],g=n.governance,loc=n.location,leader=n.leader,parents=parentEdges(n.id),children=childNodes(n.id);
  $('btn-mobile-profile').textContent='查看'+shortName(n)+'档案 ↗';
  let body='';
  if(n.catalog_records?.length){body+=section('名录身份与来源',`<p>${esc(n.institution_type||n.jurisdiction||'')}</p><p>${Object.entries(n.identifiers||{}).map(([k,v])=>esc(k.toUpperCase())+': '+esc(v)).join(' · ')}</p>${n.listings?.length?'<p>'+n.listings.map(l=>esc(l.ticker)+' / '+esc(l.exchange)).join(' · ')+'</p>':''}${n.catalog_records.map(r=>sourceLink(r.registry_url,`${r.source_id.toUpperCase()} · ${r.source_period||r.retrieved_at} ↗`)).join('')}`);}
  if(state.profile==='overview'){
    body+=section('使命与职责',textOrUnknown(n.mission||n.function));
    if(n.record_kind==='directory'&&(n.source_fields?.description||n.source_fields?.usagov?.description))body+=section('官方目录简介 · 原文',textOrUnknown(n.source_fields.usagov?.description||n.source_fields.description)+textOrUnknown(null,'目录原文可能保留历史叙述，不能代替现行职责核验。'));
    if(n.ecosystem_role)body+=section('生态定位',textOrUnknown(n.ecosystem_role));
    body+=section('最高治理主体',g?`<div class="apex-card"><small>GOVERNANCE APEX</small><strong>${esc(g.apex)}</strong>${sourceLink(g.evidence_url)}</div>`:textOrUnknown(null,'最高治理主体尚未单独核验；不能仅凭负责人头衔推断。'));
    body+=section('收敛机制 · 如何形成决定',g?textOrUnknown(g.mechanism)+sourceLink(g.evidence_url,'制度与决策依据 ↗'):textOrUnknown(null,'议事、表决与授权流程待补充。'));
    body+=section('负责人 / 执行岗位',leader?`<p>${esc(leader.name||'职位空缺')}<span class="profile-pill">${esc(statusNames[leader.status]||leader.status)}</span></p><p class="muted">${esc(leader.title)}</p>${leader.formal_position?`<p class="muted">${esc(leader.formal_position)}</p>`:''}${sourceLink(leader.evidence_url,`${leader.as_of} · 任职依据 ↗`)}`:textOrUnknown(null,'负责人姓名尚未单独核验；治理机制见上方。'));
    const relationships=parents.map(e=>`<div class="relation-card"><button data-entity="${e.parent_id}">${esc(shortName(byId.get(e.parent_id)))}<small>${esc(relNames[e.type])}</small></button>${link(e.evidence_url,'↗')}</div>`).join('');
    body+=section('隶属与结构',relationships?`<div class="profile-relationships">${relationships}</div>`:textOrUnknown(null,'当前记录无上级关系；独立入口不等于无监管。'));
    body+=`<button class="profile-action" data-profile-view="structure">探索组织层级 · ${children.length} 个已记录下级 ↗</button>`;
    const recent=events.filter(e=>e.entity_ids.includes(n.id)).slice(0,2);
    if(recent.length) body+=section('相关事件',recent.map(e=>`<article class="event-card"><div class="event-date"><time datetime="${e.date}">${esc(e.date)}</time><span>${esc(e.category)}</span></div><h3>${esc(e.title)}</h3><p>${esc(e.summary)}</p>${sourceLink(e.source_url,(e.source_name||'官方原文')+' ↗')}</article>`).join(''));
  }else if(state.profile==='funding'){
    const fm=n.funding_model;
    body+=section('资金如何支持运转',textOrUnknown(fm?.summary));
    if(fm){body+=`<div class="funding-columns"><div class="funding-column"><strong>↓ 资金来源</strong><ul>${fm.inflows.length?fm.inflows.map(s=>`<li>${esc(s)}</li>`).join(''):'<li>尚未记录</li>'}</ul></div><div class="funding-column"><strong>↑ 资金用途</strong><ul>${fm.outflows.length?fm.outflows.map(s=>`<li>${esc(s)}</li>`).join(''):'<li>尚未记录</li>'}</ul></div></div>${sourceLink(fm.evidence_url,'资金组织方式 · 官方依据 ↗')}`;}
    body+=section('已记录财务指标',(n.financial_profile||[]).length?n.financial_profile.map(m=>`<div class="profile-money">${esc(metrics[m.metric||m.type]||m.metric)} · ${esc(m.fiscal_year||m.reporting_period)}<strong>${esc(m.currency)} ${new Intl.NumberFormat('zh-CN',{maximumFractionDigits:2}).format(m.value)}</strong>${esc(m.scope||m.reporting_scope)}<br>${sourceLink(m.source_url)}</div>`).join(''):textOrUnknown(null,'尚未录入可比金额。预算、支出、收入、利润和资产不能混为同一指标。'));
    const related=flows.filter(f=>f.source_id===n.id||f.target_id===n.id);
    body+=section('关联资金机制',related.length?`<div class="profile-relationships">${related.map(f=>`<div class="relation-card"><button data-flow="${f.id}">${esc(f.label)}<small>${esc(sectorName(f.source_id))} → ${esc(sectorName(f.target_id))}</small></button>${link(f.evidence_url,'↗')}</div>`).join('')}</div>`:textOrUnknown(null,'该机构尚无单独记录的资金流；可在金融视图查看制度机制。'));
    body+='<button class="profile-action" data-profile-view="finance">进入金融循环视图 ↗</button>';
  }else{
    if(loc)body+=section('地理位置',`<p>${esc(loc.city)}, ${esc(loc.state)} · ${loc.lat.toFixed(3)}, ${loc.lon.toFixed(3)}</p><p class="muted">精度：${({city:'城市近似点',campus:'校区',headquarters:'总部'})[loc.precision]}。${esc(loc.note||'')}</p>${sourceLink(loc.evidence_url,'位置依据 ↗')}`);
    body+=section('官方来源',`<div class="source-list">${n.sources.map(s=>link(s.url,(s.description||new URL(s.url).hostname)+' ↗')).join('')}</div>`);
    body+=section('公告与公开内容',n.publications.length?`<div class="source-list">${n.publications.map(p=>link(p.url,p.label+' ↗')).join('')}</div>`:textOrUnknown(null,'尚未单独记录公告入口。'));
    body+=section('人员规模',n.employee_count?`<p>${new Intl.NumberFormat('zh-CN').format(n.employee_count.value)} · ${esc(n.employee_count.unit)}</p><p class="muted">${esc(n.employee_count.period)}</p>${sourceLink(n.employee_count.evidence_url)}`:textOrUnknown(null,'未核验；未知不等于零。'));
    if(n.research_notes)body+=section('核验范围与缺失',textOrUnknown(n.research_notes));
  }
  $('inspector-content').innerHTML=`<span class="profile-domain" style="--domain-color:${d.color}">${dot(n.domain)}${d.en}</span><h2 class="profile-name">${esc(shortName(n))}</h2><p class="profile-english">${esc(n.name)}</p><div class="profile-meta">${loc?'⌖ '+esc(loc.city)+', '+esc(loc.state):'⌖ 地理位置待核验'}<br>${esc(n.id)}</div>${n.official_url?link(n.official_url,'官方网站 ↗','official-link'):sourceLink(n.registry_url,'官方名录档案 ↗')}<div class="record-badge">${n.record_kind==='directory'?'官方名录记录 · 详细档案待补充':'研究档案'}${n.institution_type?' · '+esc(n.institution_type):''}${directoryStatus(n)?'<br>'+esc(directoryStatus(n)):''}</div>${loc?'<button class="locate-button" data-locate="'+esc(n.id)+'">⌖ 在独立地图上定位 ↗</button>':'<div class="location-pending">坐标待核验 · 已保留在组织总览</div>'}<nav class="profile-tabs" aria-label="组织档案内容"><button data-profile="overview" class="${state.profile==='overview'?'active':''}">组织与治理</button><button data-profile="funding" class="${state.profile==='funding'?'active':''}">金融</button><button data-profile="sources" class="${state.profile==='sources'?'active':''}">来源</button></nav>${body}<div class="profile-foot">${n.record_kind==='directory'?'名录采集 '+esc(n.catalog_records?.[0]?.retrieved_at)+' · 详细事实未核验':'记录日期 '+esc(n.verified_at)+(n.research_reviewed_at?' · 局部复核 '+esc(n.research_reviewed_at):' · 继承记录')}<br>来源与字段覆盖不代表完整或实时；未知字段保留。</div>`;
}
const flowModes={monetary:'货币与信贷',fiscal:'财政与公共服务',capital:'资本与创新',all:'完整循环'};
function routeFlows(){
  if(state.flowMode==='all')return flows;
  return flows.filter(f=>{
    const ids=[f.source_id,f.target_id];
    if(state.flowMode==='monetary')return ids.some(id=>['us-fed','us-fomc','us-nyfed','banks'].includes(id))||/deposit|credit|monetary|loan|存款|贷款|利率|信贷|货币/.test(f.kind+' '+f.label);
    if(state.flowMode==='fiscal')return ids.some(id=>['us-treasury','us-irs','us-fiscal','federal-budget','us-congress','us-nih','us-nsf','us-education'].includes(id));
    return ids.some(id=>['investors','capital-markets','universities'].includes(id))||/equity|investment|资本|股权|证券|科研/.test(f.kind+' '+f.label);
  });
}
function renderFinance(){
  let list=routeFlows();
  if(!list.length){$('finance-view').innerHTML='<div class="empty-state">此类金融机制尚未录入。</div>';return;}
  let active=list.find(f=>f.id===state.flowId)||list[0];state.flowId=active.id;
  const ids=[...new Set(list.flatMap(f=>[f.source_id,f.target_id]))];
  const leftIds=new Set(['households','investors','businesses','us-fomc','us-congress']);
  const centerIds=new Set(['banks','us-treasury','us-fed','capital-markets','federal-budget','us-irs','us-nyfed']);
  const cols=[[],[],[]];ids.forEach(id=>cols[leftIds.has(id)?0:centerIds.has(id)?1:2].push(id));
  // Move excess nodes to sparse columns; each flow keeps its actual source and target.
  while(Math.max(...cols.map(c=>c.length))-Math.min(...cols.map(c=>c.length))>2){const max=cols.indexOf(cols.reduce((a,b)=>a.length>b.length?a:b));const min=cols.indexOf(cols.reduce((a,b)=>a.length<b.length?a:b));cols[min].push(cols[max].pop());}
  const maxRows=Math.max(...cols.map(c=>c.length));const height=Math.max(285,maxRows*73+35);const positions={};
  cols.forEach((col,c)=>col.forEach((id,r)=>positions[id]={x:[105,405,705][c],y:35+(r+.5)*(height-70)/col.length}));
  const pathMarkup=list.map((f,i)=>{
    const a=positions[f.source_id],b=positions[f.target_id];let path,mx,my;
    if(a.x===b.x){const side=a.x>400?-1:1;const cx=a.x+side*120;path=`M${a.x+side*83},${a.y} C${cx},${a.y} ${cx},${b.y} ${b.x+side*83},${b.y}`;mx=cx;my=(a.y+b.y)/2;}
    else{const dir=b.x>a.x?1:-1;const ax=a.x+dir*84,bx=b.x-dir*84;path=`M${ax},${a.y} C${(ax+bx)/2},${a.y} ${(ax+bx)/2},${b.y} ${bx},${b.y}`;mx=(ax+bx)/2;my=(a.y+b.y)/2-7;}
    return `<path class="flow-path${f.id===active.id?' active':''}" d="${path}" marker-end="url(#flow-arrow)"><title>${esc(f.label)}</title></path>${f.id===active.id?`<text class="flow-label" x="${mx}" y="${my}" text-anchor="middle">${esc(f.label.length>16?f.label.slice(0,16)+'…':f.label)}</text>`:''}`;
  }).join('');
  const nodeMarkup=ids.map(id=>{const p=positions[id],n=byId.get(id),name=sectorName(id);const selected=[active.source_id,active.target_id].includes(id);const max=11;const chunks=name.length>max?[name.slice(0,max),name.slice(max,max*2)]:[name];return `<g class="flow-node${selected?' active':''}" transform="translate(${p.x} ${p.y})" role="button" tabindex="0" data-endpoint="${id}" aria-label="${esc(name)}"><rect x="-84" y="-27" width="168" height="54" rx="5"/>${chunks.map((s,i)=>`<text text-anchor="middle" y="${chunks.length>1?-7+i*15:-2}">${esc(s)}</text>`).join('')}<text class="flow-node-sub" y="19" text-anchor="middle">${n?domains[n.domain].en:'概念部门 · 非单一机构'}</text></g>`;}).join('');
  $('finance-view').innerHTML=`<div class="finance-intro"><div><h3>${flowModes[state.flowMode]} · 资金与决策通道</h3><p>选择一条机制，追踪来源、流向与用途。箭头与线宽均不代表已发生交易金额。</p></div><div class="finance-selects"><select id="flow-mode" aria-label="金融路径类型">${Object.entries(flowModes).map(([key,value])=>`<option value="${key}"${state.flowMode===key?' selected':''}>${value}</option>`).join('')}</select><select id="flow-selection" aria-label="选择金融机制">${list.map(f=>`<option value="${f.id}"${f.id===active.id?' selected':''}>${esc(f.label)}</option>`).join('')}</select></div></div><div class="flow-diagram-scroll" tabindex="0" role="region" aria-label="金融机制图；窄屏可横向滚动"><svg class="flow-diagram" width="810" height="${height}" viewBox="0 0 810 ${height}" preserveAspectRatio="xMidYMin meet" role="group" aria-label="金融流转机制图"><defs><marker id="flow-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0L7 3.5L0 7" fill="#75cbb6"/></marker></defs>${pathMarkup}${nodeMarkup}</svg></div><div class="flow-detail"><div class="flow-detail-head"><strong>${esc(active.label)}</strong><span>机制示意 · 金额未量化</span></div><p>${esc(sectorName(active.source_id))} → ${esc(sectorName(active.target_id))}</p><p>${esc(active.description)}</p>${sourceLink(active.evidence_url,`官方机制依据 ↗ · ${active.as_of}`)}</div><div class="flow-navigation" aria-label="选择金融流转">${list.map((f,i)=>`<button data-flow="${f.id}" class="${active.id===f.id?'active':''}">${String(i+1).padStart(2,'0')} ${esc(f.label)}</button>`).join('')}</div>`;
  $('view-count').textContent=`${list.length} MECHANISMS / ${ids.length} ENDPOINTS`;
  $('view-note').textContent='概念部门 + 已记录组织 · 机制关系不构成隶属';
}
function renderEvents(){
  const list=eventFiltered();$('event-count').textContent=list.length;
  $('events-list').innerHTML=list.map(e=>`<article class="event-card${e.id===state.eventId?' active':''}" data-event-card="${e.id}"><div class="event-date"><time datetime="${e.date}">${esc(e.date)}</time><span>${esc(e.category)}</span></div><h3>${esc(e.title)}</h3><p>${esc(e.summary)}</p><div class="event-links"><button class="event-focus" data-event="${e.id}">⌖ ${esc(sectorName(e.entity_ids[0]))}</button>${link(e.source_url,(e.source_name||'官方原文')+' ↗')}</div></article>`).join('') || '<div class="empty-state"><strong>当前范围内没有已核验的事件</strong>可以切换时间范围、取消“当前组织”或从官网公告查看。没有记录不代表没有事件。</div>';
  $('event-asof').textContent=`核验截至 ${latestReview}，非实时推送。`;
}
function render(){
  hideUniverseHover();renderDirectory();renderProfile();renderEvents();
  document.querySelectorAll('[data-view]').forEach(b=>{b.classList.toggle('active',b.dataset.view===state.view);b.setAttribute('aria-pressed',String(b.dataset.view===state.view));});
  for(const name of ['universe','map','structure','finance']) $(name+'-view').hidden=name!==state.view;
  $('view-kicker').textContent={universe:'组织全域 / ORGANIZATION UNIVERSE',map:'美国组织分布 / INSTITUTIONAL MAP',structure:'组织层级 / STRUCTURAL RELATIONS',finance:'金融流转 / FINANCIAL CIRCULATION'}[state.view];
  $('legend').innerHTML=state.view==='finance'?'<span><i class="domain-dot"></i>资金 / 决策方向</span><span>虚线：制度机制</span>':Object.entries(domains).filter(([id])=>id!=='all').map(([id,d])=>`<span>${dot(id)}${d.name.split('与')[0]}</span>`).join('');
  if(state.view==='universe')renderUniverse();else if(state.view==='map')renderMap();else if(state.view==='structure')renderStructure();else renderFinance();
}
function setView(view){hideUniverseHover();state.view=view;$('map-tooltip').hidden=true;syncHash();render();}
function setDomain(id){state.domain=id;state.query='';state.page=0;state.overviewPage=0;state.subset='all';$('search').value='';$('map-cluster').hidden=true;state.camera={k:.9,x:45,y:30};syncHash();render();}
function chooseFlow(id){
  const f=flows.find(f=>f.id===id);if(!f)return;
  state.flowId=id;state.view='finance';if(!routeFlows().some(x=>x.id===id))state.flowMode='all';
  syncHash();render();
}
function zoom(factor,anchor={x:500,y:325}){
  const c=state.camera,n=Math.max(.75,Math.min(7,c.k*factor));
  const ratio=n/c.k;c.x=anchor.x-(anchor.x-c.x)*ratio;c.y=anchor.y-(anchor.y-c.y)*ratio;c.k=n;
  $('map-cluster').hidden=true;renderMap();
}
function pointInSvg(event){const p=$('us-map').createSVGPoint();p.x=event.clientX;p.y=event.clientY;return p.matrixTransform($('us-map').getScreenCTM().inverse());}
function route(name){
  state.query='';$('search').value='';state.domain='all';state.subset='all';state.page=0;state.overviewPage=0;state.camera={k:.9,x:45,y:30};
  if(name==='branches')selectEntity('us-federal-government',{view:'structure'});
  if(name==='money'){state.flowMode='monetary';selectEntity(byId.has('us-fed')?'us-fed':'us-treasury',{view:'finance'});}
  if(name==='universities'){state.domain='university';selectEntity(byId.has('stanford')?'stanford':'uc-system',{view:'universe'});}
  if(name==='companies'){state.domain='enterprise';selectEntity(byId.has('microsoft')?'microsoft':'alphabet',{view:'universe'});}
  $('workspace').scrollIntoView({behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
}
let outlineTrigger=null;
function openOutline(trigger){outlineTrigger=trigger;$('outline-dialog').showModal();}
document.addEventListener('click',e=>{
  const chart=e.target.closest('[data-universe-chart]');
  if(chart){const n=universeHit(e.clientX,e.clientY,chart.getBoundingClientRect());if(n)selectEntity(n.id);return;}
  const target=e.target.closest('button,[data-cluster],[data-endpoint]' );if(!target)return;
  if(target.dataset.clusterPage!==undefined){openCluster(state.clusterIndex,Number(target.dataset.clusterPage));return;}
  if(target.dataset.directoryPage!==undefined){state.page=Number(target.dataset.directoryPage);renderDirectory();$('entity-list').scrollTop=0;return;}
  if(target.dataset.overviewPage!==undefined){state.overviewPage=Number(target.dataset.overviewPage);renderUniverse();return;}
  if(target.dataset.locate){selectEntity(target.dataset.locate,{view:'map',focusMap:true});$('workspace').scrollIntoView({block:'start'});return;}
  if(target.dataset.entity){selectEntity(target.dataset.entity);return;}
  if(target.dataset.domain){setDomain(target.dataset.domain);return;}
  if(target.dataset.view){setView(target.dataset.view);return;}
  if(target.dataset.profile){state.profile=target.dataset.profile;renderProfile();return;}
  if(target.dataset.profileView){setView(target.dataset.profileView);$('workspace').scrollIntoView({behavior:'smooth',block:'start'});return;}
  if(target.dataset.route){route(target.dataset.route);return;}
  if(target.dataset.cluster!==undefined){if(!state.drag?.moved)openCluster(Number(target.dataset.cluster));return;}
  if(target.hasAttribute('data-close-cluster')){$('map-cluster').hidden=true;return;}
  if(target.dataset.flow){chooseFlow(target.dataset.flow);return;}
  if(target.dataset.endpoint){const id=target.dataset.endpoint;if(byId.has(id))selectEntity(id);else{const f=routeFlows().find(f=>[f.source_id,f.target_id].includes(id));if(f)chooseFlow(f.id);$('announcement').textContent=sectors.get(id)?.description||'';}return;}
  if(target.dataset.event){const event=events.find(v=>v.id===target.dataset.event);state.eventId=event.id;selectEntity(event.entity_ids[0],{focusMap:true,view:'map'});$('workspace').scrollIntoView({behavior:'smooth',block:'start'});return;}
});
document.addEventListener('keydown',e=>{
  if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)&&!$('outline-dialog').open){e.preventDefault();$('search').focus();}
  if((e.key==='Enter'||e.key===' ')&&e.target.matches('[data-cluster],[data-endpoint]')){e.preventDefault();e.target.dispatchEvent(new MouseEvent('click',{bubbles:true}));}
  if(e.key==='Escape'){hideUniverseHover();$('map-cluster').hidden=true;$('map-tooltip').hidden=true;}
});
$('universe-view').addEventListener('pointermove',e=>{
  const chart=e.target.closest('[data-universe-chart]');
  if(!chart){hideUniverseHover();return;}
  const n=universeHit(e.clientX,e.clientY,chart.getBoundingClientRect());chart.style.cursor=n?'pointer':'default';
  if(!n){hideUniverseHover();return;}
  const label=$('universe-hover');label.textContent=shortName(n)+(n.institution_type?' · '+n.institution_type:'');
  label.style.left=Math.max(8,Math.min(e.clientX+12,window.innerWidth-292))+'px';
  label.style.top=Math.max(8,Math.min(e.clientY+16,window.innerHeight-80))+'px';label.hidden=false;
});
$('universe-view').addEventListener('pointerleave',hideUniverseHover);
$('search').addEventListener('input',e=>{state.query=e.target.value.trim().toLowerCase();state.page=0;state.overviewPage=0;$('map-cluster').hidden=true;renderDirectory();if(state.view==='map')renderMap();if(state.view==='universe')renderUniverse();});
$('search').addEventListener('keydown',e=>{if(e.key==='Enter'){const first=visibleNodes()[0];if(first)selectEntity(first.id);}if(e.key==='Escape'){state.query='';state.page=0;state.overviewPage=0;e.target.value='';renderDirectory();if(state.view==='map')renderMap();if(state.view==='universe')renderUniverse();}});
$('btn-plus').addEventListener('click',()=>zoom(1.35));$('btn-minus').addEventListener('click',()=>zoom(1/1.35));
$('btn-fit').addEventListener('click',()=>{state.camera={k:.9,x:45,y:30};$('map-cluster').hidden=true;renderMap();});
$('btn-reset').addEventListener('click',()=>{state.query='';$('search').value='';state.domain='all';state.subset='all';state.page=0;state.overviewPage=0;state.camera={k:.9,x:45,y:30};$('events-selected').checked=false;$('map-cluster').hidden=true;if(state.view==='structure')state.selected='us-federal-government';if(state.view==='finance'){state.flowMode='monetary';state.flowId=null;}syncHash();render();});
for(const id of ['show-relations','show-events','show-funding'])$(id).addEventListener('change',renderMap);
for(const id of ['event-period','events-selected'])$(id).addEventListener('change',()=>{renderEvents();if(state.view==='map')renderMap();});
document.addEventListener('change',e=>{if(e.target.id==='catalog-filter'){state.subset=e.target.value;state.page=0;state.overviewPage=0;syncHash();render();}if(e.target.id==='flow-mode'){state.flowMode=e.target.value;renderFinance();}if(e.target.id==='flow-selection')chooseFlow(e.target.value);});
for(const id of ['btn-outline','btn-about','btn-method'])$(id).addEventListener('click',e=>openOutline(e.currentTarget));
$('btn-mobile-profile').addEventListener('click',()=>document.querySelector('.inspector').scrollIntoView({block:'start',behavior:'smooth'}));
$('btn-close-outline').addEventListener('click',()=>$('outline-dialog').close());
$('outline-dialog').addEventListener('close',()=>outlineTrigger?.focus());
$('outline-dialog').addEventListener('click',e=>{if(e.target===$('outline-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
$('btn-export').addEventListener('click',()=>{const blob=new Blob([JSON.stringify(DATA,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`organization-world-model-${latestReview}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);$('announcement').textContent='完整模型 JSON 已导出';});
const map=$('us-map');
map.addEventListener('wheel',e=>{e.preventDefault();zoom(e.deltaY<0?1.12:1/1.12,pointInSvg(e));},{passive:false});
map.addEventListener('pointerdown',e=>{if(e.button!==0)return;const p=pointInSvg(e);state.drag={x:p.x,y:p.y,cx:state.camera.x,cy:state.camera.y,moved:false,pointer:e.pointerId};});
map.addEventListener('pointermove',e=>{
  const p=pointInSvg(e);
  if(state.drag&&e.buttons===1){const dx=p.x-state.drag.x,dy=p.y-state.drag.y;if(Math.hypot(dx,dy)>4){state.drag.moved=true;map.setPointerCapture(e.pointerId);state.camera.x=state.drag.cx+dx;state.camera.y=state.drag.cy+dy;const c=state.camera;$('map-camera').setAttribute('transform',`translate(${c.x} ${c.y}) scale(${c.k})`);$('map-tooltip').hidden=true;$('map-cluster').hidden=true;}return;}
  const pin=e.target.closest('[data-cluster]');
  if(pin){const g=state.groups[Number(pin.dataset.cluster)],r=$('map-view').getBoundingClientRect();$('map-tooltip').innerHTML=`${esc(g.nodes[0].location.city)} · ${g.nodes.length} 个组织<br>${esc(g.nodes.slice(0,3).map(shortName).join(' / '))}${g.nodes.length>3?' …':''}`;$('map-tooltip').style.left=Math.max(8,Math.min(e.clientX-r.left+15,r.width-265))+'px';$('map-tooltip').style.top=Math.max(8,e.clientY-r.top-60)+'px';$('map-tooltip').hidden=false;}else $('map-tooltip').hidden=true;
});
map.addEventListener('pointerup',e=>{if(map.hasPointerCapture(e.pointerId))map.releasePointerCapture(e.pointerId);setTimeout(()=>{state.drag=null;},0);});
map.addEventListener('pointercancel',()=>{state.drag=null;});
map.addEventListener('pointerleave',()=>{$('map-tooltip').hidden=true;});
map.addEventListener('dblclick',e=>{if(!e.target.closest('[data-cluster]'))zoom(1.6,pointInSvg(e));});
window.addEventListener('popstate',()=>{readHash();render();});
window.addEventListener('hashchange',()=>{readHash();render();});
$('snapshot-date').textContent=`数据快照 ${latestReview}`;
$('stats').innerHTML=[[number(nodes.length),'组织记录'],[number(nodes.filter(n=>n.location).length),'地图定位'],[flows.length,'资金机制'],[events.length,'事件记录']].map(([n,label])=>`<div class="stat"><strong>${n}</strong><span>${label}</span></div>`).join('');
$('model-boundary').textContent=`已收录 ${nodes.length} 个组织、${edges.length} 条正式结构关系、${flows.length} 条金融机制与 ${events.length} 条事件。包含 ${nodes.filter(n=>n.governance).length} 份治理说明与 ${nodes.filter(n=>n.location).length} 个地图位置。采用官方完整名录与研究档案两层数据；各目录的覆盖口径、历史条目与排除项见首页。收录组织不等于已查明全部隶属、治理或金融交易。`;
readHash();renderMapBase();renderCoverage();render();
