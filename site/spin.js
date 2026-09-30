// One cube, slowly rotating. Drag it to turn it yourself.
// Frames come from `blender/generate.py --turntable N`, exported by blender/export_site.py.
(async function () {
  const canvas = document.getElementById("cube");
  const ctx = canvas.getContext("2d");
  let meta;
  try {
    meta = await (await fetch("turntable/frames.json")).json();
  } catch (e) {
    // no turntable rendered yet: show a still of #0044 instead
    const still = new Image();
    still.onload = () => ctx.drawImage(still, 0, 0, canvas.width, canvas.height);
    still.src = "pile/0044.webp";
    return;
  }
  const n = meta.count;
  const frames = new Array(n);
  let loaded = 0;
  await new Promise((resolve) => {
    for (let i = 0; i < n; i++) {
      const img = new Image();
      img.decoding = "async";
      img.onload = img.onerror = () => {
        loaded++;
        if (i === 0 || loaded === n) resolve();
      };
      img.src = `turntable/${meta.prefix}${String(i + 1).padStart(4, "0")}.${meta.ext}`;
      frames[i] = img;
    }
  });

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const turnSeconds = meta.seconds || 24;
  let pos = 0;           // in frames, fractional
  let vel = reduced ? 0 : n / turnSeconds;
  let dragging = false;
  let lastX = 0;
  let lastT = performance.now();
  let fling = 0;

  function draw() {
    const a = ((Math.floor(pos) % n) + n) % n;
    const b = (a + 1) % n;
    const f = pos - Math.floor(pos);
    ctx.globalAlpha = 1;
    if (frames[a].complete && frames[a].naturalWidth) ctx.drawImage(frames[a], 0, 0, canvas.width, canvas.height);
    if (f > 0.01 && frames[b].complete && frames[b].naturalWidth) {
      ctx.globalAlpha = f;
      ctx.drawImage(frames[b], 0, 0, canvas.width, canvas.height);
    }
  }

  function tick(t) {
    const dt = Math.min(0.05, (t - lastT) / 1000);
    lastT = t;
    if (!dragging) {
      if (Math.abs(fling) > 0.01) {
        pos += fling * dt;
        fling *= Math.pow(0.04, dt);
      }
      pos += vel * dt;
    }
    draw();
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);

  const perPixel = () => n / canvas.getBoundingClientRect().width;
  canvas.addEventListener("pointerdown", (e) => {
    dragging = true;
    lastX = e.clientX;
    fling = 0;
    canvas.setPointerCapture(e.pointerId);
    canvas.classList.add("dragging");
  });
  canvas.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    const dx = e.clientX - lastX;
    lastX = e.clientX;
    pos -= dx * perPixel() * 0.9;
    fling = -dx * perPixel() * 40;
  });
  const up = () => {
    dragging = false;
    canvas.classList.remove("dragging");
  };
  canvas.addEventListener("pointerup", up);
  canvas.addEventListener("pointercancel", up);
})();
