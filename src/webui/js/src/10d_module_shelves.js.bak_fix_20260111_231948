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

  
