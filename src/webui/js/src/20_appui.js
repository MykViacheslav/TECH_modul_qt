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

  
