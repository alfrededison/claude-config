// Input overlay for Playwright recordings: shows the pointer, click ripples, drag trails and
// pressed keys inside the page, so recordVideo captures them (Playwright's video has no cursor).
// Usage: await context.addInitScript({ path: `${os.homedir()}/.claude/tools/pw_input_overlay.js` });
// page.setContent() wipes the listeners (document.open), so after it also run
// await page.addScriptTag({ path: <same file> });
(() => {
  // Already installed and its listeners still alive? (a window flag would survive document.open)
  const probe = { hit: false };
  window.dispatchEvent(new CustomEvent('__pwOverlayPing', { detail: probe }));
  if (probe.hit) return;
  addEventListener('__pwOverlayPing', (e) => { e.detail.hit = true; });
  const Z = 2147483647;
  const mk = (css) => { const d = document.createElement('div'); d.style.cssText = `position:fixed;pointer-events:none;z-index:${Z};${css}`; return d; };
  const mount = (el) => (document.body || document.documentElement).appendChild(el);

  let cursor, keys, canvas, ctx, trail = null;
  const init = () => {
    if (cursor) return;
    cursor = mk('width:18px;height:18px;margin:-9px 0 0 -9px;border-radius:50%;background:rgba(255,200,0,.85);border:2px solid #222;left:-50px;top:-50px;transition:transform .08s');
    keys = mk('right:12px;bottom:12px;display:flex;gap:6px;font:600 16px system-ui,sans-serif');
    canvas = document.createElement('canvas');
    canvas.style.cssText = `position:fixed;inset:0;pointer-events:none;z-index:${Z - 1}`;
    const fit = () => { canvas.width = innerWidth; canvas.height = innerHeight; };
    fit(); addEventListener('resize', fit);
    ctx = canvas.getContext('2d');
    [canvas, cursor, keys].forEach(mount);
  };

  // Same look as the iOS/Android recorders (touch_markers.py): orange square per click, held 0.8 s.
  const ripple = (x, y) => {
    const r = mk(`left:${x}px;top:${y}px;width:44px;height:44px;margin:-22px 0 0 -22px;border:4px solid rgba(255,140,0,.95);box-sizing:border-box;transition:opacity .3s`);
    mount(r);
    setTimeout(() => { r.style.opacity = '0'; }, 800);
    setTimeout(() => r.remove(), 1150);
  };

  const ORANGE = 'rgba(255,140,0,.95)', WIDTH = 7;
  const stroke = (pts) => {
    ctx.strokeStyle = ORANGE; ctx.lineWidth = WIDTH; ctx.lineCap = ctx.lineJoin = 'round';
    ctx.beginPath(); pts.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1]))); ctx.stroke();
  };
  const arrowHead = (pts) => {
    const [ex, ey] = pts[pts.length - 1];
    // Direction from a point ~24px back along the path, so jitter at the end doesn't skew it.
    let k = pts.length - 2;
    while (k > 0 && Math.hypot(ex - pts[k][0], ey - pts[k][1]) < 24) k--;
    const ang = Math.atan2(ey - pts[k][1], ex - pts[k][0]), L = 22;
    ctx.fillStyle = ORANGE; ctx.beginPath(); ctx.moveTo(ex + Math.cos(ang) * 6, ey + Math.sin(ang) * 6);
    ctx.lineTo(ex - L * Math.cos(ang - 0.5), ey - L * Math.sin(ang - 0.5));
    ctx.lineTo(ex - L * Math.cos(ang + 0.5), ey - L * Math.sin(ang + 0.5)); ctx.fill();
  };

  const fadeTrail = (pts) => {
    let a = 1;
    const draw = () => { ctx.clearRect(0, 0, canvas.width, canvas.height); ctx.globalAlpha = a; stroke(pts); arrowHead(pts); };
    draw();
    const tick = () => {
      if (trail) return; // a new drag started; it clears the canvas
      a -= 0.06;
      if (a <= 0) { ctx.clearRect(0, 0, canvas.width, canvas.height); return; }
      draw();
      requestAnimationFrame(tick);
    };
    setTimeout(tick, 800);
  };

  const down = (x, y) => { init(); cursor.style.transform = 'scale(.7)'; ripple(x, y); trail = [[x, y]]; ctx.clearRect(0, 0, canvas.width, canvas.height); };
  const move = (x, y) => {
    init(); cursor.style.left = x + 'px'; cursor.style.top = y + 'px';
    if (!trail) return;
    const [px, py] = trail[trail.length - 1];
    trail.push([x, y]);
    ctx.globalAlpha = 1; stroke([[px, py], [x, y]]);
  };
  const up = () => {
    if (!cursor) return;
    cursor.style.transform = '';
    const pts = trail; trail = null;
    if (pts && pts.length > 2) fadeTrail(pts); else ctx.clearRect(0, 0, canvas.width, canvas.height);
  };

  const opt = { capture: true, passive: true };
  addEventListener('pointermove', (e) => move(e.clientX, e.clientY), opt);
  addEventListener('pointerdown', (e) => { move(e.clientX, e.clientY); down(e.clientX, e.clientY); }, opt);
  addEventListener('pointerup', up, opt);
  addEventListener('pointercancel', up, opt);

  const NAMES = { ' ': 'Space', ArrowLeft: '←', ArrowRight: '→', ArrowUp: '↑', ArrowDown: '↓', Backspace: '⌫', Enter: '↵', Escape: 'Esc', Tab: '⇥' };
  addEventListener('keydown', (e) => {
    if (['Shift', 'Control', 'Alt', 'Meta'].includes(e.key)) return;
    init();
    const mods = [e.ctrlKey && 'Ctrl', e.altKey && 'Alt', e.metaKey && '⌘', e.shiftKey && e.key.length > 1 && 'Shift'].filter(Boolean);
    const b = mk('position:static;padding:4px 10px;border-radius:8px;background:rgba(20,20,20,.85);color:#fff;border:2px solid #ffb300;transition:opacity .4s');
    b.textContent = [...mods, NAMES[e.key] || e.key].join('+');
    keys.appendChild(b);
    while (keys.children.length > 8) keys.firstChild.remove();
    setTimeout(() => { b.style.opacity = '0'; setTimeout(() => b.remove(), 400); }, 1500);
  }, opt);
})();
