/* The deck replay page. Everything it needs is in the JSON block the page embeds; see
   provette/view/README.md for what the data means. No library, no network. */
(function () {
  'use strict';

  var D = JSON.parse(document.getElementById('provette-data').textContent);
  var N = D.events.length;
  var CE = D.cache_every || 50;
  var SVG = 'http://www.w3.org/2000/svg';

  // ------------------------------------------------------------------------------------
  // State: the wells, the tip racks and the tips, rebuilt by applying deltas
  // ------------------------------------------------------------------------------------

  function initialState() {
    var wells = new Map();
    Object.keys(D.initial).forEach(function (k) { wells.set(+k, D.initial[k]); });
    return { wells: wells, racks: new Map(), tips: new Map() };
  }
  function cloneState(s) {
    return { wells: new Map(s.wells), racks: new Map(s.racks), tips: new Map(s.tips) };
  }
  function apply(s, delta) {
    if (!delta) return;
    if (delta.wells) Object.keys(delta.wells).forEach(function (k) { s.wells.set(+k, delta.wells[k]); });
    if (delta.racks) delta.racks.forEach(function (row) { s.racks.set(row[0], row[1]); });
    if (delta.tips) Object.keys(delta.tips).forEach(function (k) { s.tips.set(+k, delta.tips[k]); });
  }
  var cache = [initialState()]; // cache[j] is the state at position j * CE
  function stateAt(p) {
    // Position p means events 0 .. p-1 have happened.
    var j = Math.floor(p / CE);
    while (cache.length <= j) {
      var s = cloneState(cache[cache.length - 1]);
      var from = (cache.length - 1) * CE;
      for (var i = from; i < from + CE && i < N; i++) apply(s, D.deltas[i]);
      cache.push(s);
    }
    var out = cloneState(cache[j]);
    for (var k = j * CE; k < p; k++) apply(out, D.deltas[k]);
    return out;
  }

  // ------------------------------------------------------------------------------------
  // Lookups
  // ------------------------------------------------------------------------------------

  var origins = D.origins;
  var wellIndex = new Map(); // "labware_id|well" -> index
  var wellInfo = [];         // index -> {lw, name}
  var labwareById = {};
  D.deck.labware.forEach(function (lw) { labwareById[lw.id] = lw; });
  D.wells.forEach(function (row, i) {
    var cut = row.lastIndexOf('[');
    var id = row.slice(0, cut), name = row.slice(cut + 1, -1);
    wellIndex.set(id + '|' + name, i);
    wellInfo[i] = { lw: labwareById[id] || null, name: name, id: id };
  });
  function indexOf(lwId, name) { var k = wellIndex.get(lwId + '|' + name); return k === undefined ? -1 : k; }
  function wellWords(i) {
    var w = wellInfo[i];
    if (!w) return 'a well';
    if (!w.lw) return w.name + ' of ' + w.id;
    if (w.lw.is_trash) return 'the trash';
    return w.lw.kind + ' ' + w.name + ' in slot ' + w.lw.slot;
  }
  function ul(v) {
    if (v === null || v === undefined) return 'an unknown amount';
    var r = Math.round(v * 100) / 100;
    return r + ' µl';
  }
  function clock(t) {
    var m = Math.floor(t / 60), s = Math.floor(t % 60);
    return m + ':' + (s < 10 ? '0' : '') + s;
  }

  // ------------------------------------------------------------------------------------
  // Drawing a labware: once for the deck, once more for the close-up
  // ------------------------------------------------------------------------------------

  function el(tag, attrs, parent) {
    var e = document.createElementNS(SVG, tag);
    if (attrs) Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); });
    if (parent) parent.appendChild(e);
    return e;
  }
  function wellGeom(w) {
    if (w.shape === 'circular') { var d = w.d || 5; return { cx: w.x, w: d, h: d, round: true }; }
    return { cx: w.x, w: w.w || 5, h: w.h || 5, round: false };
  }

  // Draws labware `lw` into `parent` with its corner at (0,0) in the labware's own mm, y down.
  // Returns the per-well handles the fills are drawn into.
  function makeLabware(lw, parent, prefix, defs) {
    var g = el('g', { 'class': 'labware' + (lw.is_tiprack ? ' tiprack' : '') + (lw.is_trash ? ' trash' : '') }, parent);
    el('rect', { x: 0, y: 0, width: lw.w, height: lw.h, rx: 2, 'class': 'lw-body' }, g);
    var label = el('text', { x: 3, y: 5.2, 'class': 'lw-label' }, g);
    var name = lw.is_trash ? 'Trash' : lw.name;
    if (name.length > 42) name = name.slice(0, 40) + '…'; // the full name is in the table below
    var labelText = lw.slot + '  ' + name;
    label.textContent = labelText;
    if (!lw.measured && !lw.is_trash) {
      var note = el('text', { x: 3, y: lw.h - 2, 'class': 'lw-note' }, g);
      note.textContent = 'well positions are a guess: no definition matched';
    }
    var handles = {};
    Object.keys(lw.wells).forEach(function (name) {
      var w = lw.wells[name], gm = wellGeom(w);
      var cx = w.x, cy = lw.h - w.y;
      var x0 = cx - gm.w / 2, y0 = cy - gm.h / 2;
      var wg = el('g', { 'class': 'well', 'data-w': indexOf(lw.id, name) }, g);
      var idx = indexOf(lw.id, name);
      var shapeAttrs = gm.round
        ? { cx: cx, cy: cy, r: gm.w / 2 }
        : { x: x0, y: y0, width: gm.w, height: gm.h, rx: 0.6 };
      var tag = gm.round ? 'circle' : 'rect';
      el(tag, Object.assign({ 'class': 'well-base' }, shapeAttrs), wg);
      var clipId = prefix + '-clip-' + lw.slot + '-' + name;
      var clip = el('clipPath', { id: clipId }, defs);
      el(tag, shapeAttrs, clip);
      var fill = el('g', { 'clip-path': 'url(#' + clipId + ')', 'class': 'well-fill' }, wg);
      var outline = el(tag, Object.assign({ 'class': 'well-outline' }, shapeAttrs), wg);
      handles[name] = { g: wg, fill: fill, outline: outline, idx: idx, x0: x0, y0: y0, w: gm.w, h: gm.h, cx: cx, cy: cy, max: w.max || 0 };
      if (lw.is_tiprack) drawTip(handles[name], 'fresh');
      if (idx >= 0) {
        wg.addEventListener('mousemove', function (ev) { showTip(ev, idx); });
        wg.addEventListener('mouseleave', hideTip);
      }
    });
    g.appendChild(label); // over the wells: a label grown to be readable must not hide under them
    return { lw: lw, g: g, wells: handles, label: label, labelText: labelText };
  }

  function clear(node) { while (node.firstChild) node.removeChild(node.firstChild); }

  // A well's contents: bands stacked from the bottom, carry-over as hatched stripes.
  function drawWell(h, row) {
    clear(h.fill);
    h.g.classList.toggle('empty', !row);
    if (!row) return;
    var vol = row[0], minVol = row[1], bands = row[2];
    var frac;
    if (vol === null) frac = h.max > 0 && minVol > 0 ? Math.min(1, minVol / h.max) : 0.35;
    else frac = h.max > 0 ? Math.min(1, vol / h.max) : (vol > 0 ? 0.5 : 0);
    var bulk = bands.filter(function (b) { return b[2] === 0; });
    var carry = bands.filter(function (b) { return b[2] === 1; });
    var known = bulk.reduce(function (a, b) { return a + (b[1] === null ? 0 : b[1]); }, 0);
    var unknownCount = bulk.filter(function (b) { return b[1] === null; }).length;
    var fillH = h.h * frac;
    var y = h.y0 + h.h; // the bottom
    var unit = unknownCount ? (known > 0 ? known / bulk.length : 1) : 0;
    var total = known + unit * unknownCount;
    if (bulk.length && fillH > 0) {
      bulk.forEach(function (b) {
        var weight = b[1] === null ? unit : b[1];
        var bh = total > 0 ? fillH * weight / total : fillH / bulk.length;
        y -= bh;
        var r = el('rect', { x: h.x0, y: y, width: h.w, height: bh, fill: origins[b[0]].colour }, h.fill);
        if (!b[3]) r.setAttribute('opacity', '0.45');
        if (b[1] === null) r.setAttribute('class', 'unknown-amount');
      });
    }
    if (vol === null) el('rect', { x: h.x0, y: h.y0, width: h.w, height: h.h, 'class': 'unknown-volume' }, h.fill);
    if (carry.length) {
      var top = Math.max(fillH, h.h * 0.3);
      var sw = h.w / carry.length;
      carry.forEach(function (b, k) {
        var r = el('rect', { x: h.x0 + k * sw, y: h.y0 + h.h - top, width: sw, height: top, fill: 'url(#hatch-' + b[0] + ')' }, h.fill);
        if (!b[3]) r.setAttribute('opacity', '0.5');
      });
    }
  }

  // A tip-rack position: fresh, in use (empty spot), parked (dirty tip back) or gone.
  function drawTip(h, status) {
    clear(h.fill);
    h.g.setAttribute('data-tip', status);
    if (status === 'fresh' || status === 'parked') {
      el('rect', { x: h.x0, y: h.y0, width: h.w, height: h.h, 'class': 'tip-' + status }, h.fill);
    }
  }

  // The pipette's tip, drawn above a well, with its residue as bands. `scale` shrinks it when
  // eight tips sit 9 mm apart, so they do not cover each other.
  function drawPipetteTip(parent, x, y, scale, tipRow, label) {
    var H = 14 * scale, W = 5 * scale, top = y - 2.5 * scale;
    var g = el('g', { 'class': 'pipette-tip' }, parent);
    var pts = [[x - W / 2, top - H], [x + W / 2, top - H], [x + W / 6, top], [x - W / 6, top]];
    var poly = pts.map(function (p) { return p.join(','); }).join(' ');
    el('polygon', { points: poly, 'class': 'tip-body' }, g);
    var clipId = 'tipclip-' + Math.round(x * 100) + '-' + Math.round(y * 100) + '-' + label;
    var defs = el('defs', {}, g);
    el('polygon', { points: poly }, el('clipPath', { id: clipId }, defs));
    var inner = el('g', { 'clip-path': 'url(#' + clipId + ')' }, g);
    var res = tipRow || [];
    if (res.length) {
      var bh = H / res.length;
      res.forEach(function (r, k) {
        var rect = el('rect', { x: x - W / 2, y: top - H + k * bh, width: W, height: bh, fill: origins[r[0]].colour }, inner);
        if (!r[1]) rect.setAttribute('opacity', '0.45');
      });
    }
    el('polygon', { points: poly, 'class': 'tip-edge' }, g);
    if (label) {  // beside the tip, so it never covers the labware's own label
      var t = el('text', { x: x + W / 2 + 0.8 * scale, y: top - H / 2 + 1.4 * scale, 'class': 'tip-label' }, g);
      t.textContent = label;
    }
    return g;
  }

  // ------------------------------------------------------------------------------------
  // The deck
  // ------------------------------------------------------------------------------------

  var deckSvg = document.getElementById('deck');
  var W = D.deck.width, H = D.deck.height;
  var MARGIN = 4;
  deckSvg.setAttribute('viewBox', (-MARGIN) + ' ' + (-MARGIN) + ' ' + (W + 2 * MARGIN) + ' ' + (H + 2 * MARGIN));
  var deckDefs = el('defs', {}, deckSvg);
  origins.forEach(function (o, i) {
    var p = el('pattern', { id: 'hatch-' + i, width: 1.6, height: 1.6, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' }, deckDefs);
    el('rect', { x: 0, y: 0, width: 0.7, height: 1.6, fill: o.colour }, p);
  });
  var parkedPattern = el('pattern', { id: 'hatch-parked', width: 1.2, height: 1.2, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' }, deckDefs);
  el('rect', { x: 0, y: 0, width: 0.5, height: 1.2, fill: '#8a6d00' }, parkedPattern);

  var slotsLayer = el('g', { 'class': 'slots' }, deckSvg);
  D.deck.slots.forEach(function (s) {
    var g = el('g', { transform: 'translate(' + s.x + ',' + (H - s.y - s.height) + ')' }, slotsLayer);
    el('rect', { x: 0, y: 0, width: s.width, height: s.height, 'class': 'slot' }, g);
    var t = el('text', { x: s.width / 2, y: s.height / 2 + 6, 'class': 'slot-number', 'text-anchor': 'middle' }, g);
    t.textContent = s.id;
  });
  var labwareLayer = el('g', { 'class': 'labware-layer' }, deckSvg);
  var tipsLayer = el('g', { 'class': 'tips-layer' }, deckSvg);

  var deckInstances = {}; // labware id -> instance
  var placement = {};     // labware id -> {x, y} of its top-left corner on the deck svg
  D.deck.labware.forEach(function (lw) {
    // The labware's corner sits at the slot's corner plus its own offset; the trash (a bin that
    // rises above slot 12) is drawn as the box of its slot.
    var x = lw.slot_x + lw.ox, y = H - (lw.slot_y + lw.oy + lw.h);
    placement[lw.id] = { x: x, y: y };
    var holder = el('g', { transform: 'translate(' + x + ',' + y + ')' }, labwareLayer);
    var inst = makeLabware(lw, holder, 'd', deckDefs);
    inst.g.addEventListener('click', function () { pinCloseup(lw.id); });
    deckInstances[lw.id] = inst;
  });

  // The labware labels are drawn in the deck's own units (5 mm, about 8 px in the product's
  // frame), so a page may ask for a smallest size on screen: --label-min-px, 11 in compact
  // mode (replay.css). How many units that is depends on how wide the deck is drawn, so the
  // fit is redone on resize; a label the labware cannot hold at that size is cut short, and
  // the full name stays in the table below and the close-up's title.
  var LABEL_UNITS = 5, CHAR_EM = 0.58;
  function fitLabels() {
    var minPx = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--label-min-px')) || 0;
    var drawn = deckSvg.getBoundingClientRect().width;
    var unitsPerPx = drawn > 0 ? (W + 2 * MARGIN) / drawn : 0;
    var size = Math.max(LABEL_UNITS, minPx * unitsPerPx);
    Object.keys(deckInstances).forEach(function (id) {
      var inst = deckInstances[id], text = inst.labelText;
      var room = Math.floor((inst.lw.w - 6) / (size * CHAR_EM));
      if (text.length > room) text = text.slice(0, Math.max(room - 1, 1)) + '…';
      inst.label.setAttribute('font-size', size);
      inst.label.setAttribute('y', size + 1);
      inst.label.textContent = text;
    });
  }
  fitLabels();
  window.addEventListener('resize', fitLabels);

  // ------------------------------------------------------------------------------------
  // The close-up
  // ------------------------------------------------------------------------------------

  var closeSvg = document.getElementById('closeup');
  var closeDefs = el('defs', {}, closeSvg);
  var closeLayer = el('g', {}, closeSvg);
  var closeTips = el('g', {}, closeSvg);
  var closeInstance = null;
  var pinned = null;
  var follow = document.getElementById('follow');
  function showCloseup(lwId) {
    var lw = labwareById[lwId];
    if (!lw || (closeInstance && closeInstance.lw.id === lwId)) return;
    clear(closeLayer); clear(closeDefs); clear(closeTips);
    closeSvg.setAttribute('viewBox', '-1 -1 ' + (lw.w + 2) + ' ' + (lw.h + 2));
    closeInstance = makeLabware(lw, closeLayer, 'c', closeDefs);
    document.getElementById('closeup-title').textContent = 'Close-up: slot ' + lw.slot + ', ' + (lw.is_trash ? 'the trash' : lw.name);
    if (current) {
      Object.keys(closeInstance.wells).forEach(function (name) {
        var h = closeInstance.wells[name];
        if (h.idx < 0) return;
        if (lw.is_tiprack) drawTip(h, current.state.racks.get(h.idx) || 'fresh');
        else drawWell(h, current.state.wells.get(h.idx) || null);
      });
      applyHighlights();
      drawTips();
    }
  }
  function pinCloseup(lwId) { pinned = lwId; follow.checked = false; showCloseup(lwId); }

  // ------------------------------------------------------------------------------------
  // Rendering a position
  // ------------------------------------------------------------------------------------

  var current = null;   // {pos, state}
  var renderedWells = new Map(), renderedRacks = new Map();
  var readout = document.getElementById('readout');
  var stepLabel = document.getElementById('step-label');
  var tipLine = document.getElementById('tip-line');
  var slider = document.getElementById('slider');
  slider.max = N;

  function goTo(p) {
    p = Math.max(0, Math.min(N, p));
    var state;
    if (current && p === current.pos + 1) { state = current.state; apply(state, D.deltas[p - 1]); }
    else state = stateAt(p);
    current = { pos: p, state: state };
    slider.value = p;

    // Wells whose row changed since the last render.
    state.wells.forEach(function (row, idx) {
      if (renderedWells.get(idx) !== row) { renderedWells.set(idx, row); paintWell(idx, row); }
    });
    renderedWells.forEach(function (row, idx) {
      if (!state.wells.has(idx)) { renderedWells.delete(idx); paintWell(idx, null); }
    });
    state.racks.forEach(function (status, idx) {
      if (renderedRacks.get(idx) !== status) { renderedRacks.set(idx, status); paintRack(idx, status); }
    });
    renderedRacks.forEach(function (status, idx) {
      if (!state.racks.has(idx)) { renderedRacks.delete(idx); paintRack(idx, 'fresh'); }
    });

    var ev = p > 0 ? D.events[p - 1] : null;
    if (ev) {
      stepLabel.textContent = 'Step ' + p + ' of ' + N + (ev.line !== null ? ', line ' + ev.line : '') + ', at ' + clock(ev.t);
      readout.textContent = ev.text;
      markLine(ev.line);
      if (follow.checked && ev.targets.length) {
        var w = wellInfo[ev.targets[0][1]];
        if (w && w.lw) showCloseup(w.lw.id);
      }
      tipLine.textContent = tipWords(ev, state);
    } else {
      stepLabel.textContent = 'Before the run starts';
      readout.textContent = 'The deck as the protocol loads it. Press play, or use the arrow keys.';
      markLine(null);
      tipLine.textContent = '';
    }
    drawTips();
    playButton.textContent = playing ? 'Pause' : 'Play';
  }

  function eachInstance(idx, fn) {
    var w = wellInfo[idx];
    if (!w || !w.lw) return;
    var inst = deckInstances[w.lw.id];
    if (inst && inst.wells[w.name]) fn(inst.wells[w.name], inst);
    if (closeInstance && closeInstance.lw.id === w.lw.id && closeInstance.wells[w.name]) fn(closeInstance.wells[w.name], closeInstance);
  }
  function paintWell(idx, row) {
    var w = wellInfo[idx];
    if (w && w.lw && w.lw.is_tiprack) return;
    eachInstance(idx, function (h) { drawWell(h, row); });
  }
  function paintRack(idx, status) {
    eachInstance(idx, function (h) { drawTip(h, status); });
  }

  function tipWords(ev, state) {
    var parts = [];
    ev.targets.forEach(function (t, k) {
      if (t[0] === null) return;
      var res = state.tips.get(t[0]) || [];
      var name = wellInfo[t[0]] ? wellInfo[t[0]].name : '?';
      var names = res.map(function (r) { return origins[r[0]].name + (r[1] ? '' : ' (not certain)'); });
      var held = ev.held ? ev.held[k] : 0;
      parts.push('Tip ' + name + ' holds ' + ul(held) + (names.length ? ' and has touched: ' + names.join(', ') : ' and is clean') + '.');
    });
    if (ev.targets.length > 1 && parts.length > 1) return parts[0] + ' (' + parts.length + ' tips; the first is described.)';
    return parts.join(' ');
  }

  // The pipette's tips above the wells of the current event.
  function drawTips() {
    clear(tipsLayer); clear(closeTips);
    if (!current || current.pos === 0) return;
    var ev = D.events[current.pos - 1];
    var many = ev.targets.length > 1;
    ev.targets.forEach(function (t, k) {
      var tipIdx = t[0], wIdx = t[1];
      var w = wellInfo[wIdx];
      if (!w || !w.lw) return;
      var lw = w.lw, place = placement[lw.id];
      var geomW = lw.wells[w.name];
      var lx = geomW ? geomW.x : lw.w / 2, ly = geomW ? lw.h - geomW.y : lw.h / 2;
      var label = tipIdx === null ? '' : (wellInfo[tipIdx] ? wellInfo[tipIdx].name : '');
      if (many && k > 0 && k < ev.targets.length - 1) label = '';
      var tipRow = tipIdx === null ? null : current.state.tips.get(tipIdx);
      drawPipetteTip(tipsLayer, place.x + lx, place.y + ly, many ? 0.5 : 1, tipRow, label);
      if (closeInstance && closeInstance.lw.id === lw.id) drawPipetteTip(closeTips, lx, ly, many ? 0.35 : 0.5, tipRow, label);
    });
  }

  // ------------------------------------------------------------------------------------
  // The code panel
  // ------------------------------------------------------------------------------------

  var code = document.getElementById('code');
  var lineNodes = [];
  D.source.forEach(function (text, i) {
    var div = document.createElement('div');
    div.className = 'ln';
    var num = document.createElement('span'); num.className = 'num'; num.textContent = i + 1;
    var body = document.createElement('span'); body.className = 'src'; body.textContent = text;
    div.appendChild(num); div.appendChild(body);
    code.appendChild(div);
    lineNodes.push(div);
  });
  var currentLine = null, markedLine = null;
  function markLine(line) {
    if (currentLine !== null && lineNodes[currentLine - 1]) lineNodes[currentLine - 1].classList.remove('cur');
    currentLine = line;
    if (line !== null && lineNodes[line - 1]) {
      var node = lineNodes[line - 1];
      node.classList.add('cur');
      // Scroll the code panel only, never the page.
      code.scrollTop = node.offsetTop - code.clientHeight / 2;
    }
  }
  function markFindingLine(line) {
    if (markedLine !== null && lineNodes[markedLine - 1]) lineNodes[markedLine - 1].classList.remove('mark');
    markedLine = line;
    if (line !== null && lineNodes[line - 1]) lineNodes[line - 1].classList.add('mark');
  }

  // ------------------------------------------------------------------------------------
  // Findings and the plate map
  // ------------------------------------------------------------------------------------

  var highlighted = { wells: [], downstream: [] };
  function applyHighlights() {
    document.querySelectorAll('.well.hl, .well.hl2').forEach(function (n) { n.classList.remove('hl'); n.classList.remove('hl2'); });
    highlighted.wells.forEach(function (i) { eachInstance(i, function (h) { h.g.classList.add('hl'); }); });
    highlighted.downstream.forEach(function (i) { eachInstance(i, function (h) { h.g.classList.add('hl2'); }); });
  }
  var selected = null;
  function selectItem(node, wells, downstream, pos, line) {
    document.querySelectorAll('.finding.selected').forEach(function (n) { n.classList.remove('selected'); });
    if (selected === node) { selected = null; highlighted = { wells: [], downstream: [] }; applyHighlights(); markFindingLine(null); return; }
    selected = node;
    node.classList.add('selected');
    highlighted = { wells: wells, downstream: downstream };
    stop();
    goTo(pos);
    applyHighlights();
    markFindingLine(line);
  }

  var list = document.getElementById('findings');
  function addItem(cls, head, body, onclick) {
    var li = document.createElement('li');
    li.className = 'finding ' + cls;
    var h = document.createElement('div'); h.className = 'f-head'; h.textContent = head;
    li.appendChild(h);
    body.forEach(function (b) {
      var p = document.createElement('div'); p.className = b[0]; p.textContent = b[1]; li.appendChild(p);
    });
    li.addEventListener('click', function () { onclick(li); });
    list.appendChild(li);
    return li;
  }
  D.findings.forEach(function (f, n) {
    var sure = f.certain ? '' : ' (not certain)';
    var body = [['f-text', f.explanation], ['f-fix', 'Fix: ' + f.fix]];
    if (f.downstream && f.downstream.count) body.push(['f-note', 'Also reached ' + f.downstream.count + ' other well' + (f.downstream.count > 1 ? 's' : '') + '.']);
    body.push(['f-note', 'Click to jump to step ' + (f.root_event + 1) + (f.line !== null ? ', line ' + f.line : '') + '.']);
    addItem(f.severity, (n + 1) + '. ' + f.severity.toUpperCase() + sure + ': ' + f.title, body, function (li) {
      selectItem(li, f.well_index, f.downstream_index, f.root_event === null ? N : f.root_event + 1, f.line);
    });
  });
  if (D.verify && D.verify.intent && D.verify.intent.mismatches.length) {
    var head = document.createElement('li'); head.className = 'f-section'; head.textContent = 'Wells that do not match the plate map (at the end of the run)';
    list.appendChild(head);
    D.verify.intent.mismatches.forEach(function (m) {
      var body = m.text.slice(1).map(function (t) { return ['f-text', t]; });
      addItem('mismatch', m.text[0], body, function (li) {
        selectItem(li, m.well_index === null ? [] : [m.well_index], [], N, null);
      });
    });
  }
  if (!list.children.length) {
    var none = document.createElement('li'); none.className = 'f-section'; none.textContent = 'Nothing to show: no findings' + (D.verify ? ', and every well matches the plate map' : '') + '.';
    list.appendChild(none);
  }

  // ------------------------------------------------------------------------------------
  // The legend
  // ------------------------------------------------------------------------------------

  var legend = document.getElementById('legend');
  origins.forEach(function (o, i) {
    var li = document.createElement('li');
    var sw = document.createElement('span'); sw.className = 'swatch'; sw.style.background = o.colour;
    li.appendChild(sw);
    var t = document.createElement('span');
    t.textContent = o.name + (o.declared ? ' (' + o.place + (o.volume !== null ? ', ' + ul(o.volume) + ' declared' : '') + ')' : ' (not declared in the protocol)');
    li.appendChild(t);
    legend.appendChild(li);
  });

  // ------------------------------------------------------------------------------------
  // Tooltip
  // ------------------------------------------------------------------------------------

  var tip = document.getElementById('tooltip');
  function wellText(idx) {
    var w = wellInfo[idx];
    var head = wellWords(idx).replace(/^\w/, function (c) { return c.toUpperCase(); });
    if (w && w.lw && w.lw.is_tiprack) {
      var st = current ? (current.state.racks.get(idx) || 'fresh') : 'fresh';
      var words = { fresh: 'a fresh tip', in_use: 'the tip is on the pipette', parked: 'a used tip, put back', gone: 'the tip was used and thrown away' };
      return head + ': ' + words[st] + '.';
    }
    var row = current ? current.state.wells.get(idx) : null;
    if (!row) return head + ': empty.';
    var parts = [], carry = [];
    row[2].forEach(function (b) {
      var o = origins[b[0]];
      var sure = b[3] ? '' : ' (not certain)';
      if (b[2] === 0) parts.push((b[1] === null ? 'some' : (b[1] === 0 ? 'a trace of' : ul(b[1]) + ' of')) + ' ' + o.name + sure);
      else carry.push(o.name + sure);
    });
    var text = head + ': ' + (row[0] === null ? 'at least ' + ul(row[1]) : ul(row[0]));
    if (parts.length) text += ' - ' + parts.join(', ');
    if (carry.length) text += '. Carry-over on a tip brought: ' + carry.join('; ');
    return text + '.';
  }
  function showTip(ev, idx) {
    tip.textContent = wellText(idx);
    tip.style.display = 'block';
    var x = ev.clientX + 14, y = ev.clientY + 14;
    if (x + tip.offsetWidth > window.innerWidth - 8) x = ev.clientX - tip.offsetWidth - 8;
    if (y + tip.offsetHeight > window.innerHeight - 8) y = ev.clientY - tip.offsetHeight - 8;
    tip.style.left = x + 'px'; tip.style.top = y + 'px';
  }
  function hideTip() { tip.style.display = 'none'; }

  // ------------------------------------------------------------------------------------
  // Controls
  // ------------------------------------------------------------------------------------

  var playing = false, timer = null;
  var playButton = document.getElementById('play');
  var speed = document.getElementById('speed');
  function tick() {
    if (!current || current.pos >= N) { stop(); return; }
    goTo(current.pos + 1);
  }
  function start() {
    if (current && current.pos >= N) goTo(0);
    playing = true;
    playButton.textContent = 'Pause';
    timer = setInterval(tick, 1000 / (+speed.value));
  }
  function stop() {
    playing = false;
    playButton.textContent = 'Play';
    if (timer) { clearInterval(timer); timer = null; }
  }
  playButton.addEventListener('click', function () { if (playing) stop(); else start(); });
  speed.addEventListener('change', function () { if (playing) { stop(); start(); } });
  document.getElementById('back').addEventListener('click', function () { stop(); goTo(current.pos - 1); });
  document.getElementById('forward').addEventListener('click', function () { stop(); goTo(current.pos + 1); });
  document.getElementById('first').addEventListener('click', function () { stop(); goTo(0); });
  document.getElementById('last').addEventListener('click', function () { stop(); goTo(N); });
  slider.addEventListener('input', function () { stop(); goTo(+slider.value); });
  follow.addEventListener('change', function () { if (follow.checked) { pinned = null; goTo(current.pos); } });
  document.addEventListener('keydown', function (ev) {
    if (ev.target && (ev.target.tagName === 'INPUT' || ev.target.tagName === 'SELECT')) { if (ev.key === ' ') { ev.preventDefault(); } else return; }
    if (ev.key === 'ArrowRight') { stop(); goTo(current.pos + 1); ev.preventDefault(); }
    else if (ev.key === 'ArrowLeft') { stop(); goTo(current.pos - 1); ev.preventDefault(); }
    else if (ev.key === 'Home') { stop(); goTo(0); ev.preventDefault(); }
    else if (ev.key === 'End') { stop(); goTo(N); ev.preventDefault(); }
    else if (ev.key === ' ') { if (playing) stop(); else start(); ev.preventDefault(); }
  });

  // First paint. The close-up starts on the labware of the first event, or the first labware.
  goTo(0);
  var firstTarget = D.events.length && D.events[0].targets.length ? wellInfo[D.events[0].targets[0][1]] : null;
  showCloseup(firstTarget && firstTarget.lw ? firstTarget.lw.id : (D.deck.labware[0] ? D.deck.labware[0].id : null));

  // "#step=12" opens at a step; "#finding=1" opens on a finding, as clicking it would.
  var hash = /^#(step|finding)=(\d+)$/.exec(window.location.hash || '');
  if (hash && hash[1] === 'step') goTo(+hash[2]);
  else if (hash && hash[1] === 'finding') {
    var item = list.querySelectorAll('.finding')[+hash[2] - 1];
    if (item) item.click();
  }
  // In a frame (the product's page), say how tall the page is: once its content is laid
  // out, again on resize, and after anything that changes its height (a taller close-up, a
  // prep sheet unfolded), so the frame is that tall and no height is guessed. The body's
  // own height, not the document's scroll height: that one never shrinks below the frame.
  var lastHeight = 0, heightQueued = false;
  function postHeight() {
    heightQueued = false;
    if (window.parent === window) return;
    var height = Math.ceil(document.body.getBoundingClientRect().height);
    if (!height || height === lastHeight) return;
    lastHeight = height;
    window.parent.postMessage({ type: 'provette:height', height: height }, '*');
  }
  function queueHeight() {
    if (heightQueued) return;
    heightQueued = true;
    window.requestAnimationFrame(postHeight);
  }
  window.addEventListener('resize', queueHeight);
  window.addEventListener('load', queueHeight);
  if (typeof ResizeObserver === 'function') new ResizeObserver(queueHeight).observe(document.body);
  queueHeight();

  window.provetteReplay = { goTo: goTo, stateAt: stateAt, data: D, fitLabels: fitLabels, postHeight: postHeight };
})();
