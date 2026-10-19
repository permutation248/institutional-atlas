(()=>{
'use strict';
const data=ATLAS_DATA;
const all=data.entities;
const byId=new Map(all.map(x=>[x.id,x]));
const byParent=new Map();
for(const e of data.edges){
 if(!byParent.has(e.parent_id))byParent.set(e.parent_id,[]);
 byParent.get(e.parent_id).push(e);
}
const domains=[['government','🏛️','政府组织','us-federal-government'],['finance','🏦','金融机构','bofa-corp'],['enterprise','🏢','企业集团','alphabet'],['university','🎓','大学体系','uc-system']];
const typeName={PART_OF:'内部组成', REPORTS_TO:'向其负责', CONTROLLED_BY:'受其控制', FUNCTION_DELEGATED_BY:'获其职能授权', FINANCIALLY_DEPENDENT_ON:'依赖其持续资金'};
const leaderStatus={confirmed:'正式任职',serving:'官网列示现任',unknown:'任职状态待核验',acting:'代理',performing_duties:'履行职责',vacant:'职位空缺'};
const nodeType={government_system:'联邦政府体系',government_branch:'政府分支',legislative_body:'立法机关',court:'法院',executive_department:'行政部门',executive_agency:'行政机关',independent_agency:'独立联邦机构',university_system:'大学系统',university_campus:'大学校区',enterprise_group:'企业集团',company_subsidiary:'子公司',financial_group:'金融控股集团',regulated_bank:'银行'};
const state={domain:'government',focus:'us-federal-government',zoom:1};
const $=s=>document.querySelector(s);
const svgns='http://www.w3.org/2000/svg';
const svgEl=(tag,attrs={},text)=>{const el=document.createElementNS(svgns,tag);for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);if(text!==undefined)el.textContent=text;return el};
function elt(tag,txt,cls){const el=document.createElement(tag);if(txt!==undefined)el.textContent=txt;if(cls)el.className=cls;return el}
function link(url,txt,cls){const a=elt('a',txt,cls);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a}
function safeLabel(x,n){return x.length>n?x.slice(0,n-1)+'…':x}
function searchRank(n,q){const values=[n.id,n.name,n.name_zh,...(n.aliases||[])].map(v=>v.toLowerCase());return values.includes(q)?3:values.some(v=>v.startsWith(q))?2:1;}
function chooseDomain(d){const row=domains.find(x=>x[0]===d);choose(row[3]);}
function choose(id){if(!byId.has(id))return;state.focus=id;state.domain=byId.get(id).domain;state.zoom=1;history.replaceState(null,'','#'+encodeURIComponent(id));render()}
function childEdges(id){return byParent.get(id)||[]}
function countDirect(id){return new Set(childEdges(id).map(e=>e.child_id)).size}
function ancestry(id){let chain=[id],cur=id;for(let k=0;k<9;k++){let n=byId.get(cur);if(!n)break;let p=(n.parents||[]).find(x=>x.type==='PART_OF'||x.type==='CONTROLLED_BY'||x.type==='REPORTS_TO');if(!p||!byId.has(p.parent_id))break;chain.unshift(p.parent_id);cur=p.parent_id;}return chain}
function renderNav(){const nav=$('#domain-nav');nav.replaceChildren();for(const [key,ico,label] of domains){const b=elt('button',undefined,'domain'+(state.domain===key?' active':''));b.type='button';b.setAttribute('aria-pressed',String(state.domain===key));b.append(elt('span',ico));b.append(elt('span',label));const count=all.filter(e=>e.domain===key).length;b.append(elt('small',String(count)));b.onclick=()=>chooseDomain(key);nav.append(b)}
 const roots=$('#root-nav');roots.replaceChildren();for(const n of all.filter(n=>n.domain===state.domain&&!n.parents.length)){const b=elt('button',n.name_zh);b.type='button';b.onclick=()=>choose(n.id);roots.append(b)}
}
function renderGraph(){const selected=byId.get(state.focus);const grouped=new Map();for(const e of childEdges(selected.id)){if(!grouped.has(e.child_id))grouped.set(e.child_id,{...e,node:byId.get(e.child_id),relations:[]});grouped.get(e.child_id).relations.push(e)}const children=[...grouped.values()].filter(e=>e.node);
 children.sort((a,b)=>a.node.name.localeCompare(b.node.name));
 const cols=Math.max(1,Math.min(5,children.length));const rows=Math.max(1,Math.ceil(children.length/cols));
 const W=Math.max(920,cols*210+90),H=Math.max(530,rows*144+260),parentX=W/2,parentY=53;
 const g=$('#graph');g.setAttribute('viewBox',`0 0 ${W} ${H}`);g.style.width=`${Math.round(W*state.zoom)}px`;g.style.height=`${Math.round(H*state.zoom)}px`;g.replaceChildren();
 g.append(svgEl('text',{x:25,y:26,class:'node-sub'},'CURRENT FOCUS'));
 const cardW=180,cardH=95;
 function card(n,x,y,current){const grp=svgEl('g',{class:'node-card'+(current?' current':''),role:'button',tabindex:'0','aria-label':`查看 ${n.name_zh}`,transform:`translate(${x},${y})`});
  grp.append(svgEl('rect',{width:cardW,height:cardH,rx:12,ry:12}));
  grp.append(svgEl('text',{x:14,y:23,class:'node-kicker'},current?'当前机构':(nodeType[n.category]||'组织')));
  grp.append(svgEl('text',{x:14,y:46,class:'node-title'},safeLabel(n.name_zh,11)));
  grp.append(svgEl('text',{x:14,y:65,class:'node-sub'},safeLabel(n.name,24)));
  grp.append(svgEl('text',{x:14,y:83,class:'child-n'},countDirect(n.id)>0?`关联 ${countDirect(n.id)} · 点击展开`:'查看档案 · 暂无子节点'));
  grp.addEventListener('click',()=>choose(n.id));grp.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose(n.id)}});
  grp.append(svgEl('title',{},n.name));g.append(grp);
 }
 const at=[];
 children.forEach((e,i)=>{const row=Math.floor(i/cols),col=i%cols,x=W/2+(col-(cols-1)/2)*204-cardW/2,y=230+row*144;at.push([e,x,y]);});
 for(const [e,x,y] of at){const cx=x+cardW/2;const path=svgEl('path',{class:'edge-path',d:`M${parentX} ${parentY+cardH} V190 H${x-12} V${y+cardH/2} H${x}`});path.append(svgEl('title',{},e.relations.map(r=>`${e.node.name_zh} ${typeName[r.type]} ${selected.name_zh}\n${r.evidence_url}`).join('\n')));g.append(path);g.append(svgEl('text',{x:cx,y:y-10,'text-anchor':'middle',class:'edge-label'},e.relations.map(r=>typeName[r.type]).join(' / ')));}
 card(selected,parentX-cardW/2,parentY,true);
 for(const [e,x,y] of at)card(e.node,x,y,false);
 if(children.length===0)g.append(svgEl('text',{x:W/2,y:244,'text-anchor':'middle',class:'empty-map'},'当前尚未收录直接组成或依赖节点。'));
 const chain=ancestry(selected.id);const crumbs=$('#breadcrumb');crumbs.replaceChildren();chain.forEach((id,i)=>{if(i)crumbs.append(elt('span',' / '));const b=elt('button',byId.get(id).name_zh);b.type='button';b.onclick=()=>choose(id);crumbs.append(b)});
 $('#map-title').textContent=`${selected.name_zh} · 组成与依赖结构`;
 $('#graph-summary').textContent=`已收录 ${data.metadata.total_entities} 个节点 / ${data.metadata.total_edges} 条关系 · 当前 ${children.length} 个关联机构`;$('#zoom-label').textContent=`${Math.round(state.zoom*100)}%`;
 $('#btn-up').disabled=chain.length<=1;
 const canvas=$('#canvas');canvas.scrollLeft=Math.max(0,(g.clientWidth-canvas.clientWidth)/2);canvas.scrollTop=0;
 }
 function renderInspector(){const n=byId.get(state.focus),node=$('#inspector-content');node.replaceChildren();
 node.append(elt('span',nodeType[n.category]||n.category,'tag'));
 node.append(elt('div',n.name_zh,'name'));node.append(elt('div',n.name,'eng'));
 const status=elt('div',n.research_reviewed_at?`本轮官方来源复核：${n.research_reviewed_at} · 部分字段仍可缺失`:`原始包研究快照：${n.verified_at} · 本轮未逐字段重核`,'status');node.append(status);
 node.append(link(n.official_url,`↗ 访问官网${n.website_type==='official'?'':'（门户/共享站点）'}`,'link-button'));
 node.append(elt('h3','职责与功能'));node.append(elt('p',n.function||'待核验'));
 node.append(elt('h3','最高负责人 / 决策岗位'));
 if(n.leader){const b=elt('div',undefined,'info-block');b.append(elt('b',n.leader.name||'未指定履职人'));b.append(elt('div',n.leader.title));b.append(elt('div',`${leaderStatus[n.leader.status]||n.leader.status||'状态待核验'} · 记录日期 ${n.leader.as_of||'未知'}`));if(n.leader.formal_position)b.append(elt('div',n.leader.formal_position));b.append(link(n.leader.evidence_url,'职务来源 ↗'));node.append(b)}else node.append(elt('div','待核验，或不存在单一最高负责人。','empty'));
 node.append(elt('h3','人员规模'));
 if(n.employee_count?.value!=null){const b=elt('div',undefined,'info-block');b.append(elt('b',`${n.employee_count.approximate?'约 ':''}${n.employee_count.value.toLocaleString('en-US')} ${n.employee_count.unit==='faculty_and_staff'?'教职员工':n.employee_count.unit||'人员'}`));b.append(elt('div',n.employee_count.period||''));b.append(link(n.employee_count.evidence_url,'统计依据 ↗'));node.append(b)}else node.append(elt('div','未核验：不以零代替未知。','empty'));
 node.append(elt('h3','上级 / 控制 / 强依赖关系'));
 if(n.parents?.length){const ul=elt('ul',undefined,'mini-list');for(const p of n.parents){const li=elt('li');li.append(elt('span',(typeName[p.type]||p.type)+' → '));const b=elt('button',byId.get(p.parent_id)?.name_zh||p.parent_id);b.style.cssText='border:0;padding:0;background:transparent;color:#2563eb;cursor:pointer;font-size:12px;';b.onclick=()=>choose(p.parent_id);li.append(b);li.append(elt('span',' · '));li.append(link(p.evidence_url,'关系证据 ↗'));ul.append(li)}node.append(ul)}else node.append(elt('div','当前领域入口，没有已建模的上级关系。','empty'));
 node.append(elt('h3','资金与财务信息'));
 if(n.financial_profile?.length){const ul=elt('ul',undefined,'mini-list');for(const f of n.financial_profile){const li=elt('li',`${f.metric} · ${f.value==null?'未知':f.value.toLocaleString('en-US')} ${f.currency||''}`);li.append(elt('div',`${f.fiscal_year||f.reporting_period||''} · ${f.scope||f.reporting_scope||''}`));if(f.source_url)li.append(link(f.source_url,'财务口径与依据 ↗'));ul.append(li)}node.append(ul)}else node.append(elt('div','本版尚未导入可核验的资金数值；不推定为没有资金活动。','empty'));
 node.append(elt('h3','内部组织结构'));const children=[...new Set(childEdges(n.id).map(e=>e.child_id))];node.append(elt('p',children.length?`已收录 ${children.length} 个直接组成或依赖机构，点击中央节点继续下钻；不代表内部名录已完整。`:'尚未录入可核验的下一级机构。'));
 if(n.research_notes){node.append(elt('h3','本轮研究说明'));node.append(elt('p',Array.isArray(n.research_notes)?n.research_notes.join('；'):n.research_notes));}
 node.append(elt('h3','公开发布渠道'));
 if(n.publications?.length){const ul=elt('ul',undefined,'mini-list');for(const p of n.publications){const li=elt('li');li.append(link(p.url,p.label+' ↗'));ul.append(li)}node.append(ul)}else node.append(elt('div','待核验官方公告和信息发布入口。','empty'));
 node.append(elt('h3','事实与关系证据'));
 const ul=elt('ul',undefined,'mini-list');for(const s of n.sources||[]){const li=elt('li');li.append(link(s.url,s.description+' ↗'));ul.append(li)}node.append(ul);
 const a=elt('p',`源文件：${n.__file__}`);a.style.cssText='font-size:11px;color:#98a6ba;margin-top:17px;word-break:break-all';node.append(a);
 }
 function render(){renderNav();renderGraph();renderInspector()}
 $('#snapshot-date').textContent=data.metadata.snapshot_date;
 const coverage=$('#coverage-bar');for(const [label,value] of [['组织',all.length],['强关系',data.edges.length],['本轮复核档案',all.filter(n=>n.research_reviewed_at).length],['含领导记录',all.filter(n=>n.leader).length]]){const stat=elt('span');stat.append(elt('b',String(value)));stat.append(document.createTextNode(' '+label));coverage.append(stat)}
 coverage.append(elt('small','来源链接不等于所有字段均已验证；空值表示未知。'));
 $('#btn-export').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json;charset=utf-8'}));const a=elt('a');a.href=url;a.download=`institutional-atlas-${data.metadata.snapshot_date}.json`;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)});
 $('#btn-up').addEventListener('click',()=>{const chain=ancestry(state.focus);if(chain.length>=2)choose(chain[chain.length-2])});
 $('#btn-reset').addEventListener('click',()=>chooseDomain(state.domain));
 $('#btn-plus').addEventListener('click',()=>{state.zoom=Math.min(1.8,Math.round((state.zoom+.15)*100)/100);renderGraph()});
 $('#btn-minus').addEventListener('click',()=>{state.zoom=Math.max(.65,Math.round((state.zoom-.15)*100)/100);renderGraph()});
 let search=$('#search'),results=$('#search-results');
 search.addEventListener('input',()=>{const q=search.value.trim().toLowerCase();results.replaceChildren();if(!q){results.hidden=true;return}const matched=all.filter(x=>(x.name+x.name_zh+x.id+(x.aliases||[]).join(" ")).toLowerCase().includes(q)).sort((a,b)=>searchRank(b,q)-searchRank(a,q)).slice(0,12);for(const n of matched){const b=elt('button',n.name_zh,'search-result');b.type='button';b.append(elt('small',n.name));b.onclick=()=>{choose(n.id);search.value='';results.hidden=true};results.append(b)}if(!matched.length)results.append(elt('div','暂无匹配条目','search-result'));results.hidden=false});
 document.addEventListener('click',e=>{if(!e.target.closest('.searchwrap'))results.hidden=true});
 search.addEventListener('keydown',e=>{if(e.key==='Escape'){results.hidden=true;search.value=''}if(e.key==='Enter'){const first=results.querySelector('button');if(first&&!results.hidden){e.preventDefault();first.click()}}});
 window.addEventListener('hashchange',()=>{try{const id=decodeURIComponent(location.hash.slice(1));if(byId.has(id))choose(id)}catch{}});
 try{const id=decodeURIComponent(location.hash.slice(1));if(byId.has(id)){state.focus=id;state.domain=byId.get(id).domain}}catch{}
 render();
})();
