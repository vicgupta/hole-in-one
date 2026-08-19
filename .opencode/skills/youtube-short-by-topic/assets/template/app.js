/* ═══════════════════════════════════════════════════════════
   Short player — two modes off one timeline.

   preview  : audio drives everything, like a normal deck player.
   render   : ?render=1 — no audio, no chrome. capture_frames.py calls
              __seek(scene, t) and screenshots. Animations are frozen at
              an exact offset via a negative animation-delay on a paused
              animation, so a mid-fade frame is reproducible rather than
              dependent on wall-clock timing.
   ═══════════════════════════════════════════════════════════ */

(() => {
  'use strict';

  const $  = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  const stage   = $('#stage');
  const player  = $('#player');
  const gate    = $('#gate');
  const capBox  = $('#captions');
  const capText = $('#captionText');
  const tLabel  = $('#t');
  const body    = document.body;

  const scenes = $$('.scene');
  const COUNT  = scenes.length;
  const ANIM   = 0.55;               // must match the .r animation duration

  const params   = new URLSearchParams(location.search);
  const RENDER   = params.has('render');
  let index      = 0;
  let started    = false;

  if (RENDER) body.classList.add('is-render');

  /* ── fit the stage to the viewport ───────────────────────── */
  // STAGE comes from data.js: [w, h] — 1080×1920 short, 1920×1080 deck.
  const [SW, SH] = (typeof STAGE !== 'undefined') ? STAGE : [1080, 1920];

  function fit() {
    // Render mode sizes the viewport to the stage exactly: scale 1.
    const scale = RENDER
      ? 1
      : Math.min(window.innerWidth / SW, (window.innerHeight - 90) / SH);
    stage.style.transform = `scale(${scale})`;
    const wrap = $('.stage-wrap');
    if (wrap) wrap.style.height = RENDER ? `${SH}px` : '';
  }
  window.addEventListener('resize', fit);
  fit();

  /* ── ticks ───────────────────────────────────────────────── */
  const ticks = $$('.tick i');

  /* ── reveal bookkeeping ──────────────────────────────────── */
  const reveals = i => $$('[data-at]', scenes[i])
    .map(el => ({ el, at: parseFloat(el.dataset.at) || 0 }));
  const highlights = i => $$('[data-hl-at]', scenes[i])
    .map(el => ({ el, at: parseFloat(el.dataset.hlAt) || 0 }));

  function resetScene(i) {
    reveals(i).forEach(({ el }) => {
      el.classList.remove('shown');
      el.style.animationDelay = '';
    });
    highlights(i).forEach(({ el }) => {
      el.classList.remove('on');
      el.style.animationDelay = '';
    });
  }

  /**
   * Put scene `i` into the exact visual state it should have at `t`
   * seconds into its narration track.
   */
  function syncScene(i, t, { freeze = RENDER } = {}) {
    const apply = (el, at, cls) => {
      const dt = t - at;
      if (dt < 0) {
        el.classList.remove(cls);
        el.style.animationDelay = '';
        return;
      }
      el.classList.add(cls);
      // Paused animation + negative delay = frame-exact freeze at `dt`.
      if (freeze) el.style.animationDelay = `-${Math.min(dt, ANIM + 0.01).toFixed(3)}s`;
    };
    reveals(i).forEach(({ el, at }) => apply(el, at, 'shown'));
    highlights(i).forEach(({ el, at }) => apply(el, at, 'on'));
  }

  /* ── navigation ──────────────────────────────────────────── */
  function go(i, { autoplay = false } = {}) {
    i = Math.max(0, Math.min(COUNT - 1, i));
    if (i !== index) resetScene(index);
    index = i;

    scenes.forEach((s, n) => s.classList.toggle('is-active', n === i));
    ticks.forEach((el, n) => { el.style.width = n < i ? '100%' : '0%'; });

    const data = SCENES[i];
    if (capText) capText.textContent = '';
    if (capBox) capBox.classList.remove('on');

    resetScene(i);
    if (player) {
      player.src = data.audio;
      player.currentTime = 0;
    }
    syncScene(i, 0.01);

    if (autoplay && !RENDER) play();
  }

  const play  = () => { started = true; player.play().catch(() => {}); };
  const pause = () => player.pause();

  /* ── preview playback ────────────────────────────────────── */
  if (!RENDER) {
    player.addEventListener('timeupdate', () => {
      const t = player.currentTime;
      const d = SCENES[index];
      syncScene(index, t, { freeze: false });
      ticks[index].style.width = `${Math.min(100, (t / d.duration) * 100)}%`;

      const before = SCENES.slice(0, index).reduce((a, s) => a + s.duration, 0);
      const tot = before + t;
      tLabel.textContent = `${tot.toFixed(1)}s / ${TOTAL_DURATION.toFixed(1)}s`;

      const cue = d.cues.find(c => t >= c.start && t < c.end);
      if (cue) {
        if (capText.textContent !== cue.text) capText.textContent = cue.text;
        capBox.classList.add('on');
      } else if (t >= d.duration - 0.3) {
        capBox.classList.remove('on');
      }
    });

    player.addEventListener('ended', () => {
      if (index < COUNT - 1) go(index + 1, { autoplay: true });
      else capBox.classList.remove('on');
    });

    $('#btnPlay').addEventListener('click', () => (player.paused ? play() : pause()));
    $('#btnPrev').addEventListener('click', () => go(index - 1, { autoplay: started }));
    $('#btnNext').addEventListener('click', () => go(index + 1, { autoplay: started }));
    $('#btnStart').addEventListener('click', () => {
      gate.classList.add('hide');
      go(0, { autoplay: true });
    });

    document.addEventListener('keydown', e => {
      if (e.metaKey || e.ctrlKey) return;
      if (!started && (e.key === ' ' || e.key === 'Enter')) {
        e.preventDefault(); $('#btnStart').click(); return;
      }
      if (e.key === ' ') { e.preventDefault(); $('#btnPlay').click(); }
      if (e.key === 'ArrowRight') $('#btnNext').click();
      if (e.key === 'ArrowLeft')  $('#btnPrev').click();
    });
  }

  /* ── render API ──────────────────────────────────────────── */
  window.__seek = (sceneIdx, t) => {
    if (sceneIdx !== index) {
      resetScene(index);
      index = Math.max(0, Math.min(COUNT - 1, sceneIdx));
      scenes.forEach((s, n) => s.classList.toggle('is-active', n === index));
    }
    const d = SCENES[index];
    ticks.forEach((el, n) => {
      el.style.width = n < index ? '100%'
        : n > index ? '0%'
        : `${Math.min(100, (t / d.duration) * 100)}%`;
    });
    syncScene(index, t, { freeze: true });

    // Captions are drawn here rather than burned in by ffmpeg — not every
    // ffmpeg build ships libass, and Chrome gives us the deck's own type.
    const cue = d.cues.find(c => t >= c.start && t < c.end);
    capText.textContent = cue ? cue.text : '';
    capBox.classList.toggle('on', Boolean(cue));
    return true;
  };
  window.__ready = true;
  window.__SCENES = () => SCENES.map(s => s.duration);

  /* ── boot ────────────────────────────────────────────────── */
  go(0);
  if (RENDER) window.__seek(0, 0.01);
  setTimeout(fit, 50);
})();
