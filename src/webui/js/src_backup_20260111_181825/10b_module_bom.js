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
  const innerH_opening = Math.max(20, m.dims.H - m.pos.T - m.pos.B);
  const legsExtra = (m.hardware.mountType === "legs") ? num(m.hardware.legsH, 0) : 0;

  let frontH_bom = Math.max(10, m.dims.H - 2*gap);
  if (m.front.heightMode === "opening") frontH_bom = Math.max(10, innerH_opening - 2*gap);
  if (m.front.heightMode === "floor")   frontH_bom = Math.max(10, (m.dims.H + legsExtra) - 2*gap);
const gap = clamp(m.front.gap,0,10);
      const doorH = frontH_bom;
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

  

