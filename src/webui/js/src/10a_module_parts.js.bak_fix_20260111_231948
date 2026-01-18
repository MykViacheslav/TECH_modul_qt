function rebuildParts(){
  const m = state.model;
  const {W,H,D} = m.dims;

  if (!m.midA) m.midA = { enabled:false, x:Math.floor(W/2), mat:"pb18", offT:0, offB:0 };
  if (!m.midB) m.midB = { enabled:false, x:Math.floor(W*0.7), mat:"pb18", offT:0, offB:0 };
  if (!m.shelves) m.shelves = { autoCount:0, autoY:[], extra:[], seg:"ALL" };
  if (m.shelves.seg == null) m.shelves.seg = "ALL";

  const p = [];
  const matSide = "pb18";

  // basic carcass
  if (m.has?.left)   p.push(mkPart("left","Bok lewy","side", matSide, D, H));
  if (m.has?.right)  p.push(mkPart("right","Bok prawy","side", matSide, D, H));
  if (m.has?.top)    p.push(mkPart("top","Wieniec górny","top", matSide, W, D));
  if (m.has?.bottom) p.push(mkPart("bottom","Wieniec dolny","bottom", matSide, W, D));
  if (m.has?.back && m.back?.enabled) p.push(mkPart("back","Plecy","back", m.back.mat||"hdf3", W, H));

  // segments (ALL / L / M / R)
  // positions are inside inner width (between pos.L and pos.R)
  const innerW = Math.max(10, W - (m.pos?.L||0) - (m.pos?.R||0));
  const clampX = (x)=> clamp(Math.round(num(x,0)), 1, innerW-1);

  let aOn = !!m.midA.enabled;
  let bOn = !!m.midB.enabled;

  const aX = aOn ? clampX(m.midA.x) : null;
  const bX = bOn ? clampX(m.midB.x) : null;

  // sort mids if both enabled
  let x1 = aX, x2 = bX;
  let mid1 = "midA", mid2 = "midB";
  if (aOn && bOn && x2 < x1){
    [x1,x2] = [x2,x1];
    [mid1, mid2] = [mid2, mid1];
  }

  const segs = [];
  if (!aOn && !bOn){
    segs.push({ key:"ALL", xL:0, xR:innerW });
  } else if ((aOn && !bOn) || (!aOn && bOn)){
    const x = aOn ? aX : bX;
    segs.push({ key:"L", xL:0, xR:x });
    segs.push({ key:"R", xL:x, xR:innerW });
  } else {
    segs.push({ key:"L", xL:0, xR:x1 });
    segs.push({ key:"M", xL:x1, xR:x2 });
    segs.push({ key:"R", xL:x2, xR:innerW });
  }

  // mids as parts with offT/offB
  const addMid = (idLabel, mm)=>{
    const offT = Math.max(0, Math.round(num(mm.offT,0)));
    const offB = Math.max(0, Math.round(num(mm.offB,0)));
    const midH = Math.max(10, H - offT - offB);
    p.push(mkPart(idLabel, `Pion ${idLabel}`, "mid", mm.mat||matSide, D, midH, { offT, offB, x: mm.x }));
  };

  if (aOn && bOn){
    addMid(mid1, m[mid1]);
    addMid(mid2, m[mid2]);
  } else {
    if (aOn) addMid("midA", m.midA);
    if (bOn) addMid("midB", m.midB);
  }

  // shelves: create in selected segment; if ALL => full opening (innerW)
  const shelfMat = matSide;
  const shelfYs = Array.isArray(m.shelves.autoY) ? m.shelves.autoY : [];
  const segKey = String(m.shelves.seg||"ALL").toUpperCase();

  const pickSeg = (k)=>{
    if (k==="ALL") return { key:"ALL", xL:0, xR:innerW };
    return segs.find(s=>s.key===k) || { key:"ALL", xL:0, xR:innerW };
  };
  const useSeg = pickSeg(segKey);

  shelfYs.forEach((y, idx)=>{
    const segW = Math.max(10, useSeg.xR - useSeg.xL);
    p.push(mkPart(`s_auto_${idx}`, `Półka auto #${idx+1} (${useSeg.key})`, "shelf", shelfMat, segW, D, { shelfY:y, seg:useSeg.key, xL:useSeg.xL, xR:useSeg.xR }));
  });

  // extras shelves in same segment by default
  const extras = Array.isArray(m.shelves.extra) ? m.shelves.extra : [];
  extras.forEach((it, idx)=>{
    const segW = Math.max(10, useSeg.xR - useSeg.xL);
    p.push(mkPart(it.id||(`s_ex_${idx}`), `Półka extra (${useSeg.key})`, "shelf", shelfMat, segW, D, { shelfY:it.y, seg:useSeg.key, xL:useSeg.xL, xR:useSeg.xR }));
  });

  state.parts = p;
  if (!state.selected || !state.parts.some(x=>x.id===state.selected)){
    state.selected = state.parts[0]?.id || null;
  }
}
