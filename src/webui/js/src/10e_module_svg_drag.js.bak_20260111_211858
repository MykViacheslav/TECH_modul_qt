function renderSVG(){
  const svg = $("moduleView");
  if (!svg) return;
  svg.innerHTML = "";

  const m = state.model;
  const {W,H,D} = m.dims;

  // defaults (backward safe)
  if (!m.midA) m.midA = { enabled:false, x:Math.floor(W/2), mat:"pb18", offT:0, offB:0 };
  if (!m.midB) m.midB = { enabled:false, x:Math.floor(W*0.7), mat:"pb18", offT:0, offB:0 };
  if (!m.front) m.front = { mode:"none", count:0, mat:"mdf18", gap:2, inset:2 };
  if (m.front.inset == null) m.front.inset = 2;

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
  const line=(x1,y1,x2,y2,sw=1.2,col="#000",dash=null,op=1)=>{
    const l=make("line",{x1,y1,x2,y2,stroke:col,"stroke-width":sw,opacity:op,"stroke-linecap":"square"});
    if (dash) l.setAttribute("stroke-dasharray",dash);
    svg.appendChild(l);
    return l;
  };
  const rect=(x,y,w,h,sw=1.2,col="#000",fill="transparent",op=1,dash=null)=>{
    const r=make("rect",{x,y,width:w,height:h,stroke:col,"stroke-width":sw,fill,opacity:op});
    if (dash) r.setAttribute("stroke-dasharray",dash);
    svg.appendChild(r);
    return r;
  };

  const strokeColor=(id)=>{
    if (id===state.selected) return "#d93025";
    if (id===state.hover) return "#1a73e8";
    return "#000";
  };
  const strokeW=(id)=>{
    if (id===state.selected) return 4.2;
    if (id===state.hover) return 2.6;
    return 1.3;
  };

  const selectableLine=(id,x1,y1,x2,y2,dragType=null, tipLabel=null, tipGet=null, tipSet=null)=>{
    const hit=make("line",{x1,y1,x2,y2,stroke:"#000","stroke-width":18,"stroke-opacity":0,"pointer-events":"stroke"});
    hit.style.cursor = dragType ? "grab" : "pointer";
    hit.onmouseenter=()=>{ state.hover=id; renderAll(); };
    hit.onmouseleave=()=>{ state.hover=null; renderAll(); };
    hit.onclick=()=>{ state.selected=id; renderAll(); };
    if (dragType){
      hit.onpointerdown=(e)=>{
        state.drag = { type: dragType, tip: tipLabel ? {label:tipLabel, get:tipGet, set:tipSet} : null };
        e.preventDefault();
        if (state.drag.tip && typeof dragTip!=="undefined"){ dragTip.bindActive(state.drag.tip, e.clientX, e.clientY); }
        window.addEventListener("pointermove", onDragMove);
        window.addEventListener("pointerup", onDragEnd, { once:true });
      };
    }
    svg.appendChild(hit);

    const ln=make("line",{x1,y1,x2,y2,stroke: strokeColor(id),"stroke-width": strokeW(id),"stroke-linecap":"square"});
    svg.appendChild(ln);
  };

  // Titles
  text(frontX, frontY-20, "Front view", true);
  text(topX, topY-20, "Top view", true);

  // envelope
  rect(frontX, frontY, frontW, frontH, 1.0, "#000", "transparent", 0.20);

  // clamp pos
  m.pos.L = clamp(m.pos.L, 0, Math.max(0, W - m.pos.R - 1));
  m.pos.R = clamp(m.pos.R, 0, Math.max(0, W - m.pos.L - 1));
  m.pos.T = clamp(m.pos.T, 0, Math.max(0, H - m.pos.B - 1));
  m.pos.B = clamp(m.pos.B, 0, Math.max(0, H - m.pos.T - 1));

  const leftX   = frontX + m.pos.L*scale;
  const rightX  = frontX + (W - m.pos.R)*scale;
  const topYl   = frontY + m.pos.T*scale;
  const bottomYl= frontY + (H - m.pos.B)*scale;

  selectableLine("left", leftX, frontY, leftX, frontY+frontH, "posL", "Left (mm)", ()=>m.pos.L, (v)=>{ m.pos.L=clamp(v,0,Math.max(0,W-m.pos.R-1)); $("posL").value=m.pos.L; rebuildParts(); renderAll(); });
  selectableLine("right", rightX, frontY, rightX, frontY+frontH, "posR", "Right (mm)", ()=>m.pos.R, (v)=>{ m.pos.R=clamp(v,0,Math.max(0,W-m.pos.L-1)); $("posR").value=m.pos.R; rebuildParts(); renderAll(); });
  selectableLine("top", leftX, topYl, rightX, topYl, "posT", "Top (mm)", ()=>m.pos.T, (v)=>{ m.pos.T=clamp(v,0,Math.max(0,H-m.pos.B-1)); $("posT").value=m.pos.T; rebuildParts(); renderAll(); });
  selectableLine("bottom", leftX, bottomYl, rightX, bottomYl, "posB", "Bottom (mm)", ()=>m.pos.B, (v)=>{ m.pos.B=clamp(v,0,Math.max(0,H-m.pos.T-1)); $("posB").value=m.pos.B; rebuildParts(); renderAll(); });

  // inner dims
  const innerW = Math.max(50, W - m.pos.L - m.pos.R);
  const innerH = Math.max(50, H - m.pos.T - m.pos.B);

  // mids with offsets
  const drawMid = (id, mm, xLocal)=>{
    mm.offT = clamp(Math.round(num(mm.offT,0)), 0, innerH-1);
    mm.offB = clamp(Math.round(num(mm.offB,0)), 0, Math.max(0, innerH - mm.offT - 1));
    const midX = frontX + (m.pos.L + xLocal)*scale;
    const y1 = topYl + mm.offT*scale;
    const y2 = bottomYl - mm.offB*scale;

    selectableLine(id, midX, y1, midX, y2, (id==="midA"?"midX":"mid2X"),
      (id==="midA"?"MidA X (mm)":"MidB X (mm)"),
      ()=>xLocal,
      (v)=>{ /* handled in drag */ });

    // markers for offsets
    line(midX-10, y1, midX+10, y1, 1.0, "#000", "4 4", 0.25);
    line(midX-10, y2, midX+10, y2, 1.0, "#000", "4 4", 0.25);
  };

  // sort x if both enabled
  let aOn=!!m.midA.enabled, bOn=!!m.midB.enabled;
  let aX = aOn ? clamp(Math.round(num(m.midA.x, Math.floor(innerW/2))), 1, innerW-1) : null;
  let bX = bOn ? clamp(Math.round(num(m.midB.x, Math.floor(innerW*0.7))), 1, innerW-1) : null;

  if(aOn) m.midA.x = aX;
  if(bOn) m.midB.x = bX;

  if(aOn) drawMid("midA", m.midA, aX);
  if(bOn) drawMid("midB", m.midB, bX);

  // FRONT with inset from sides
  const inset = clamp(Math.round(num(m.front.inset,2)), 0, 50);
  const fx1 = leftX + inset*scale;
  const fx2 = rightX - inset*scale;
  const fy1 = topYl + inset*scale;
  const fy2 = bottomYl - inset*scale;

  if (m.front && m.front.mode && m.front.mode !== "none"){
    const dash = (m.front.mode==="drawers") ? "10 4 2 4" : null; // dash-dot for drawers
    rect(fx1, fy1, Math.max(10, fx2-fx1), Math.max(10, fy2-fy1), 1.4, "#000", "transparent", 0.9, dash);
  }

  // Top view box
  rect(topX, topY, topW, topD, 1.2, "#000", "transparent", 1);

  text(frontX + frontW/2, frontY + frontH + 30, `W ${W} mm`, false, "middle");
  text(frontX + frontW + 16, frontY + frontH/2, `H ${H} mm`);
  text(topX + topW + 16, topY + topD/2, `D ${D} mm`);
}

