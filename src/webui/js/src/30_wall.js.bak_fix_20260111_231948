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

  
