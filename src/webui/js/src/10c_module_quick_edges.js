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

  
