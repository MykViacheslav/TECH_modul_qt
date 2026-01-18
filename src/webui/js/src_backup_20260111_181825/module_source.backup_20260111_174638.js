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

  
