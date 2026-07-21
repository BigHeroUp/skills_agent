(() => {
  "use strict";
  const state = {data:null, scale:1, selected:null, activeTab:"experience"};
  const $ = (id) => document.getElementById(id);
  const svgNS = "http://www.w3.org/2000/svg";
  const colors = ["#5ce8ff","#2679ff","#59f5bd","#ffc86b","#d178ff","#ff647c","#37a6ff","#75e2b8","#ff9f71"];
  const colorFor = (type) => colors[Math.abs([...String(type)].reduce((n,c)=>n+c.charCodeAt(0),0))%colors.length];
  const el = (tag, cls, text) => {const node=document.createElement(tag);if(cls)node.className=cls;if(text!==undefined)node.textContent=String(text);return node;};
  const pretty = (value) => value===null||value===undefined||value==="" ? "—" : typeof value==="object" ? JSON.stringify(value) : String(value);
  const shortDate = (value) => value ? new Intl.DateTimeFormat("it-IT",{dateStyle:"short",timeStyle:"short"}).format(new Date(value)) : "—";
  function toast(message){$("toast").textContent=message;$("toast").classList.add("show");setTimeout(()=>$("toast").classList.remove("show"),2200)}

  async function loadData(){
    $("system-label").textContent="SINCRONIZZAZIONE";
    const params=new URLSearchParams();
    const q=$("search").value.trim(), type=$("type-filter").value;
    if(q)params.set("q",q);if(type)params.set("type",type);
    const response=await fetch(`/portal/api/knowledge?${params}`,{headers:{Accept:"application/json"}});
    if(response.status===401){location.href="/portal";return}
    if(!response.ok)throw new Error((await response.json()).error||"Errore di caricamento");
    state.data=await response.json();state.selected=null;
    renderAll();$("system-label").textContent="SISTEMA OPERATIVO";
  }

  function renderAll(){
    const d=state.data,s=d.summary,q=d.quality;
    $("metric-nodes").textContent=s.nodes;$("metric-edges").textContent=s.edges;$("metric-types").textContent=s.node_types;
    $("metric-experiences").textContent=s.experiences;$("metric-analyses").textContent=s.analyses;
    $("metric-quality").textContent=q.can_consume ? "VALID" : d.source.exists ? "REVIEW" : "EMPTY";
    $("metric-quality").style.color=q.can_consume?"var(--green)":"var(--amber)";
    $("updated-at").textContent=shortDate(d.source.updated_at);$("schema-version").textContent=`SCHEMA V${d.source.schema_version}`;
    renderFilters();renderRelationships();renderGraph();renderIntelligence();renderTimeline();
  }

  function renderFilters(){
    const select=$("type-filter"), current=select.value;
    if(select.options.length===1){Object.keys(state.data.node_types).forEach(type=>{const o=el("option",null,`${type} (${state.data.node_types[type]})`);o.value=type;select.append(o)})}
    const legend=$("legend");legend.replaceChildren();
    Object.entries(state.data.node_types).slice(0,12).forEach(([type,count])=>{
      const button=el("button");const dot=el("i");dot.style.color=colorFor(type);dot.style.background=colorFor(type);button.append(dot,document.createTextNode(`${type} · ${count}`));
      button.addEventListener("click",()=>{select.value=type;loadData().catch(showError)});legend.append(button);
    });
    if(current)select.value=current;
  }

  function renderRelationships(){
    const box=$("relationships");box.replaceChildren();const entries=Object.entries(state.data.relationships).sort((a,b)=>b[1]-a[1]).slice(0,6);const max=Math.max(1,...entries.map(x=>x[1]));
    entries.forEach(([name,count])=>{const row=el("div","bar"),label=el("label");label.append(el("span",null,name),el("span",null,count));const bar=el("i");bar.style.width=`${Math.max(8,count/max*100)}%`;row.append(label,bar);box.append(row)});
  }

  function renderGraph(){
    const svg=$("knowledge-graph");svg.replaceChildren();const nodes=state.data.nodes,edges=state.data.edges;
    $("visible-count").textContent=`${nodes.length} nodi visibili`;$("empty-state").hidden=nodes.length>0;svg.hidden=nodes.length===0;
    if(!nodes.length)return;
    const root=document.createElementNS(svgNS,"g");root.id="graph-root";svg.append(root);
    const positions=new Map(), groups={};nodes.forEach(n=>(groups[n.type]??=[]).push(n));
    const types=Object.keys(groups);let index=0;
    types.forEach((type,typeIndex)=>groups[type].forEach((node,localIndex)=>{
      const global=index++, ring=1+Math.floor(global/38), angle=(localIndex/groups[type].length)*Math.PI*2+(typeIndex/types.length)*Math.PI*2;
      const sector=typeIndex/types.length*Math.PI*2, spread=(localIndex-(groups[type].length-1)/2)*Math.min(.28,Math.PI*1.7/Math.max(1,groups[type].length));
      const radius=Math.min(255,95+ring*55+(typeIndex%2)*24);positions.set(node.id,{x:450+Math.cos(sector+spread)*radius,y:300+Math.sin(sector+spread)*radius});
    }));
    edges.forEach(edge=>{const a=positions.get(edge.source),b=positions.get(edge.target);if(!a||!b)return;const line=document.createElementNS(svgNS,"line");line.setAttribute("class","edge");line.setAttribute("x1",a.x);line.setAttribute("y1",a.y);line.setAttribute("x2",b.x);line.setAttribute("y2",b.y);line.dataset.relationship=edge.relationship;root.append(line)});
    nodes.forEach(node=>{const p=positions.get(node.id),group=document.createElementNS(svgNS,"g");group.setAttribute("class","node");group.setAttribute("transform",`translate(${p.x} ${p.y})`);group.dataset.id=node.id;
      const circle=document.createElementNS(svgNS,"circle"),size=Math.max(5,Math.min(15,6+(state.data.edges.filter(e=>e.source===node.id||e.target===node.id).length*.8)));circle.setAttribute("r",size);circle.setAttribute("fill",colorFor(node.type)+"55");circle.setAttribute("stroke",colorFor(node.type));
      const title=document.createElementNS(svgNS,"title");title.textContent=`${node.label} · ${node.type}`;circle.append(title);group.append(circle);
      if(nodes.length<90){const label=document.createElementNS(svgNS,"text");label.setAttribute("x",size+5);label.setAttribute("y","3");label.textContent=node.label.slice(0,24);group.append(label)}
      group.addEventListener("click",()=>inspectNode(node.id,group));root.append(group)});
    applyZoom();
  }

  function applyZoom(){const root=$("graph-root");if(root)root.setAttribute("transform",`translate(${450*(1-state.scale)} ${310*(1-state.scale)}) scale(${state.scale})`)}
  async function inspectNode(id,group){
    document.querySelectorAll(".node.selected").forEach(n=>n.classList.remove("selected"));group.classList.add("selected");
    const response=await fetch(`/portal/api/knowledge/nodes/${encodeURIComponent(id)}`);if(!response.ok){toast("Nodo non disponibile");return}const d=await response.json();state.selected=id;
    $("node-placeholder").hidden=true;$("node-detail").hidden=false;$("node-type").textContent=d.node.type;$("node-label").textContent=d.node.label;$("node-id").textContent=d.node.id;
    const props=$("node-properties");props.replaceChildren();Object.entries(d.node.properties||{}).forEach(([k,v])=>{props.append(el("dt",null,k),el("dd",null,pretty(v))) });if(!props.children.length)props.append(el("dd",null,"Nessuna proprietà"));
    const neighbors=$("node-neighbors");neighbors.replaceChildren();d.neighbors.slice(0,30).forEach(item=>{const box=el("div","neighbor"),node=item.node||{};box.append(el("b",null,node.label||node.id),el("small",null,`${item.direction||""} · ${(item.edge||{}).relationship||"relazione"}`));neighbors.append(box)});if(!neighbors.children.length)neighbors.append(el("p",null,"Nessuna connessione visibile"));
  }

  function cards(items, empty){const box=document.createDocumentFragment();if(!items.length)box.append(el("p",null,empty));items.forEach(item=>{const card=el("div","intel-card");card.append(el("b",null,item.title||item.step||item.label||item.status||"Evidenza"),el("span",null,item.description||item.reason||item.summary||item.selected?.title||pretty(item)));box.append(card)});return box}
  function renderIntelligence(){
    const box=$("intelligence-content");box.replaceChildren();const d=state.data,intel=d.intelligence||{};
    if(state.activeTab==="experience")box.append(cards(d.experiences,"Nessuna Experience ancora consolidata."));
    else if(state.activeTab==="recommendation"){const r=intel.recommendation||intel.recommendations||{};const items=Array.isArray(r)?r:(r.recommendations||r.recommended_steps||[]);box.append(cards(items,"Nessuna raccomandazione nell’ultima analisi."))}
    else if(state.activeTab==="decision"){const decision=intel.decision||{};const items=[];if(decision.selected)items.push({title:decision.selected.title||decision.selected.label||"Opzione selezionata",description:decision.selected.rationale||decision.rationale||pretty(decision.selected)});else if(Object.keys(decision).length)items.push({title:`Stato: ${decision.status||"computed"}`,description:pretty(decision)});box.append(cards(items,"Nessuna decisione arbitrata nell’ultima analisi."))}
    else {const q=d.quality;const issues=(q.issues||[]).slice(0,20).map(x=>({title:x.code||x.severity||"Issue",description:x.message||pretty(x)}));box.append(cards(issues,q.can_consume?"Grafo consumabile: nessun problema bloccante.":"Il grafo non è ancora disponibile o richiede revisione."))}
  }

  function renderTimeline(){const box=$("timeline");box.replaceChildren();state.data.analyses.forEach(item=>{const row=el("div","timeline-item");row.append(el("b",null,item.description),el("small",null,shortDate(item.created_at)),el("span",null,`${item.status.toUpperCase()} · ${item.progress}% · ${item.id.slice(0,8)}`));box.append(row)});if(!box.children.length)box.append(el("p",null,"Nessuna analisi eseguita."))}

  async function runQuery(question){
    const output=$("query-result");output.replaceChildren(el("span",null,"PROCESSING"),el("p",null,"Ricerca delle evidenze in corso…"));
    const response=await fetch("/portal/api/knowledge/query",{method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":document.querySelector('meta[name="csrf-token"]').content},body:JSON.stringify({question})});
    const result=await response.json();if(!response.ok)throw new Error(result.error||"Query non riuscita");output.replaceChildren(el("span",null,`CONFIDENCE ${Math.round((result.confidence||0)*100)}% · ${result.execution_type||"QUERY"}`),el("p",null,result.answer||"Nessuna risposta"));
    (result.matches||[]).slice(0,5).forEach(match=>output.append(el("p",null,`↳ ${match.label||match.id}`)));
  }
  function showError(error){$("system-label").textContent="ERRORE SISTEMA";toast(error.message||String(error))}
  $("search-button").addEventListener("click",()=>loadData().catch(showError));$("search").addEventListener("keydown",e=>{if(e.key==="Enter")loadData().catch(showError)});$("type-filter").addEventListener("change",()=>loadData().catch(showError));
  $("reset-view").addEventListener("click",()=>{$("search").value="";$("type-filter").value="";state.scale=1;loadData().catch(showError)});$("zoom-in").addEventListener("click",()=>{state.scale=Math.min(2,state.scale+.15);applyZoom()});$("zoom-out").addEventListener("click",()=>{state.scale=Math.max(.5,state.scale-.15);applyZoom()});
  $("knowledge-graph").addEventListener("wheel",e=>{e.preventDefault();state.scale=Math.max(.5,Math.min(2,state.scale+(e.deltaY<0?.08:-.08)));applyZoom()},{passive:false});
  $("query-form").addEventListener("submit",e=>{e.preventDefault();runQuery($("question").value.trim()).catch(showError)});document.querySelectorAll(".suggestions button").forEach(b=>b.addEventListener("click",()=>{$("question").value=b.textContent;runQuery(b.textContent).catch(showError)}));
  document.querySelectorAll(".tabbar button").forEach(b=>b.addEventListener("click",()=>{document.querySelectorAll(".tabbar button").forEach(x=>x.classList.remove("active"));b.classList.add("active");state.activeTab=b.dataset.tab;renderIntelligence()}));
  loadData().catch(showError);
})();
