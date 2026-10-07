'use strict';

const {Plugin} = require('obsidian');
let core;
const NS = 'http://www.w3.org/2000/svg';
const element = (tag, attrs) => {
  const el = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, String(value));
  return el;
};

module.exports = class ProofRouting extends Plugin {
  onload() {
    const path = require('path').join(this.app.vault.adapter.basePath, this.manifest.dir, 'geometry-core.cjs');
    try {
      const resolved = window.require.resolve(path);
      delete window.require.cache[resolved];
    } catch (_) {
      // A first load may not have a cached module yet.
    }
    core = window.require(path);
    this.states = new Map();
    this.registerInterval(window.setInterval(() => this.tick(), 200));
    this.registerEvent(this.app.workspace.on('layout-change', () => this.tick(true)));
    this.tick(true);
  }

  signature(data) {
    return JSON.stringify({
      nodes: data.nodes.map((node) => [node.id, node.x, node.y, node.width, node.height]),
      edges: data.edges.map((edge) => [edge.id, edge.fromNode, edge.toNode, edge.label, edge.proofRoute]),
    });
  }

  tick(force = false) {
    const live = new Set(this.app.workspace.getLeavesOfType('canvas').map((leaf) => leaf.view.canvas));
    for (const [canvas, state] of this.states) {
      if (live.has(canvas)) continue;
      state.layer.remove();
      for (const [el, value] of state.native) el.style.visibility = value;
      this.states.delete(canvas);
    }
    for (const leaf of this.app.workspace.getLeavesOfType('canvas')) {
      const canvas = leaf.view.canvas;
      if (!canvas) continue;
      const data = canvas.getData();
      if (data.metadata?.proofRouting?.profile !== core.PROFILE) continue;
      let state = this.states.get(canvas);
      if (!state) {
        state = {signature: null, layer: element('g', {'data-proof-paths': core.PROFILE}), native: []};
        canvas.edgeContainerEl.appendChild(state.layer);
        this.states.set(canvas, state);
      }
      const signature = this.signature(data);
      if (force || signature !== state.signature) {
        state.layer.replaceChildren();
        this.draw(canvas, data, state);
        state.signature = signature;
      }
      for (const edge of canvas.edges.values()) {
        for (const el of [edge.lineGroupEl, edge.lineEndGroupEl, edge.labelElement?.el]) {
          if (!el) continue;
          if (!state.native.some((item) => item[0] === el)) state.native.push([el, el.style.visibility]);
          el.style.visibility = 'hidden';
        }
      }
    }
  }

  draw(canvas, data, state) {
    const initialRoutes = core.routes(data);
    const labelSpecs = this.measureLabels(initialRoutes, state.layer);
    const resolved = core.resolveLabels(initialRoutes, labelSpecs);
    for (const edge of resolved.routes) this.drawPath(canvas, edge, state.layer);
    const labelLayer = element('g', {'data-proof-labels': core.PROFILE});
    state.layer.append(labelLayer);
    const byEdge = new Map(resolved.routes.map((edge) => [edge.id, edge]));
    for (const spec of resolved.labels) {
      this.drawLabel(byEdge.get(spec.edgeId), spec, labelLayer);
    }
  }

  measureLabels(routes, layer) {
    const measureLayer = element('g', {visibility: 'hidden', 'pointer-events': 'none'});
    layer.append(measureLayer);
    const specs = [];
    for (const edge of routes) {
      if (!edge.label) continue;
      const text = element('text', {'font-size': 16});
      text.textContent = edge.label;
      measureLayer.append(text);
      const wide = /[\u1100-\u115F\u2E80-\uA4CF\uAC00-\uD7A3\uF900-\uFAFF\uFE10-\uFE6F\uFF01-\uFF60\uFFE0-\uFFE6]/;
      const fallback = [...edge.label].reduce((sum, char) => sum + (wide.test(char) ? 18 : 9), 0);
      const measured = Number(text.getComputedTextLength());
      const width = Math.max(80, (Number.isFinite(measured) && measured > 0 ? Math.ceil(measured) : fallback) + 16);
      specs.push({edgeId: edge.id, width});
    }
    measureLayer.remove();
    return specs;
  }

  drawPath(canvas, edge, layer) {
    const group = element('g', {'data-proof-edge': edge.id});
    const d = edge.path;
    const color = edge.color || '#6F7782';
    const hit = element('path', {d, fill: 'none', stroke: 'transparent', 'stroke-width': 16, 'pointer-events': 'stroke'});
    hit.addEventListener('click', (event) => canvas.edges.get(edge.id)?.onClick(event));
    hit.addEventListener('contextmenu', (event) => canvas.edges.get(edge.id)?.onContextMenu(event));
    const display = element('path', {
      d,
      fill: 'none',
      stroke: color,
      'stroke-width': 2,
      'marker-end': `url(#proof-arrow-${edge.id})`,
      'pointer-events': 'none',
    });
    const defs = element('defs', {});
    const marker = element('marker', {
      id: `proof-arrow-${edge.id}`,
      viewBox: '0 0 10 10',
      refX: 9.5,
      refY: 5,
      markerWidth: 7,
      markerHeight: 7,
      orient: 'auto',
    });
    const tip = element('path', {d: 'M0 0L10 5L0 10z', fill: color});
    marker.append(tip);
    defs.append(marker);
    group.append(defs, hit, display);
    layer.append(group);
  }

  drawLabel(edge, spec, layer) {
    const placement = spec.placement;
    const group = element('g', {'data-proof-label': edge.id});
    const text = element('text', {
      x: placement.x,
      y: placement.y,
      'text-anchor': 'middle',
      'dominant-baseline': 'middle',
      fill: 'var(--text-normal)',
      'font-size': 16,
    });
    text.textContent = edge.label;
    group.append(text);
    const back = element('rect', {
      x: placement.x - spec.width / 2,
      y: placement.rectY,
      width: spec.width,
      height: 28,
      rx: 4,
      fill: 'var(--background-primary)',
    });
    group.insertBefore(back, text);
    layer.append(group);
  }

  onunload() {
    for (const [canvas, state] of this.states) {
      state.layer.remove();
      for (const [el, value] of state.native) el.style.visibility = value;
      canvas.markViewportChanged();
    }
    this.states.clear();
  }
};
