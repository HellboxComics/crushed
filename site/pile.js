// The pile: every rendered block, then zoom until you find the pager.
(async function () {
  const grid = document.getElementById("grid");
  const dlg = document.getElementById("viewer");
  const stage = document.getElementById("stage");
  const full = document.getElementById("full");
  const title = document.getElementById("title");
  const desc = document.getElementById("desc");
  const traits = document.getElementById("traits");
  const RARE = new Set(["GOLD", "BIOHAZARD", "CLEAN", "BURNT", "SOAKED"]);

  const pile = await (await fetch("pile/pile.json")).json();
  document.getElementById("count").textContent = `${pile.length} OF 888`;

  pile.forEach((b, i) => {
    const t = document.createElement("button");
    t.className = "tile";
    t.setAttribute("aria-label", b.name);
    const img = document.createElement("img");
    img.loading = "lazy";
    img.decoding = "async";
    img.src = b.thumb;
    img.alt = b.name;
    const label = document.createElement("span");
    label.textContent = b.name;
    t.append(img, label);
    t.addEventListener("click", () => open(i));
    grid.appendChild(t);
  });

  let cur = 0;
  function open(i) {
    cur = (i + pile.length) % pile.length;
    const b = pile[cur];
    stage.classList.remove("zoomed");
    full.src = b.image;
    full.alt = b.name;
    title.textContent = b.name;
    desc.textContent = b.description;
    traits.innerHTML = "";
    for (const a of b.attributes) {
      const dt = document.createElement("dt");
      dt.textContent = a.trait_type;
      const dd = document.createElement("dd");
      dd.textContent = a.value;
      const one = a.trait_type === "One of One";
      const rare = one || (a.trait_type === "Condition" && RARE.has(a.value)) ||
        (a.trait_type === "Contaminant" && a.value !== "None") || a.trait_type === "Gilded";
      if (rare) dd.className = "rare";
      traits.append(dt, dd);
    }
    if (!dlg.open) dlg.showModal();
  }

  // click to zoom, move to look around
  function aim(e) {
    const r = stage.getBoundingClientRect();
    const x = ((e.clientX - r.left) / r.width) * 100;
    const y = ((e.clientY - r.top) / r.height) * 100;
    full.style.transformOrigin = `${x}% ${y}%`;
  }
  stage.addEventListener("click", (e) => {
    if (e.target.closest(".controls")) return;
    aim(e);
    stage.classList.toggle("zoomed");
  });
  stage.addEventListener("pointermove", (e) => {
    if (stage.classList.contains("zoomed")) aim(e);
  });

  document.getElementById("prev").addEventListener("click", () => open(cur - 1));
  document.getElementById("next").addEventListener("click", () => open(cur + 1));
  document.getElementById("close").addEventListener("click", () => dlg.close());
  document.addEventListener("keydown", (e) => {
    if (!dlg.open) return;
    if (e.key === "ArrowRight") open(cur + 1);
    if (e.key === "ArrowLeft") open(cur - 1);
  });
})();
