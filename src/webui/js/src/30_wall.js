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
    (w.modules3dc||[]).forEach(m=>{
      extra.push({x:m.x, y:m.y});
      extra.push({x:m.x+m.length, y:m.y+m.width});
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

    // 3D-Constructor modules
    (w.modules3dc||[]).forEach(m=>{
      const s=toSvg(m.x,m.y);
      const selected = m.id===w.selectedModuleId;
      const col = selected ? "#137333" : "#0b57d0";
      const fill = selected ? "rgba(19,115,51,0.16)" : "rgba(11,87,208,0.12)";
      const r=make("rect",{
        x:s.X,
        y:s.Y,
        width:Math.max(4,m.length*scale),
        height:Math.max(4,m.width*scale),
        fill,
        stroke:col,
        "stroke-width":selected ? 3 : 2,
        rx:6,
        ry:6
      });
      svg.appendChild(r);

      const t=make("text",{x:s.X+8,y:s.Y+18,"font-size":12,fill:col,"font-weight":900});
      t.textContent = m.code || m.name || "3DC";
      svg.appendChild(t);

      const dim=make("text",{x:s.X+8,y:s.Y+36,"font-size":11,fill:col});
      dim.textContent = `${Math.round(m.length)}×${Math.round(m.width)}×${Math.round(m.height)}`;
      svg.appendChild(dim);

      const hit=make("rect",{
        x:s.X,
        y:s.Y,
        width:Math.max(6,m.length*scale),
        height:Math.max(6,m.width*scale),
        fill:"transparent",
        stroke:"#000",
        "stroke-width":18,
        "stroke-opacity":0,
        "pointer-events":"stroke"
      });
      hit.style.cursor="grab";
      hit.onclick=()=>{ w.selectedModuleId=m.id; renderWallAll(); };
      hit.onpointerdown=(e)=>{
        w.selectedModuleId=m.id;
        w.drag={type:"module3dc", id:m.id};
        e.preventDefault();
        window.addEventListener("pointermove", onWallDragMove);
        window.addEventListener("pointerup", onWallDragEnd, {once:true});
        renderWallAll();
      };
      svg.appendChild(hit);
    });

    const selBadge = $("wallSelBadge");
    if (selBadge){
      selBadge.textContent = w.selectedModuleId
        ? `Selected: ${w.selectedModuleId}`
        : (w.selectedObsId ? `Selected: ${w.selectedObsId}` : "Selected: —");
    }
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
    if (w.drag.type==="module3dc"){
      const m = (w.modules3dc||[]).find(x=>x.id===w.drag.id);
      if (!m) return;
      m.x = clamp(Math.round(xMm), 0, 20000);
      m.y = clamp(Math.round(yMm), 0, 20000);
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

  function ensureWallModulesPanel(){
    if ($("modules3dcPanel")) return;
    const host = $("panel_wall") || $("main_wall") || $("obsList")?.parentElement;
    if (!host) return;

    const card = document.createElement("div");
    card.className = "listCard";
    card.id = "modules3dcPanel";
    card.style.marginTop = "12px";
    card.innerHTML = `
      <div class="listHeader">
        <div>
          <div><b>Moduly 3D-Constructor</b></div>
          <div class="muted">Import .project, zmiana wymiarow i ustawianie na scianie.</div>
        </div>
        <div class="badge" id="modules3dcCount">0</div>
      </div>
      <div class="btnRow" style="margin-top:10px">
        <button class="miniBtn" id="import3dcProjectBtn" type="button">Import .project</button>
        <button class="miniBtn" id="add3dcDemoBtn" type="button">Demo</button>
      </div>
      <input id="import3dcProjectFile" type="file" accept=".project,.xml" style="display:none">
      <div id="modules3dcList" style="margin-top:10px"></div>
    `;
    host.appendChild(card);

    $("import3dcProjectBtn").onclick=()=> $("import3dcProjectFile").click();
    $("import3dcProjectFile").onchange=(e)=>{
      const file = e.target.files && e.target.files[0];
      if (file) import3dcProjectFile(file);
      e.target.value = "";
    };
    $("add3dcDemoBtn").onclick=()=>{
      add3dcModule({
        code:"ASS1.00.000",
        name:"SZ_D_1F_lewa",
        length:400,
        width:525,
        height:780,
        x:120,
        y:120
      });
      renderWallAll();
    };
  }

  function add3dcModule(data){
    const w = state.wall;
    if (!Array.isArray(w.modules3dc)) w.modules3dc = [];
    const id = uid("m3dc");
    w.modules3dc.push({
      id,
      code:String(data.code||data.name||"3DC"),
      name:String(data.name||data.code||"3D-Constructor module"),
      length:clamp(Math.round(num(data.length,600)), 1, 20000),
      width:clamp(Math.round(num(data.width,560)), 1, 20000),
      height:clamp(Math.round(num(data.height,720)), 1, 20000),
      x:clamp(Math.round(num(data.x,0)), 0, 20000),
      y:clamp(Math.round(num(data.y,0)), 0, 20000),
      z:clamp(Math.round(num(data.z,0)), 0, 20000),
      angle:Math.round(num(data.angle,0)),
      coordinateSystem:Number.isFinite(Number(data.coordinateSystem)) ? Number(data.coordinateSystem) : -1,
      sourceObjId:String(data.sourceObjId||"")
    });
    w.selectedModuleId = id;
  }

  function import3dcProjectFile(file){
    const reader = new FileReader();
    reader.onload=()=>{
      try{
        const modules = parse3dcProject(String(reader.result||""), file.name);
        if (!modules.length){
          alert("Nie znaleziono glownych modulow class=1 w pliku .project.");
          return;
        }
        const w = state.wall;
        const maxX = (w.modules3dc||[]).reduce((acc,m)=>Math.max(acc, num(m.x,0)+num(m.length,0)), 0);
        modules.forEach((m,i)=> add3dcModule({...m, x:maxX + 40 + num(m.x,0), y:num(m.y,0)}));
        renderWallAll();
      }catch(err){
        alert("Blad importu .project: " + err);
      }
    };
    reader.readAsText(file);
  }

  function parse3dcProject(xmlText, fileName="project"){
    const doc = new DOMParser().parseFromString(xmlText, "application/xml");
    if (doc.querySelector("parsererror")) throw new Error("Niepoprawny XML");
    const projectName = doc.documentElement?.getAttribute("name") || fileName.replace(/\.(project|xml)$/i,"");
    const assemblies = Array.from(doc.querySelectorAll("Obj[class='1']"));
    const top = assemblies.filter(node=>!String(node.getAttribute("parent")||"").trim());
    const picked = top.length ? top : assemblies;
    return picked.map((node,i)=>({
      code:node.getAttribute("code") || `${projectName}_${i+1}`,
      name:node.getAttribute("name") || node.getAttribute("code") || `${projectName} ${i+1}`,
      length:num(node.getAttribute("dtl") || node.getAttribute("l"), 600),
      width:num(node.getAttribute("dtw") || node.getAttribute("w"), 560),
      height:num(node.getAttribute("dtt"), 720),
      x:i*640,
      y:0,
      sourceObjId:node.getAttribute("id") || ""
    }));
  }

  function renderWallModulesList(){
    ensureWallModulesPanel();
    const w = state.wall;
    if (!Array.isArray(w.modules3dc)) w.modules3dc = [];
    const count = $("modules3dcCount");
    if (count) count.textContent = String(w.modules3dc.length);
    const wrap = $("modules3dcList");
    if (!wrap) return;
    wrap.innerHTML = "";
    if (!w.modules3dc.length){
      wrap.innerHTML = `<div class="muted">Brak modulow.</div>`;
      return;
    }
    w.modules3dc.forEach(m=>{
      const card = document.createElement("div");
      card.className = "listCard";
      card.innerHTML = `
        <div class="listHeader">
          <div>
            <div><b>${esc(m.code)}</b> ${m.id===w.selectedModuleId ? '<span class="badge">SELECTED</span>' : ''}</div>
            <div class="muted">${esc(m.name)} • x=${m.x}, y=${m.y}</div>
          </div>
          <div class="btnRow">
            <button class="miniBtn" data-sel3dc="${m.id}">Select</button>
            <button class="miniBtn danger" data-del3dc="${m.id}">Delete</button>
          </div>
        </div>
        <div class="row3" style="margin-top:10px">
          <div><label>Dlug.</label><input data-m3dc="${m.id}" data-field="length" value="${m.length}" type="number"></div>
          <div><label>Szer.</label><input data-m3dc="${m.id}" data-field="width" value="${m.width}" type="number"></div>
          <div><label>Wys.</label><input data-m3dc="${m.id}" data-field="height" value="${m.height}" type="number"></div>
        </div>
      `;
      wrap.appendChild(card);
    });

    wrap.querySelectorAll("button[data-sel3dc]").forEach(b=>b.onclick=()=>{
      w.selectedModuleId = b.getAttribute("data-sel3dc");
      renderWallAll();
    });
    wrap.querySelectorAll("button[data-del3dc]").forEach(b=>b.onclick=()=>{
      const id = b.getAttribute("data-del3dc");
      w.modules3dc = w.modules3dc.filter(x=>x.id!==id);
      if (w.selectedModuleId===id) w.selectedModuleId=null;
      renderWallAll();
    });
    wrap.querySelectorAll("input[data-m3dc]").forEach(inp=>inp.oninput=()=>{
      const id = inp.getAttribute("data-m3dc");
      const field = inp.getAttribute("data-field");
      const m = w.modules3dc.find(x=>x.id===id);
      if (!m) return;
      m[field] = clamp(Math.round(num(inp.value, m[field])), 1, 20000);
      w.selectedModuleId = id;
      renderWallSVG();
    });
  }

  function renderWallAll(){
    renderWallObsList();
    renderWallModulesList();
    renderWallSVG();
  }

  
