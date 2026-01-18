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

    const innerW_shelf = Math.max(50, (W - m.pos.L - m.pos.R));
const midOn = !!m.mid.enabled;
const midX_shelf = midOn ? clamp(m.mid.x, 1, innerW_shelf-1) : null;
const leftW_shelf = midOn ? midX_shelf : innerW_shelf;
const rightW_shelf = midOn ? (innerW_shelf - midX_shelf) : 0;

function getShelfSpan(baseId){
  if (!m.shelves.span) m.shelves.span = {};
  if (!m.shelves.span[baseId]) m.shelves.span[baseId] = "both";
  return m.shelves.span[baseId];
}

function pushShelfParts(baseId, label, y, shelfType){
  const span = getShelfSpan(baseId);
  const metaBase = { shelfY:y, shelfType:shelfType, baseId:baseId };

  if (!midOn){
    p.push(mkPart(baseId, label, "shelf", "pb18", innerW_shelf, D, metaBase));
    return;
  }

  if (span === "both" -or span === "left") {
    p.push(mkPart(`${baseId}_L`, `${label} (L)`, "shelf", "pb18", leftW_shelf, D, { ...metaBase, side:"L" }));
  }
  if (span === "both" -or span === "right") {
    p.push(mkPart(`${baseId}_R`, `${label} (P)`, "shelf", "pb18", rightW_shelf, D, { ...metaBase, side:"R" }));
  }
}

m.shelves.autoY.forEach((y, idx)=>{
  const baseId = "s_auto_"+idx;
  pushShelfParts(baseId, `Półka auto #${idx+1}`, y, "auto");
});
m.shelves.extra.forEach((it)=>{
  const baseId = it.id;
  pushShelfParts(baseId, `Półka extra`, it.y, "extra");
});});

    if (m.has.front && m.front.mode !== "none" && m.front.count>0){
      const gap = clamp(m.front.gap, 0, 10);
const innerH_opening = Math.max(20, H - m.pos.T - m.pos.B);
const legsExtra = (m.hardware.mountType === "legs") ? num(m.hardware.legsH, 0) : 0;

let frontH = Math.max(10, H - 2*gap); // carcass default
if (m.front.heightMode === "opening") {
  frontH = Math.max(10, innerH_opening - 2*gap);
}
if (m.front.heightMode === "floor") {
  frontH = Math.max(10, (H + legsExtra) - 2*gap);
}
      const count = clamp(m.front.count, 1, 12);

      if (m.front.mode==="doors"){
        const doorCount = count;
        const totalGap = (doorCount+1)*gap;
        const doorW = Math.max(10, Math.floor((W - totalGap)/doorCount));
        const doorH = frontH;
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
          const avail = Math.max(20, frontH - totalGap);
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

  

