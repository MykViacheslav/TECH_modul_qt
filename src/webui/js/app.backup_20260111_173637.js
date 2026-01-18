(() => {
  const $ = (id) => document.getElementById(id);
  const on = (id, evt, fn) => { const el = $(id); if (el) el.addEventListener(evt, fn); };
  const esc = (s) => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clamp = (v,a,b)=>Math.max(a,Math.min(b,v));
  const num = (v,def=0)=>{ const n=Number(v); return Number.isFinite(n)?n:def; };
  const nowISO = ()=> new Date().toISOString();

  // ---- Storage keys
  const KEY_TEMPL = "tech_modul_templates_v10";
  const KEY_GROUP = "tech_modul_groups_v1";
  const KEY_LEFTW = "tech_modul_left_width_v4";
  const KEY_SIDEW = "tech_modul_side_width_v4";

  // ---- Drag tip
  const dragTip = {
    el: $("dragTip"),
    title: $("dragTipTitle"),
    input: $("dragTipInput"),
    close: $("dragTipClose"),
    active: null, // { label, get, set }
    showAt(clientX, clientY){
      const pad = 14;
      dragTip.el.style.left = (clientX + pad) + "px";
      dragTip.el.style.top  = (clientY + pad) + "px";
      dragTip.el.style.display = "block";
    },
    hide(){
      dragTip.el.style.display = "none";
      dragTip.active = null;
    },
    bindActive(active, clientX, clientY){
      dragTip.active = active;
      dragTip.title.textContent = active.label;
      dragTip.input.value = String(active.get());
      dragTip.showAt(clientX, clientY);
      dragTip.input.focus({preventScroll:true});
      dragTip.input.select();
    },
    syncValue(){
      if (!dragTip.active) return;
      dragTip.input.value = String(dragTip.active.get());
    },
    commit(){
      if (!dragTip.active) return;
      const v = Math.round(num(dragTip.input.value, dragTip.active.get()));
      dragTip.active.set(v);
      dragTip.syncValue();
    }
  };

  dragTip.close.onclick = ()=> dragTip.hide();
  dragTip.input.addEventListener("keydown",(e)=>{
    if (e.key==="Enter"){
      dragTip.commit();
      dragTip.hide();
    }
    if (e.key==="Escape"){
      dragTip.hide();
    }
  });
  window.addEventListener("pointerdown",(e)=>{
    if (dragTip.el.style.display==="block"){
      const inside = dragTip.el.contains(e.target);
      if (!inside) dragTip.hide();
    }
  }, {capture:true});

  const materials = [
    { id:"pb18",  name:"Płyta 18 mm (PB18)" },
    { id:"pb16",  name:"Płyta 16 mm (PB16)" },
    { id:"mdf18", name:"MDF 18 mm" },
    { id:"hdf3",  name:"HDF 3 mm" },
    { id:"ply6",  name:"Sklejka 6 mm" },
    { id:"wood16",name:"Drewno 16 mm" }
  ];
  const edgeBands = [
    { id:"abs08", name:"ABS 0.8" },
    { id:"abs2",  name:"ABS 2.0" }
  ];
  const matName = (id)=> (materials.find(m=>m.id===id)||materials[0]).name;
  const ebName  = (id)=> (edgeBands.find(e=>e.id===id)||edgeBands[0]).name;
  const defaultGroups = ["Kitchen","RTV","Łazienka","Inne"];

  function loadGroups(){
    try{
      const g = JSON.parse(localStorage.getItem(KEY_GROUP) || "null");
      if (Array.isArray(g) && g.length) return g;
    }catch{}
    localStorage.setItem(KEY_GROUP, JSON.stringify(defaultGroups));
    return [...defaultGroups];
  }
  function loadTemplates(){
    try{
      const t = JSON.parse(localStorage.getItem(KEY_TEMPL) || "[]");
      if (Array.isArray(t)) return t;
    }catch{}
    return [];
  }
  function saveTemplates(list){
    localStorage.setItem(KEY_TEMPL, JSON.stringify(list));
  }
  function uid(prefix="x"){
    return prefix + "_" + Math.random().toString(16).slice(2) + "_" + Date.now().toString(16);
  }

  const state = {
    tab: "module",
    groups: loadGroups(),
    templates: loadTemplates(),
    loadedTemplateId: null,

    model: {
      group: "Kitchen",
      name: "",
      dims: { W:600, H:720, D:560 },
      anchor: { corner:"NONE", dx:0, dy:0 },
      pos: { L:0, R:0, T:0, B:0 },
      sideMode: "full",
      has: { left:true, right:true, top:true, bottom:true, back:true, front:true },
      mid: { enabled:false, x:300, mat:"pb18" },
      shelves: { autoCount:1, autoY:[360], extra:[] },
      back: { enabled:true, mat:"hdf3" },
      front: {
        mode:"none",
        count:0,
        mat:"mdf18",
        gap:2,
        drawerSystem:"Blum|MerivoBox",
        drawerHeights:"",
        cornerFront:false
      },
      hardware: {
        mountType:"legs",
        mountCount:4,
        drawerEstimate:true,
        drawerBottomMat:"pb16",
        drawerBackMat:"pb16",
        drawerWoodMat:"wood16",
        drawerClear:40
      }
    },

    wall: {
      type:"I",
      H:2700,
      // I
      A:4000, th:120,
      // L
      LA:3000, LB:2500, Lth:120,
      // C
      CA:3500, CB:2200, CC:1600, Cth:120,

      island:{ on:false, W:900, D:600, x:1200, y:800 },
      obs: [], // {id,type,name,x,y,W,D}
      selectedObsId:null,
      drag:null,
      view:null
    },

    parts: [],
    selected: null,
    hover: null,
    view: null,
    drag: null
  };

  function defaultEdgesForKind(kind){
    if (kind==="front") return {L:"abs2",R:"abs2",T:"abs2",B:"abs2"};
    return {L:null,R:null,T:null,B:null};
  }
  function mkPart(id,name,kind,mat,dimW,dimH,meta={}){
    return { id,name,kind,mat,dimW,dimH, edges: defaultEdgesForKind(kind), meta };
  }

  function parseHeightsList(s){
    const arr = String(s||"").split(",").map(x=>Number(x.trim())).filter(x=>Number.isFinite(x) && x>0);
    return arr;
  }

  function rebuildParts(){
    const m = state.model;
    const {W,H,D} = m.dims;

    const p = [];
    if (m.has.left)   p.push(mkPart("left","Bok lewy","side","pb18", D, H));
    if (m.has.right)  p.push(mkPart("right","Bok prawy","side","pb18", D, H));
    if (m.has.top)    p.push(mkPart("top","Wieniec górny","top","pb18", W, D));
    if (m.has.bottom) p.push(mkPart("bottom","Wieniec dolny","bottom","pb18", W, D));
    if (m.back.enabled && m.has.back) p.push(mkPart("back","Plecy","back", m.back.mat, W, H));
    if (m.mid.enabled) p.push(mkPart("mid","Pion środkowy","mid", m.mid.mat, D, H));

    m.shelves.autoY.forEach((y, idx)=>{
      p.push(mkPart("s_auto_"+idx, `Półka auto #${idx+1}`, "shelf", "pb18", W, D, { shelfY:y, shelfType:"auto" }));
    });
    m.shelves.extra.forEach((it)=>{
      p.push(mkPart(it.id, `Półka extra`, "shelf", "pb18", W, D, { shelfY:it.y, shelfType:"extra" }));
    });

    if (m.has.front && m.front.mode !== "none" && m.front.count>0){
      const gap = clamp(m.front.gap, 0, 10);
      const count = clamp(m.front.count, 1, 12);

      if (m.front.mode==="doors"){
        const doorCount = count;
        const totalGap = (doorCount+1)*gap;
        const doorW = Math.max(10, Math.floor((W - totalGap)/doorCount));
        const doorH = Math.max(10, H - 2*gap);
        for (let i=0;i<doorCount;i++){
          p.push(mkPart(`front_${i+1}`, `Drzwi #${i+1}`, "front", m.front.mat, doorW, doorH, { frontIndex:i+1, mode:"doors", corner:m.front.cornerFront }));
        }
      }

      if (m.front.mode==="drawers"){
        const drawerCount = count;
        const list = parseHeightsList(m.front.drawerHeights);
        let heights = [];
        if (list.length === drawerCount){
          heights = list;
        } else {
          const totalGap = (drawerCount+1)*gap;
          const avail = Math.max(20, H - totalGap);
          const each = Math.floor(avail/drawerCount);
          heights = Array.from({length:drawerCount}, ()=> each);
        }
        const frontW = Math.max(10, W - 2*gap);
        for (let i=0;i<drawerCount;i++){
          p.push(mkPart(`front_${i+1}`, `Front szuflady #${i+1}`, "front", m.front.mat, frontW, Math.max(10, heights[i]), { frontIndex:i+1, mode:"drawers", corner:m.front.cornerFront }));
        }
      }
    }

    state.parts = p;
    if (!state.selected || !state.parts.some(x=>x.id===state.selected)){
      state.selected = state.parts[0]?.id || null;
    }
  }

  function computeHingesPerDoor(doorH){
    if (doorH <= 900) return 2;
    if (doorH <= 1400) return 3;
    if (doorH <= 2000) return 4;
    return 5;
  }

  function renderBOM(){
    const m = state.model;

    const area = new Map();
    const edge = new Map();
    const addA = (mat, mm2)=> area.set(mat, (area.get(mat)||0) + mm2/1_000_000);
    const addE = (band, mm)=> { if(!band) return; edge.set(band, (edge.get(band)||0) + mm); };

    for (const p of state.parts){
      if (p.dimW>0 && p.dimH>0) addA(p.mat, p.dimW*p.dimH);
      addE(p.edges.L, p.dimH);
      addE(p.edges.R, p.dimH);
      addE(p.edges.T, p.dimW);
      addE(p.edges.B, p.dimW);
    }

    const hw = [];
    if (m.hardware.mountType !== "none" && m.hardware.mountCount>0){
      hw.push({ name: (m.hardware.mountType==="legs" ? "Nóżki" : "Zawieszki"), qty: m.hardware.mountCount });
    }
    if (m.front.mode==="doors" && m.front.count>0){
      const gap = clamp(m.front.gap,0,10);
      const doorH = Math.max(10, m.dims.H - 2*gap);
      const perDoor = computeHingesPerDoor(doorH);
      hw.push({ name: "Zawiasy (est.)", qty: perDoor * m.front.count });
    }
    if (m.front.mode==="drawers" && m.front.count>0){
      hw.push({ name: `Prowadnice / zestawy (${m.front.drawerSystem})`, qty: m.front.count });

      if (m.hardware.drawerEstimate){
        const {W,D} = m.dims;
        const wClear = clamp(m.hardware.drawerClear, 0, 200);
        const innerW = Math.max(50, W - m.pos.L - m.pos.R - wClear);
        const depth = Math.max(100, D - 60);

        addA(m.hardware.drawerBottomMat, innerW * depth * m.front.count);
        addA(m.hardware.drawerBackMat, innerW * 100 * m.front.count);

        if (m.front.drawerSystem.endsWith("TandemBoxWood")){
          addA(m.hardware.drawerWoodMat, (2*depth*100 + 2*innerW*100) * m.front.count);
        }
      }
    }

    const matsHtml = [...area.entries()].map(([id,m2]) =>
      `<div class="box"><div class="muted">${esc(matName(id))}</div><div><b>${m2.toFixed(3)}</b> m²</div></div>`
    ).join("") || `<div class="muted">—</div>`;

    const edgeHtml = [...edge.entries()].map(([id,mm]) =>
      `<div class="box"><div class="muted">${esc(ebName(id))}</div><div><b>${(mm/1000).toFixed(2)}</b> m</div></div>`
    ).join("") || `<div class="muted">—</div>`;

    const hwHtml = hw.length
      ? `<table><thead><tr><th>Furnitura</th><th>Qty</th></tr></thead><tbody>${
          hw.map(x=>`<tr><td>${esc(x.name)}</td><td><b>${x.qty}</b></td></tr>`).join("")
        }</tbody></table>`
      : `<div class="muted">—</div>`;

    $("bomBadge").textContent = `parts: ${state.parts.length}`;
    $("bom").innerHTML = `
      <div class="hr"></div>
      <div style="font-weight:800; margin-bottom:6px;">Materiały</div>
      <div class="kpi">${matsHtml}</div>

      <div class="hr"></div>
      <div style="font-weight:800; margin-bottom:6px;">Okleina</div>
      <div class="kpi">${edgeHtml}</div>

      <div class="hr"></div>
      <div style="font-weight:800; margin-bottom:6px;">Furnitura</div>
      ${hwHtml}
    `;
  }

  function renderPartsList(){
    const wrap = $("parts");
    wrap.innerHTML = "";
    for (const p of state.parts){
      const row = document.createElement("div");
      row.className = "partItem" + (p.id===state.selected ? " selected" : "");
      row.onclick = ()=>{ state.selected = p.id; renderAll(); };
      row.innerHTML = `<div>${esc(p.name)}</div><div class="badge">${esc(matName(p.mat))}</div>`;
      wrap.appendChild(row);
    }
  }

  function selPart(){ return state.parts.find(p=>p.id===state.selected) || null; }

  function renderQuick(){
    const p = selPart();
    $("selBadge").textContent = p ? `Selected: ${p.name}` : "Selected: —";
    $("quickBadge").textContent = p ? p.name : "—";
    if (!p) return;

    $("quickMat").value = p.mat;

    const show = (k)=> p.edges[k] ? ebName(p.edges[k]) : "—";
    const upd = (k)=>{
      $("q"+k+"v").textContent = show(k);
      $("q"+k).classList.toggle("on", !!p.edges[k]);
    };
    upd("L"); upd("R"); upd("T"); upd("B");

    renderEdgeSketch(p);
  }

  function toggleEdge(k){
    const p = selPart(); if (!p) return;
    p.edges[k] = p.edges[k] ? null : $("quickBand").value;
    renderAll();
  }
  function setAllEdges(band){
    const p = selPart(); if (!p) return;
    p.edges = {L:band,R:band,T:band,B:band};
    renderAll();
  }
  function clearEdges(){
    const p = selPart(); if (!p) return;
    p.edges = {L:null,R:null,T:null,B:null};
    renderAll();
  }
  function applyKind(){
    const p = selPart(); if (!p) return;
    for (const x of state.parts){
      if (x.kind === p.kind) x.edges = {...p.edges};
    }
    renderAll();
  }

  function renderEdgeSketch(p){
    const svg = $("edgeSketch");
    svg.innerHTML = "";
    const NS="http://www.w3.org/2000/svg";

    const make = (tag, attrs={})=>{
      const el=document.createElementNS(NS,tag);
      for (const [k,v] of Object.entries(attrs)) el.setAttribute(k,String(v));
      return el;
    };

    const box = make("rect",{x:20,y:20,width:80,height:80,rx:10,ry:10,fill:"#fff",stroke:"#111","stroke-width":2});
    svg.appendChild(box);

    const seg = (id,x1,y1,x2,y2)=>{
      const on = !!p.edges[id];
      const hit = make("line",{
        x1,y1,x2,y2,
        stroke:"#000","stroke-width":18,
        "stroke-opacity":0,
        "pointer-events":"stroke"
      });
      hit.style.cursor="pointer";
      hit.addEventListener("click", ()=>toggleEdge(id));
      svg.appendChild(hit);

      const ln = make("line",{
        x1,y1,x2,y2,
        stroke: on ? "#111" : "#999",
        "stroke-width": on ? 8 : 4,
        "stroke-linecap":"round"
      });
      svg.appendChild(ln);
    };

    // L R T B
    seg("T", 26,20, 94,20);
    seg("B", 26,100, 94,100);
    seg("L", 20,26, 20,94);
    seg("R", 100,26, 100,94);

    const label = (t,x,y)=>{
      const tx = make("text",{x,y,"font-size":12,"text-anchor":"middle","font-weight":800,fill:"#222"});
      tx.textContent=t;
      svg.appendChild(tx);
    };
    label("G",60,14);
    label("D",60,116);
    label("L",10,64);
    label("P",110,64);
  }

  function normalizeShelves(){
    const m = state.model;
    const H = m.dims.H;
    const top = m.pos.T;
    const bot = m.pos.B;
    const innerH = Math.max(50, H - top - bot);
    m.shelves.autoY = m.shelves.autoY.map(y=>clamp(Math.round(num(y,0)), 1, innerH-1)).sort((a,b)=>a-b);
    m.shelves.extra = m.shelves.extra.map(it=>({ ...it, y: clamp(Math.round(num(it.y,0)), 1, innerH-1) })).sort((a,b)=>a.y-b.y);
  }

  function setAutoShelvesEqual(){
    const m = state.model;
    const count = clamp(m.shelves.autoCount, 0, 12);
    const H = m.dims.H;
    const top = m.pos.T;
    const bot = m.pos.B;
    const innerH = Math.max(50, H - top - bot);
    const y = [];
    for (let i=1;i<=count;i++){
      y.push(Math.round((innerH*(i/(count+1)))));
    }
    m.shelves.autoY = y;
    normalizeShelves();
  }

  function renderShelvesUI(){
    const m = state.model;
    const wrap = $("shelfList");
    wrap.innerHTML = "";

    if (m.shelves.autoY.length===0){
      wrap.innerHTML = `<div class="muted">—</div>`;
      return;
    }

    const table = document.createElement("table");
    table.innerHTML = `<thead><tr><th>#</th><th>Y od dołu (mm)</th><th></th></tr></thead>`;
    const tb = document.createElement("tbody");

    m.shelves.autoY.forEach((y, idx)=>{
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${idx+1}</td>
        <td><input data-idx="${idx}" class="shelfYInput" type="number" min="1" value="${y}" style="width:120px;"></td>
        <td class="muted">drag na rysunku</td>
      `;
      tb.appendChild(tr);
    });

    table.appendChild(tb);
    wrap.appendChild(table);

    wrap.querySelectorAll(".shelfYInput").forEach(inp=>{
      inp.addEventListener("input", (e)=>{
        const i = Number(e.target.getAttribute("data-idx"));
        m.shelves.autoY[i] = num(e.target.value, m.shelves.autoY[i]);
        normalizeShelves();
        rebuildParts();
        renderAll();
      });
    });
  }

  function renderExtraShelvesUI(){
    const m = state.model;
    const wrap = $("extraShelfList");
    wrap.innerHTML = "";

    if (m.shelves.extra.length===0){
      wrap.innerHTML = `<div class="muted">—</div>`;
      return;
    }

    m.shelves.extra.forEach(it=>{
      const card = document.createElement("div");
      card.className = "listCard";
      card.innerHTML = `
        <div class="listHeader">
          <div><b>Półka extra</b> <span class="muted">(${it.id})</span></div>
          <button class="miniBtn danger" data-del="${it.id}">Usuń</button>
        </div>
        <div class="row" style="margin-top:8px;">
          <div>
            <label>Y od dołu (mm)</label>
            <input class="extraY" data-id="${it.id}" type="number" min="1" value="${it.y}">
          </div>
          <div class="muted" style="align-self:end;">drag na rysunku</div>
        </div>
      `;
      wrap.appendChild(card);
    });

    wrap.querySelectorAll("button[data-del]").forEach(btn=>{
      btn.onclick = ()=>{
        const id = btn.getAttribute("data-del");
        m.shelves.extra = m.shelves.extra.filter(x=>x.id!==id);
        normalizeShelves();
        rebuildParts();
        renderAll();
        renderExtraShelvesUI();
      };
    });

    wrap.querySelectorAll("input.extraY").forEach(inp=>{
      inp.addEventListener("input", ()=>{
        const id = inp.getAttribute("data-id");
        const it = m.shelves.extra.find(x=>x.id===id);
        if (!it) return;
        it.y = num(inp.value, it.y);
        normalizeShelves();
        rebuildParts();
        renderAll();
      });
    });
  }

  function strokeColor(id){
    if (id===state.selected) return "#d93025";
    if (id===state.hover) return "#1a73e8";
    return "#000";
  }
  function strokeW(id){
    if (id===state.selected) return 4.2;
    if (id===state.hover) return 2.6;
    return 1.3;
  }
  function clientToSvg(svg, e){
    const rect = svg.getBoundingClientRect();
    const vb = svg.viewBox.baseVal;
    const x = (e.clientX - rect.left) * (vb.width / rect.width);
    const y = (e.clientY - rect.top)  * (vb.height / rect.height);
    return {x,y};
  }

  function renderSVG(){
    const svg = $("moduleView");
    svg.innerHTML = "";

    const m = state.model;
    const {W,H,D} = m.dims;
    const vbW=900, vbH=940;
    const padX=80, padY=80, dimRight=120, gapMm=130;
    const availW = vbW - padX*2 - dimRight;
    const availH = vbH - padY*2 - 50;
    const scale = Math.min(availW/W, availH/(H + gapMm + D));

    const frontX=padX, frontY=padY, frontW=W*scale, frontH=H*scale;
    const topX=padX, topY=frontY+frontH+(gapMm*scale), topW=W*scale, topD=D*scale;

    state.view = { scale, frontX, frontY, frontW, frontH, topX, topY, topW, topD };

    const NS="http://www.w3.org/2000/svg";
    const make=(tag,attrs={})=>{
      const el=document.createElementNS(NS,tag);
      for (const [k,v] of Object.entries(attrs)) el.setAttribute(k,String(v));
      return el;
    };
    const text=(x,y,t,bold=false,anchor="start")=>{
      const el=make("text",{x,y,"font-size":13,"text-anchor":anchor});
      if (bold) el.setAttribute("font-weight","800");
      el.textContent=t;
      svg.appendChild(el);
    };
    const rawRect=(x,y,w,h,sw=1.2,col="#000",fill="transparent",op=1,dash=null)=>{
      const r=make("rect",{x,y,width:w,height:h,stroke:col,"stroke-width":sw,fill,opacity:op});
      if (dash) r.setAttribute("stroke-dasharray",dash);
      svg.appendChild(r);
    };
    const rawLine=(x1,y1,x2,y2,sw=1.2,col="#000",dash=null,op=1)=>{
      const l=make("line",{x1,y1,x2,y2,stroke:col,"stroke-width":sw,opacity:op,"stroke-linecap":"square"});
      if (dash) l.setAttribute("stroke-dasharray",dash);
      svg.appendChild(l);
    };

    const selectableLine=(id,x1,y1,x2,y2,dragType=null, tipLabel=null, tipGet=null, tipSet=null)=>{
      // HIT (IMPORTANT: not transparent stroke; we use opacity 0 + pointer-events=stroke)
      const hit=make("line",{
        x1,y1,x2,y2,
        stroke:"#000","stroke-width":18,
        "stroke-opacity":0,
        "pointer-events":"stroke"
      });
      hit.style.cursor = dragType ? "grab" : "pointer";
      hit.onmouseenter=()=>{ state.hover=id; renderAll(); };
      hit.onmouseleave=()=>{ state.hover=null; renderAll(); };
      hit.onclick=()=>{ state.selected=id; renderAll(); };
      if (dragType){
        hit.onpointerdown=(e)=>{
          state.drag = { type: dragType, tip: tipLabel ? {label:tipLabel, get:tipGet, set:tipSet} : null };
          e.preventDefault();
          if (state.drag.tip){
            dragTip.bindActive(state.drag.tip, e.clientX, e.clientY);
          }
          window.addEventListener("pointermove", onDragMove);
          window.addEventListener("pointerup", onDragEnd, { once:true });
        };
      }
      svg.appendChild(hit);

      // visible line
      const ln=make("line",{
        x1,y1,x2,y2,
        stroke: strokeColor(id),
        "stroke-width": strokeW(id),
        "stroke-linecap":"square"
      });
      svg.appendChild(ln);

      // small handle at mid (better visibility)
      if (dragType){
        const mx=(x1+x2)/2, my=(y1+y2)/2;
        const h=make("rect",{
          x: mx-5, y: my-5, width:10, height:10,
          fill: (id===state.selected ? "rgba(217,48,37,0.20)" : "rgba(0,0,0,0.10)"),
          stroke: strokeColor(id),
          "stroke-width": 1.2,
          rx:2, ry:2
        });
        svg.appendChild(h);
      }
    };

    const selectableCircle=(id,cx,cy,r,dragType=null, tipLabel=null, tipGet=null, tipSet=null)=>{
      const hit=make("circle",{
        cx,cy,r:r+10,
        fill:"transparent",
        stroke:"#000",
        "stroke-width":18,
        "stroke-opacity":0,
        "pointer-events":"stroke"
      });
      hit.style.cursor = dragType ? "grab" : "pointer";
      hit.onmouseenter=()=>{ state.hover=id; renderAll(); };
      hit.onmouseleave=()=>{ state.hover=null; renderAll(); };
      hit.onclick=()=>{ state.selected=id; renderAll(); };
      if (dragType){
        hit.onpointerdown=(e)=>{
          state.drag = { type: dragType, tip: tipLabel ? {label:tipLabel, get:tipGet, set:tipSet} : null };
          e.preventDefault();
          if (state.drag.tip){
            dragTip.bindActive(state.drag.tip, e.clientX, e.clientY);
          }
          window.addEventListener("pointermove", onDragMove);
          window.addEventListener("pointerup", onDragEnd, { once:true });
        };
      }
      svg.appendChild(hit);

      const c=make("circle",{
        cx,cy,r,
        fill: id===state.selected ? "rgba(217,48,37,0.18)" : "rgba(26,115,232,0.10)",
        stroke: strokeColor(id),
        "stroke-width": strokeW(id)
      });
      svg.appendChild(c);
    };

    // Titles
    text(frontX, frontY-20, "Front view", true);
    text(topX, topY-20, "Top view", true);

    // Envelope
    rawRect(frontX, frontY, frontW, frontH, 1.0, "#000", "transparent", 0.20);

    // clamp
    m.pos.L = clamp(m.pos.L, 0, Math.max(0, W - m.pos.R - 1));
    m.pos.R = clamp(m.pos.R, 0, Math.max(0, W - m.pos.L - 1));
    m.pos.T = clamp(m.pos.T, 0, Math.max(0, H - m.pos.B - 1));
    m.pos.B = clamp(m.pos.B, 0, Math.max(0, H - m.pos.T - 1));

    const leftX   = frontX + m.pos.L*scale;
    const rightX  = frontX + (W - m.pos.R)*scale;
    const topYl   = frontY + m.pos.T*scale;
    const bottomYl= frontY + (H - m.pos.B)*scale;

    const sideY1 = (m.sideMode==="between") ? topYl : frontY;
    const sideY2 = (m.sideMode==="between") ? bottomYl : (frontY+frontH);

    // lines with drag tip mapping
    if (m.has.left) selectableLine("left", leftX, sideY1, leftX, sideY2, "posL",
      "Left (mm)", ()=>m.pos.L, (v)=>{ m.pos.L=clamp(v,0,Math.max(0,W-m.pos.R-1)); $("posL").value=m.pos.L; normalizeShelves(); rebuildParts(); renderShelvesUI(); renderAll(); });

    if (m.has.right) selectableLine("right", rightX, sideY1, rightX, sideY2, "posR",
      "Right (mm)", ()=>m.pos.R, (v)=>{ m.pos.R=clamp(v,0,Math.max(0,W-m.pos.L-1)); $("posR").value=m.pos.R; normalizeShelves(); rebuildParts(); renderShelvesUI(); renderAll(); });

    if (m.has.top) selectableLine("top", leftX, topYl, rightX, topYl, "posT",
      "Top (mm)", ()=>m.pos.T, (v)=>{ m.pos.T=clamp(v,0,Math.max(0,H-m.pos.B-1)); $("posT").value=m.pos.T; normalizeShelves(); rebuildParts(); renderShelvesUI(); renderExtraShelvesUI(); renderAll(); });

    if (m.has.bottom) selectableLine("bottom", leftX, bottomYl, rightX, bottomYl, "posB",
      "Bottom (mm)", ()=>m.pos.B, (v)=>{ m.pos.B=clamp(v,0,Math.max(0,H-m.pos.T-1)); $("posB").value=m.pos.B; normalizeShelves(); rebuildParts(); renderShelvesUI(); renderExtraShelvesUI(); renderAll(); });

    // mid
    if (m.mid.enabled){
      const innerW = Math.max(50, (W - m.pos.L - m.pos.R));
      m.mid.x = clamp(m.mid.x, 1, innerW-1);
      const midX = frontX + (m.pos.L + m.mid.x)*scale;
      selectableLine("mid", midX, topYl, midX, bottomYl, "midX",
        "Mid X (mm)", ()=>m.mid.x, (v)=>{ m.mid.x=clamp(v,1,innerW-1); $("midX").value=m.mid.x; rebuildParts(); renderAll(); });
    }

    // shelves
    normalizeShelves();
    const innerH = Math.max(50, H - m.pos.T - m.pos.B);
    const yToSvg = (yFromBottom)=>{
      const yFromTopInner = innerH - yFromBottom;
      return topYl + yFromTopInner*scale;
    };
    const shelfX1 = leftX, shelfX2 = rightX;

    m.shelves.autoY.forEach((y, idx)=>{
      const id = "s_auto_"+idx;
      const ySvg = yToSvg(y);
      selectableLine(id, shelfX1, ySvg, shelfX2, ySvg, "shelf:"+id,
        `Shelf #${idx+1} (mm)`, ()=>m.shelves.autoY[idx], (v)=>{
          m.shelves.autoY[idx]=clamp(v,1,innerH-1);
          normalizeShelves();
          rebuildParts();
          renderShelvesUI();
          renderAll();
        });
      rawLine(shelfX1, ySvg, shelfX2, ySvg, 1.0, "#000", "6 6", 0.25);
    });

    m.shelves.extra.forEach((it)=>{
      const ySvg = yToSvg(it.y);
      selectableLine(it.id, shelfX1, ySvg, shelfX2, ySvg, "shelf:"+it.id,
        `Shelf extra (mm)`, ()=>it.y, (v)=>{
          it.y=clamp(v,1,innerH-1);
          normalizeShelves();
          rebuildParts();
          renderExtraShelvesUI();
          renderAll();
        });
      rawLine(shelfX1, ySvg, shelfX2, ySvg, 1.0, "#000", "6 6", 0.25);
    });

    // front dashed + corner marker
    if (m.has.front && m.front.mode!=="none" && m.front.count>0){
      rawRect(frontX, frontY, frontW, frontH, 1.0, "#000", "transparent", 0.18, "6 6");
      if (m.front.cornerFront){
        // simple diagonal marker on front (MVP)
        rawLine(frontX, frontY, frontX+frontW*0.35, frontY+frontH*0.35, 1.2, "#000", "6 6", 0.25);
      }
    }

    // anchor
    if (m.anchor.corner !== "NONE"){
      let ax = frontX, ay = frontY;
      if (m.anchor.corner==="LT"){ ax = frontX + m.anchor.dx*scale; ay = frontY + m.anchor.dy*scale; }
      if (m.anchor.corner==="RT"){ ax = frontX + frontW - m.anchor.dx*scale; ay = frontY + m.anchor.dy*scale; }
      if (m.anchor.corner==="LB"){ ax = frontX + m.anchor.dx*scale; ay = frontY + frontH - m.anchor.dy*scale; }
      if (m.anchor.corner==="RB"){ ax = frontX + frontW - m.anchor.dx*scale; ay = frontY + frontH - m.anchor.dy*scale; }
      selectableCircle("anchor", ax, ay, 6, "anchor",
        "Anchor DX/DY", ()=>m.anchor.dx, (v)=>{ m.anchor.dx=clamp(v,0,5000); $("anchorDX").value=m.anchor.dx; renderAll(); });
    }

    // top view
    rawRect(topX, topY, topW, topD, 1.2, "#000", "transparent", 1);
    if (m.has.back && m.back.enabled) selectableLine("back", topX, topY, topX+topW, topY);

    text(frontX + frontW/2, frontY + frontH + 30, `W ${W} mm`, false, "middle");
    text(frontX + frontW + 16, frontY + frontH/2, `H ${H} mm`);
    text(topX + topW + 16, topY + topD/2, `D ${D} mm`);
  }

  function onDragMove(e){
    if (!state.drag || !state.view) return;
    const svg = $("moduleView");
    const pt = clientToSvg(svg, e);
    const m = state.model;
    const {W,H} = m.dims;
    const {scale, frontX, frontY} = state.view;

    const xMm = (pt.x - frontX)/scale;
    const yMm = (pt.y - frontY)/scale;

    if (state.drag.tip){
      dragTip.showAt(e.clientX, e.clientY);
    }

    const t = state.drag.type;

    if (t==="posL"){
      m.pos.L = clamp(Math.round(xMm), 0, Math.max(0, W - m.pos.R - 1));
      $("posL").value = m.pos.L;
      dragTip.syncValue();
      normalizeShelves(); rebuildParts(); renderShelvesUI(); renderExtraShelvesUI(); renderAll();
      return;
    }
    if (t==="posR"){
      const rightIn = Math.round(W - xMm);
      m.pos.R = clamp(rightIn, 0, Math.max(0, W - m.pos.L - 1));
      $("posR").value = m.pos.R;
      dragTip.syncValue();
      normalizeShelves(); rebuildParts(); renderShelvesUI(); renderExtraShelvesUI(); renderAll();
      return;
    }
    if (t==="posT"){
      m.pos.T = clamp(Math.round(yMm), 0, Math.max(0, H - m.pos.B - 1));
      $("posT").value = m.pos.T;
      dragTip.syncValue();
      normalizeShelves(); rebuildParts(); renderShelvesUI(); renderExtraShelvesUI(); renderAll();
      return;
    }
    if (t==="posB"){
      const botIn = Math.round(H - yMm);
      m.pos.B = clamp(botIn, 0, Math.max(0, H - m.pos.T - 1));
      $("posB").value = m.pos.B;
      dragTip.syncValue();
      normalizeShelves(); rebuildParts(); renderShelvesUI(); renderExtraShelvesUI(); renderAll();
      return;
    }
    if (t==="midX"){
      const innerW = Math.max(50, W - m.pos.L - m.pos.R);
      const xInInner = Math.round(xMm - m.pos.L);
      m.mid.x = clamp(xInInner, 1, innerW-1);
      $("midX").value = m.mid.x;
      dragTip.syncValue();
      rebuildParts(); renderAll();
      return;
    }
    if (String(t).startsWith("shelf:")){
      const id = String(t).slice("shelf:".length);
      const innerH = Math.max(50, H - m.pos.T - m.pos.B);
      const yFromBottom = Math.round(innerH - (yMm - m.pos.T));
      const yClamped = clamp(yFromBottom, 1, innerH-1);

      if (id.startsWith("s_auto_")){
        const idx = Number(id.split("_").pop());
        if (Number.isFinite(idx) && m.shelves.autoY[idx]!=null){
          m.shelves.autoY[idx] = yClamped;
        }
      } else {
        const it = m.shelves.extra.find(x=>x.id===id);
        if (it) it.y = yClamped;
      }
      normalizeShelves();
      rebuildParts();
      renderShelvesUI();
      renderExtraShelvesUI();
      renderAll();
      return;
    }
    if (t==="anchor"){
      // anchor dragging (dx/dy) — simplified here
      // we'll keep as editable in inputs; marker drag can be extended later
      return;
    }
  }

  function onDragEnd(){
    window.removeEventListener("pointermove", onDragMove);
    // leave tip open for manual edit (user can press Enter)
    state.drag = null;
  }

  // ---- Tabs
  function setTab(t){
    state.tab = t;
    ["module","base","wall","set"].forEach(x=>{
      $("tab_"+x).classList.toggle("active", x===t);
      $("panel_"+x).classList.toggle("hidden", x!==t);
      $("main_"+x).classList.toggle("hidden", x!==t);
    });
    if (t==="base") renderBaseList();
    if (t==="wall") renderWallAll();
  }

  // ---- Splitters
  function initSplitters(){
    const leftSaved = num(localStorage.getItem(KEY_LEFTW), 560);
    if (leftSaved>340 && leftSaved<1200) document.documentElement.style.setProperty("--left", leftSaved+"px");

    const sideSaved = num(localStorage.getItem(KEY_SIDEW), 380);
    if (sideSaved>280 && sideSaved<800) document.documentElement.style.setProperty("--side", sideSaved+"px");

    const splitL = $("splitLeft");
    let resizing=false, startX=0, startW=0;
    splitL.addEventListener("pointerdown",(e)=>{
      resizing=true; startX=e.clientX;
      const cs = getComputedStyle(document.documentElement).getPropertyValue("--left").trim();
      startW = num(cs.replace("px",""), 560);
      splitL.setPointerCapture(e.pointerId);
    });
    splitL.addEventListener("pointermove",(e)=>{
      if(!resizing) return;
      const dx = e.clientX - startX;
      const w = clamp(startW + dx, 360, 980);
      document.documentElement.style.setProperty("--left", w+"px");
    });
    splitL.addEventListener("pointerup",(e)=>{
      if(!resizing) return;
      resizing=false;
      const cs = getComputedStyle(document.documentElement).getPropertyValue("--left").trim();
      const w = num(cs.replace("px",""), 560);
      localStorage.setItem(KEY_LEFTW, String(w));
      try{ splitL.releasePointerCapture(e.pointerId); }catch{}
    });

    const splitM = $("splitMid");
    let resizingM=false, startXM=0, startWM=0;
    splitM.addEventListener("pointerdown",(e)=>{
      resizingM=true; startXM=e.clientX;
      const cs = getComputedStyle(document.documentElement).getPropertyValue("--side").trim();
      startWM = num(cs.replace("px",""), 380);
      splitM.setPointerCapture(e.pointerId);
    });
    splitM.addEventListener("pointermove",(e)=>{
      if(!resizingM) return;
      const dx = e.clientX - startXM;
      const w = clamp(startWM - dx, 320, 620);
      document.documentElement.style.setProperty("--side", w+"px");
    });
    splitM.addEventListener("pointerup",(e)=>{
      if(!resizingM) return;
      resizingM=false;
      const cs = getComputedStyle(document.documentElement).getPropertyValue("--side").trim();
      const w = num(cs.replace("px",""), 380);
      localStorage.setItem(KEY_SIDEW, String(w));
      try{ splitM.releasePointerCapture(e.pointerId); }catch{}
    });
  }

  // ---- Base (templates)
  function fillGroupSelects(){
    const selA = $("moduleGroup");
    const selB = $("baseFilterGroup");
    selA.innerHTML = "";
    selB.innerHTML = "";

    const optAll = document.createElement("option");
    optAll.value = "ALL";
    optAll.textContent = "Wszystkie";
    selB.appendChild(optAll);

    for (const g of state.groups){
      const o1=document.createElement("option"); o1.value=g; o1.textContent=g; selA.appendChild(o1);
      const o2=document.createElement("option"); o2.value=g; o2.textContent=g; selB.appendChild(o2);
    }
    selA.value = state.model.group;
    selB.value = "ALL";
  }

  function updateLoadedInfo(){
    const t = state.templates.find(x=>x.id===state.loadedTemplateId);
    $("loadedInfo").textContent = t ? `Loaded: ${t.group} / ${t.name}` : "Loaded: —";
  }

  function snapshotModel(){
    return JSON.parse(JSON.stringify(state.model));
  }

  function saveAsNew(){
    const m = state.model;
    const name = String(m.name||"").trim();
    if (!name){ alert("Wpisz nazwę modelu."); return; }
    const tpl = { id: uid("tpl"), name, group: m.group, updatedAt: nowISO(), data: snapshotModel() };
    state.templates.unshift(tpl);
    saveTemplates(state.templates);
    state.loadedTemplateId = tpl.id;
    updateLoadedInfo();
    renderBaseList();
    renderStatus();
  }

  function overwriteLoaded(){
    const id = state.loadedTemplateId;
    if (!id){ alert("Najpierw załaduj model z bazy albo zapisz jako NOWY."); return; }
    const name = String(state.model.name||"").trim();
    if (!name){ alert("Wpisz nazwę modelu."); return; }
    const idx = state.templates.findIndex(x=>x.id===id);
    if (idx<0){ alert("Loaded model nie znaleziony w bazie."); return; }
    state.templates[idx] = { ...state.templates[idx], name, group: state.model.group, updatedAt: nowISO(), data: snapshotModel() };
    saveTemplates(state.templates);
    updateLoadedInfo();
    renderBaseList();
    renderStatus();
  }

  function detachLoaded(){
    state.loadedTemplateId = null;
    updateLoadedInfo();
    renderStatus();
  }

  function syncAllInputsFromModel(){
    const m = state.model;
    $("moduleGroup").value = m.group;
    $("moduleName").value = m.name || "";
    $("w").value = m.dims.W; $("h").value = m.dims.H; $("d").value = m.dims.D;
    $("anchorCorner").value = m.anchor.corner;
    $("anchorDX").value = m.anchor.dx;
    $("anchorDY").value = m.anchor.dy;
    $("posL").value = m.pos.L; $("posR").value = m.pos.R; $("posT").value = m.pos.T; $("posB").value = m.pos.B;
    $("sideMode").value = m.sideMode;

    $("hasLeft").checked = m.has.left;
    $("hasRight").checked = m.has.right;
    $("hasTop").checked = m.has.top;
    $("hasBottom").checked = m.has.bottom;
    $("hasBack").checked = m.has.back;
    $("hasFront").checked = m.has.front;

    $("midEnabled").checked = m.mid.enabled;
    $("midWrap").style.display = m.mid.enabled ? "" : "none";
    $("midX").value = m.mid.x;
    $("midMat").value = m.mid.mat;

    $("autoShelfCount").value = m.shelves.autoCount;

    $("backEnabled").value = m.back.enabled ? "yes" : "no";
    $("backMat").value = m.back.mat;

    $("frontMode").value = m.front.mode;
    $("frontCount").value = m.front.count;
    $("frontMat").value = m.front.mat;
    $("frontGap").value = m.front.gap;
    $("drawerSystem").value = m.front.drawerSystem;
    $("drawerHeights").value = m.front.drawerHeights || "";
    $("cornerFront").checked = !!m.front.cornerFront;
    $("drawerRow").style.display = (m.front.mode==="drawers") ? "" : "none";

    $("mountType").value = m.hardware.mountType;
    $("mountCount").value = m.hardware.mountCount;

    $("drawerEstimate").checked = !!m.hardware.drawerEstimate;
    $("drawerBottomMat").value = m.hardware.drawerBottomMat;
    $("drawerBackMat").value = m.hardware.drawerBackMat;
    $("drawerWoodMat").value = m.hardware.drawerWoodMat;
    $("drawerClear").value = m.hardware.drawerClear;

    $("quickBand").value = "abs08";
  }

  function loadTemplate(id){
    const tpl = state.templates.find(x=>x.id===id);
    if (!tpl) return;
    state.model = JSON.parse(JSON.stringify(tpl.data));
    state.loadedTemplateId = tpl.id;

    syncAllInputsFromModel();
    normalizeShelves();
    rebuildParts();
    renderShelvesUI();
    renderExtraShelvesUI();
    updateLoadedInfo();
    renderAll();
  }

  function deleteTemplate(id){
    state.templates = state.templates.filter(x=>x.id!==id);
    if (state.loadedTemplateId===id) state.loadedTemplateId=null;
    saveTemplates(state.templates);
    updateLoadedInfo();
    renderBaseList();
  }

  function renderBaseList(){
    const group = $("baseFilterGroup").value;
    const q = String($("baseSearch").value||"").toLowerCase().trim();

    const list = state.templates.filter(t=>{
      if (group && group!=="ALL" && t.group!==group) return false;
      if (q && !t.name.toLowerCase().includes(q)) return false;
      return true;
    });

    $("baseCount").textContent = String(list.length);
    const wrap = $("baseList");
    wrap.innerHTML = "";

    if (!list.length){
      wrap.innerHTML = `<div class="muted">—</div>`;
      return;
    }

    for (const t of list){
      const card = document.createElement("div");
      card.className = "listCard";
      const isLoaded = (t.id===state.loadedTemplateId);
      card.innerHTML = `
        <div class="listHeader">
          <div>
            <div><b>${esc(t.name)}</b> ${isLoaded ? '<span class="badge">LOADED</span>' : ''}</div>
            <div class="muted">${esc(t.group)} • ${esc(t.updatedAt)}</div>
          </div>
          <div class="btnRow">
            <button class="miniBtn" data-load="${t.id}">Load</button>
            <button class="miniBtn danger" data-del="${t.id}">Delete</button>
          </div>
        </div>
      `;
      wrap.appendChild(card);
    }

    wrap.querySelectorAll("button[data-load]").forEach(btn=> btn.onclick = ()=> loadTemplate(btn.getAttribute("data-load")));
    wrap.querySelectorAll("button[data-del]").forEach(btn=> btn.onclick = ()=> deleteTemplate(btn.getAttribute("data-del")));
  }

  function exportJSON(){
    const data = { groups: state.groups, templates: state.templates };
    const blob = new Blob([JSON.stringify(data,null,2)], {type:"application/json"});
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "tech_modul_db.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(()=>URL.revokeObjectURL(a.href), 500);
  }
  function importJSONFile(file){
    const r = new FileReader();
    r.onload = ()=>{
      try{
        const data = JSON.parse(String(r.result||"{}"));
        if (Array.isArray(data.groups) && Array.isArray(data.templates)){
          state.groups = data.groups;
          state.templates = data.templates;
          localStorage.setItem(KEY_GROUP, JSON.stringify(state.groups));
          saveTemplates(state.templates);
          fillGroupSelects();
          renderBaseList();
          alert("OK: zaimportowano.");
        } else alert("Zły format JSON.");
      }catch(err){
        alert("Błąd importu: " + err);
      }
    };
    r.readAsText(file);
  }

  // ---- Wall MVP
  function wallBBox(points){
    let minX=Infinity,minY=Infinity,maxX=-Infinity,maxY=-Infinity;
    points.forEach(p=>{
      minX=Math.min(minX,p.x); minY=Math.min(minY,p.y);
      maxX=Math.max(maxX,p.x); maxY=Math.max(maxY,p.y);
    });
    return {minX,minY,maxX,maxY,w:maxX-minX,h:maxY-minY};
  }

  function getWallPolyline(){
    const w = state.wall;
    if (w.type==="I"){
      return [{x:0,y:0},{x:w.A,y:0}];
    }
    if (w.type==="L"){
      return [{x:0,y:0},{x:w.LA,y:0},{x:w.LA,y:w.LB}];
    }
    // C
    return [{x:0,y:0},{x:w.CA,y:0},{x:w.CA,y:w.CB},{x:w.CA - w.CC,y:w.CB}];
  }

  function renderWallSVG(){
    const svg = $("wallView");
    svg.innerHTML = "";
    const NS="http://www.w3.org/2000/svg";
    const make=(tag,attrs={})=>{
      const el=document.createElementNS(NS,tag);
      for (const [k,v] of Object.entries(attrs)) el.setAttribute(k,String(v));
      return el;
    };

    const vbW=900, vbH=780, pad=70;
    const pts = getWallPolyline();
    const box = wallBBox(pts);

    // include island + obstacles in bbox
    const w = state.wall;
    const extra = [];
    if (w.island.on){
      extra.push({x:w.island.x, y:w.island.y});
      extra.push({x:w.island.x+w.island.W, y:w.island.y+w.island.D});
    }
    w.obs.forEach(o=>{
      extra.push({x:o.x, y:o.y});
      extra.push({x:o.x+o.W, y:o.y+o.D});
    });
    const box2 = extra.length ? wallBBox(pts.concat(extra)) : box;

    const scale = Math.min((vbW-2*pad)/(box2.w||1), (vbH-2*pad)/(box2.h||1));
    const toSvg=(x,y)=>({ X: pad + (x - box2.minX)*scale, Y: pad + (y - box2.minY)*scale });

    state.wall.view = { scale, pad, box: box2, toSvg };

    const bg = make("rect",{x:0,y:0,width:vbW,height:vbH,fill:"#fff"});
    svg.appendChild(bg);

    // polyline
    const d = pts.map((p,i)=>{
      const s=toSvg(p.x,p.y);
      return (i===0?`M ${s.X} ${s.Y}`:`L ${s.X} ${s.Y}`);
    }).join(" ");
    const path = make("path",{d,fill:"none",stroke:"#111","stroke-width":3,"stroke-linejoin":"round","stroke-linecap":"round"});
    svg.appendChild(path);

    // island
    if (w.island.on){
      const s=toSvg(w.island.x,w.island.y);
      const rect=make("rect",{x:s.X,y:s.Y,width:w.island.W*scale,height:w.island.D*scale,fill:"rgba(26,115,232,0.10)",stroke:"#1a73e8","stroke-width":2,rx:10,ry:10});
      svg.appendChild(rect);

      const hit=make("rect",{x:s.X,y:s.Y,width:w.island.W*scale,height:w.island.D*scale,fill:"transparent",stroke:"#000","stroke-width":18,"stroke-opacity":0,"pointer-events":"stroke"});
      hit.style.cursor="grab";
      hit.onpointerdown=(e)=>{
        w.drag={type:"island"};
        e.preventDefault();
        window.addEventListener("pointermove", onWallDragMove);
        window.addEventListener("pointerup", onWallDragEnd, {once:true});
      };
      svg.appendChild(hit);
    }

    // obstacles
    w.obs.forEach(o=>{
      const s=toSvg(o.x,o.y);
      const col = (o.id===w.selectedObsId) ? "#d93025" : "#111";
      const fill = (o.id===w.selectedObsId) ? "rgba(217,48,37,0.12)" : "rgba(0,0,0,0.06)";
      const r=make("rect",{x:s.X,y:s.Y,width:o.W*scale,height:o.D*scale,fill,stroke:col,"stroke-width":2,rx:10,ry:10});
      svg.appendChild(r);

      const t=make("text",{x:s.X+8,y:s.Y+16,"font-size":12,fill:col,"font-weight":800});
      t.textContent = o.name || o.type;
      svg.appendChild(t);

      const hit=make("rect",{x:s.X,y:s.Y,width:o.W*scale,height:o.D*scale,fill:"transparent",stroke:"#000","stroke-width":18,"stroke-opacity":0,"pointer-events":"stroke"});
      hit.style.cursor="grab";
      hit.onclick=()=>{ w.selectedObsId=o.id; renderWallAll(); };
      hit.onpointerdown=(e)=>{
        w.selectedObsId=o.id;
        w.drag={type:"obs", id:o.id};
        e.preventDefault();
        window.addEventListener("pointermove", onWallDragMove);
        window.addEventListener("pointerup", onWallDragEnd, {once:true});
        renderWallAll();
      };
      svg.appendChild(hit);
    });

    $("wallSelBadge").textContent = w.selectedObsId ? `Selected: ${w.selectedObsId}` : "Selected: —";
  }

  function onWallDragMove(e){
    const w = state.wall;
    if (!w.drag || !w.view) return;
    const svg = $("wallView");
    const pt = clientToSvg(svg, e);
    const {scale, box} = w.view;
    const xMm = (pt.x - 70)/scale + box.minX; // 70 = pad (fixed)
    const yMm = (pt.y - 70)/scale + box.minY;

    if (w.drag.type==="island"){
      w.island.x = clamp(Math.round(xMm), 0, 20000);
      w.island.y = clamp(Math.round(yMm), 0, 20000);
      $("islandX").value = w.island.x;
      $("islandY").value = w.island.y;
      renderWallAll();
      return;
    }
    if (w.drag.type==="obs"){
      const o = w.obs.find(x=>x.id===w.drag.id);
      if (!o) return;
      o.x = clamp(Math.round(xMm), 0, 20000);
      o.y = clamp(Math.round(yMm), 0, 20000);
      renderWallAll();
      return;
    }
  }
  function onWallDragEnd(){
    window.removeEventListener("pointermove", onWallDragMove);
    state.wall.drag = null;
  }

  function renderWallObsList(){
    const w = state.wall;
    $("wallObsCount").textContent = String(w.obs.length);

    const wrap = $("obsList");
    wrap.innerHTML = "";
    if (!w.obs.length){
      wrap.innerHTML = `<div class="muted">—</div>`;
      return;
    }
    w.obs.forEach(o=>{
      const card = document.createElement("div");
      card.className = "listCard";
      card.innerHTML = `
        <div class="listHeader">
          <div>
            <div><b>${esc(o.name || o.type)}</b></div>
            <div class="muted">${esc(o.type)} • x=${o.x}, y=${o.y} • ${o.W}×${o.D}</div>
          </div>
          <div class="btnRow">
            <button class="miniBtn" data-sel="${o.id}">Select</button>
            <button class="miniBtn danger" data-del="${o.id}">Delete</button>
          </div>
        </div>
      `;
      wrap.appendChild(card);
    });

    wrap.querySelectorAll("button[data-sel]").forEach(b=>b.onclick=()=>{
      w.selectedObsId = b.getAttribute("data-sel");
      renderWallAll();
    });
    wrap.querySelectorAll("button[data-del]").forEach(b=>b.onclick=()=>{
      const id=b.getAttribute("data-del");
      w.obs = w.obs.filter(x=>x.id!==id);
      if (w.selectedObsId===id) w.selectedObsId=null;
      renderWallAll();
    });

    const quick = $("wallObsQuick");
    quick.innerHTML = wrap.innerHTML;
  }

  function renderWallAll(){
    renderWallObsList();
    renderWallSVG();
  }

  function renderStatus(){
    const m = state.model;
    const t = state.templates.find(x=>x.id===state.loadedTemplateId);
    const loadedTxt = t ? ` • LOADED: ${t.name}` : "";
    $("statusPill").textContent = `${m.dims.W}×${m.dims.H}×${m.dims.D}${loadedTxt}`;
  }

  function renderAll(){
    renderStatus();
    renderPartsList();
    renderQuick();
    renderBOM();
    renderSVG();
  }

  function init(){
    // fill selects
    for (const m of materials){
      const o=document.createElement("option"); o.value=m.id; o.textContent=m.name;
      $("midMat").appendChild(o.cloneNode(true));
      $("backMat").appendChild(o.cloneNode(true));
      $("frontMat").appendChild(o.cloneNode(true));
      $("drawerBottomMat").appendChild(o.cloneNode(true));
      $("drawerBackMat").appendChild(o.cloneNode(true));
      $("drawerWoodMat").appendChild(o.cloneNode(true));
      $("quickMat").appendChild(o.cloneNode(true));
    }
    for (const b of edgeBands){
      const o=document.createElement("option"); o.value=b.id; o.textContent=b.name;
      $("quickBand").appendChild(o);
    }

    fillGroupSelects();
    state.model.group = state.groups[0] || "Kitchen";
    syncAllInputsFromModel();

    // tabs
    on("tab_module","click",()=>setTab("module"));
    on("tab_base","click",()=>setTab("base"));
    on("tab_wall","click",()=>setTab("wall"));
    on("tab_set","click",()=>setTab("set"));

    initSplitters();

    // base actions
    on("saveNew","click", saveAsNew);
    on("overwriteLoaded","click", overwriteLoaded);
    on("detachLoaded","click", detachLoaded);

    on("baseFilterGroup","change", renderBaseList);
    on("baseSearch","input", renderBaseList);
    on("exportJson","click", exportJSON);
    on("importJson","click", ()=> $("importFile").click());
    on("importFile","change", (e)=>{
      const f = e.target.files && e.target.files[0];
      if (f) importJSONFile(f);
      e.target.value = "";
    });

    // module inputs
    on("moduleGroup","change", ()=>{ state.model.group = $("moduleGroup").value; renderStatus(); });
    on("moduleName","input", ()=>{ state.model.name = $("moduleName").value; renderStatus(); });

    on("w","input", ()=>{ state.model.dims.W = clamp(Math.round(num($("w").value,600)), 50, 5000); rebuildParts(); renderAll(); });
    on("h","input", ()=>{ state.model.dims.H = clamp(Math.round(num($("h").value,720)), 50, 5000); normalizeShelves(); rebuildParts(); renderShelvesUI(); renderExtraShelvesUI(); renderAll(); });
    on("d","input", ()=>{ state.model.dims.D = clamp(Math.round(num($("d").value,560)), 50, 2000); rebuildParts(); renderAll(); });

    on("anchorCorner","change", ()=>{ state.model.anchor.corner = $("anchorCorner").value; renderAll(); });
    on("anchorDX","input", ()=>{ state.model.anchor.dx = clamp(Math.round(num($("anchorDX").value,0)), 0, 5000); renderAll(); });
    on("anchorDY","input", ()=>{ state.model.anchor.dy = clamp(Math.round(num($("anchorDY").value,0)), 0, 5000); renderAll(); });

    on("sideMode","change", ()=>{ state.model.sideMode = $("sideMode").value; renderAll(); });

    const bindPos=(id,key)=> on(id,"input", ()=>{
      const m=state.model;
      const {W,H}=m.dims;
      const v = clamp(Math.round(num($(id).value,0)), 0, 5000);
      if (key==="L") m.pos.L = clamp(v,0, Math.max(0, W - m.pos.R - 1));
      if (key==="R") m.pos.R = clamp(v,0, Math.max(0, W - m.pos.L - 1));
      if (key==="T") m.pos.T = clamp(v,0, Math.max(0, H - m.pos.B - 1));
      if (key==="B") m.pos.B = clamp(v,0, Math.max(0, H - m.pos.T - 1));
      normalizeShelves();
      rebuildParts();
      renderShelvesUI();
      renderExtraShelvesUI();
      renderAll();
    });
    bindPos("posL","L"); bindPos("posR","R"); bindPos("posT","T"); bindPos("posB","B");

    on("posZero","click", ()=>{
      state.model.pos = {L:0,R:0,T:0,B:0};
      syncAllInputsFromModel();
      normalizeShelves();
      rebuildParts();
      renderShelvesUI();
      renderExtraShelvesUI();
      renderAll();
    });
    on("posLRsame","click", ()=>{
      state.model.pos.R = state.model.pos.L;
      syncAllInputsFromModel();
      rebuildParts();
      renderAll();
    });
    on("posTBsame","click", ()=>{
      state.model.pos.B = state.model.pos.T;
      syncAllInputsFromModel();
      normalizeShelves();
      rebuildParts();
      renderShelvesUI();
      renderExtraShelvesUI();
      renderAll();
    });

    const bindHas=(id,key)=> on(id,"change", ()=>{
      state.model.has[key] = $(id).checked;
      if (key==="back") state.model.back.enabled = state.model.has.back && state.model.back.enabled;
      rebuildParts();
      renderAll();
    });
    bindHas("hasLeft","left"); bindHas("hasRight","right");
    bindHas("hasTop","top"); bindHas("hasBottom","bottom");
    bindHas("hasBack","back"); bindHas("hasFront","front");

    on("midEnabled","change", ()=>{
      state.model.mid.enabled = $("midEnabled").checked;
      $("midWrap").style.display = state.model.mid.enabled ? "" : "none";
      rebuildParts(); renderAll();
    });
    on("midX","input", ()=>{ state.model.mid.x = Math.round(num($("midX").value, state.model.mid.x)); rebuildParts(); renderAll(); });
    on("midMat","change", ()=>{ state.model.mid.mat = $("midMat").value; rebuildParts(); renderAll(); });

    on("autoShelfCount","input", ()=>{
      state.model.shelves.autoCount = clamp(Math.round(num($("autoShelfCount").value,0)), 0, 12);
      setAutoShelvesEqual();
      rebuildParts();
      renderShelvesUI();
      renderExtraShelvesUI();
      renderAll();
    });
    on("shelvesEqual","click", ()=>{
      setAutoShelvesEqual();
      rebuildParts();
      renderShelvesUI();
      renderAll();
    });
    on("shelvesClear","click", ()=>{
      state.model.shelves.autoCount = 0;
      state.model.shelves.autoY = [];
      $("autoShelfCount").value = 0;
      rebuildParts();
      renderShelvesUI();
      renderAll();
    });
    on("addExtraShelf","click", ()=>{
      const y = Math.round(num($("extraShelfY").value,150));
      state.model.shelves.extra.push({ id: uid("s_ex"), y });
      normalizeShelves();
      rebuildParts();
      renderExtraShelvesUI();
      renderAll();
    });

    on("backEnabled","change", ()=>{ state.model.back.enabled = $("backEnabled").value==="yes"; rebuildParts(); renderAll(); });
    on("backMat","change", ()=>{ state.model.back.mat = $("backMat").value; rebuildParts(); renderAll(); });

    on("frontMode","change", ()=>{
      state.model.front.mode = $("frontMode").value;
      $("drawerRow").style.display = (state.model.front.mode==="drawers") ? "" : "none";
      rebuildParts(); renderAll();
    });
    on("frontCount","input", ()=>{ state.model.front.count = clamp(Math.round(num($("frontCount").value,0)), 0, 12); rebuildParts(); renderAll(); });
    on("frontMat","change", ()=>{ state.model.front.mat = $("frontMat").value; rebuildParts(); renderAll(); });
    on("frontGap","input", ()=>{ state.model.front.gap = clamp(Math.round(num($("frontGap").value,2)), 0, 10); rebuildParts(); renderAll(); });
    on("drawerSystem","change", ()=>{ state.model.front.drawerSystem = $("drawerSystem").value; rebuildParts(); renderAll(); });
    on("drawerHeights","input", ()=>{ state.model.front.drawerHeights = $("drawerHeights").value; rebuildParts(); renderAll(); });
    on("cornerFront","change", ()=>{ state.model.front.cornerFront = $("cornerFront").checked; rebuildParts(); renderAll(); });

    on("mountType","change", ()=>{ state.model.hardware.mountType = $("mountType").value; renderAll(); });
    on("mountCount","input", ()=>{ state.model.hardware.mountCount = clamp(Math.round(num($("mountCount").value,0)), 0, 99); renderAll(); });

    on("drawerEstimate","change", ()=>{ state.model.hardware.drawerEstimate = $("drawerEstimate").checked; renderAll(); });
    on("drawerBottomMat","change", ()=>{ state.model.hardware.drawerBottomMat = $("drawerBottomMat").value; renderAll(); });
    on("drawerBackMat","change", ()=>{ state.model.hardware.drawerBackMat = $("drawerBackMat").value; renderAll(); });
    on("drawerWoodMat","change", ()=>{ state.model.hardware.drawerWoodMat = $("drawerWoodMat").value; renderAll(); });
    on("drawerClear","input", ()=>{ state.model.hardware.drawerClear = clamp(Math.round(num($("drawerClear").value,40)), 0, 200); renderAll(); });

    // Quick
    on("quickMat","change", ()=>{ const p = selPart(); if(!p) return; p.mat = $("quickMat").value; renderAll(); });
    on("qL","click", ()=>toggleEdge("L"));
    on("qR","click", ()=>toggleEdge("R"));
    on("qT","click", ()=>toggleEdge("T"));
    on("qB","click", ()=>toggleEdge("B"));
    on("qAll08","click", ()=>setAllEdges("abs08"));
    on("qAll2","click", ()=>setAllEdges("abs2"));
    on("qClear","click", clearEdges);
    on("qApplyKind","click", applyKind);

    // Wall bindings
    on("wallType","change", ()=>{
      state.wall.type = $("wallType").value;
      $("wallDimsI").classList.toggle("hidden", state.wall.type!=="I");
      $("wallDimsL").classList.toggle("hidden", state.wall.type!=="L");
      $("wallDimsC").classList.toggle("hidden", state.wall.type!=="C");
      renderWallAll();
    });
    on("wallH","input", ()=>{ state.wall.H = Math.round(num($("wallH").value,2700)); renderWallAll(); });

    on("wallA","input", ()=>{ state.wall.A = Math.round(num($("wallA").value,4000)); renderWallAll(); });
    on("wallTh","input", ()=>{ state.wall.th = Math.round(num($("wallTh").value,120)); renderWallAll(); });

    on("wallLA","input", ()=>{ state.wall.LA = Math.round(num($("wallLA").value,3000)); renderWallAll(); });
    on("wallLB","input", ()=>{ state.wall.LB = Math.round(num($("wallLB").value,2500)); renderWallAll(); });
    on("wallLTh","input", ()=>{ state.wall.Lth = Math.round(num($("wallLTh").value,120)); renderWallAll(); });

    on("wallCA","input", ()=>{ state.wall.CA = Math.round(num($("wallCA").value,3500)); renderWallAll(); });
    on("wallCB","input", ()=>{ state.wall.CB = Math.round(num($("wallCB").value,2200)); renderWallAll(); });
    on("wallCC","input", ()=>{ state.wall.CC = Math.round(num($("wallCC").value,1600)); renderWallAll(); });
    on("wallCTh","input", ()=>{ state.wall.Cth = Math.round(num($("wallCTh").value,120)); renderWallAll(); });

    on("islandOn","change", ()=>{
      state.wall.island.on = $("islandOn").checked;
      $("islandWrap").classList.toggle("hidden", !state.wall.island.on);
      renderWallAll();
    });
    on("islandW","input", ()=>{ state.wall.island.W = Math.round(num($("islandW").value,900)); renderWallAll(); });
    on("islandD","input", ()=>{ state.wall.island.D = Math.round(num($("islandD").value,600)); renderWallAll(); });
    on("islandX","input", ()=>{ state.wall.island.x = Math.round(num($("islandX").value,1200)); renderWallAll(); });
    on("islandY","input", ()=>{ state.wall.island.y = Math.round(num($("islandY").value,800)); renderWallAll(); });

    on("addObs","click", ()=>{
      const o = {
        id: uid("obs"),
        type: $("obsType").value,
        name: String($("obsName").value || "").trim() || $("obsType").value,
        x: Math.round(num($("obsX").value,800)),
        y: Math.round(num($("obsY").value,0)),
        W: Math.round(num($("obsW").value,1200)),
        D: Math.round(num($("obsD").value,120))
      };
      state.wall.obs.push(o);
      state.wall.selectedObsId = o.id;
      renderWallAll();
    });

    // initial shelves
    setAutoShelvesEqual();
    normalizeShelves();

    rebuildParts();
    renderShelvesUI();
    renderExtraShelvesUI();
    updateLoadedInfo();
    renderAll();

    // init wall UI visibility
    $("wallDimsI").classList.toggle("hidden", state.wall.type!=="I");
    $("wallDimsL").classList.toggle("hidden", state.wall.type!=="L");
    $("wallDimsC").classList.toggle("hidden", state.wall.type!=="C");
    $("islandWrap").classList.toggle("hidden", !state.wall.island.on);

    window.addEventListener("resize", ()=>{ renderSVG(); renderWallSVG(); });
  }

  init();
})();