function clientToSvg(svg, e){
  const rect = svg.getBoundingClientRect();
  const vb = svg.viewBox.baseVal;
  const x = (e.clientX - rect.left) * (vb.width / rect.width);
  const y = (e.clientY - rect.top)  * (vb.height / rect.height);
  return {x,y};
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

  if (state.drag.tip && typeof dragTip!=="undefined"){ dragTip.showAt(e.clientX, e.clientY); }

  const t = state.drag.type;

  if (t==="posL"){ m.pos.L = clamp(Math.round(xMm), 0, Math.max(0, W - m.pos.R - 1)); $("posL").value=m.pos.L; rebuildParts(); renderAll(); return; }
  if (t==="posR"){ const rightIn = Math.round(W - xMm); m.pos.R = clamp(rightIn, 0, Math.max(0, W - m.pos.L - 1)); $("posR").value=m.pos.R; rebuildParts(); renderAll(); return; }
  if (t==="posT"){ m.pos.T = clamp(Math.round(yMm), 0, Math.max(0, H - m.pos.B - 1)); $("posT").value=m.pos.T; rebuildParts(); renderAll(); return; }
  if (t==="posB"){ const botIn = Math.round(H - yMm); m.pos.B = clamp(botIn, 0, Math.max(0, H - m.pos.T - 1)); $("posB").value=m.pos.B; rebuildParts(); renderAll(); return; }

  const innerW = Math.max(50, W - m.pos.L - m.pos.R);
  if (t==="midX"){
    const xInInner = Math.round(xMm - m.pos.L);
    m.midA.x = clamp(xInInner, 1, innerW-1);
    if ($("midX")) $("midX").value = m.midA.x;
    rebuildParts(); renderAll(); return;
  }
  if (t==="mid2X"){
    const xInInner = Math.round(xMm - m.pos.L);
    m.midB.x = clamp(xInInner, 1, innerW-1);
    if ($("mid2X")) $("mid2X").value = m.midB.x;
    rebuildParts(); renderAll(); return;
  }
}

function onDragEnd(){
  window.removeEventListener("pointermove", onDragMove);
  state.drag = null;
}
