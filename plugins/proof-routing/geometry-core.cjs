'use strict';

const PROFILE = 'downward-orthogonal';
const BRIDGE_RADIUS = 8;
const CLEARANCE = 2;
const LABEL_HEIGHT = 28;

function port(n, side, offset = 0) {
  const cx = n.x + n.width / 2;
  const cy = n.y + n.height / 2;
  if (n.styleAttributes?.shape === 'circle' && (side === 'top' || side === 'bottom')) {
    const radius = Math.min(n.width, n.height) / 2;
    const clamped = Math.max(-radius + 5, Math.min(radius - 5, offset));
    const dy = Math.sqrt(Math.max(0, radius * radius - clamped * clamped));
    return [cx + clamped, cy + (side === 'top' ? -dy : dy)];
  }
  if (side === 'top') return [cx + offset, n.y];
  if (side === 'bottom') return [cx + offset, n.y + n.height];
  if (side === 'left') return [n.x, cy + offset];
  return [n.x + n.width, cy + offset];
}

function points(canvas, edge) {
  const nodes = Object.fromEntries(canvas.nodes.filter((node) => node.type !== 'group').map((node) => [node.id, node]));
  const route = edge.proofRoute || {};
  const start = port(nodes[edge.fromNode], 'bottom', route.fromOffset || 0);
  const end = port(nodes[edge.toNode], 'top', route.toOffset || 0);
  if (Math.abs(start[0] - end[0]) < 0.75) return [start, end];
  const middleY = (start[1] + end[1]) / 2 + (route.midOffset || 0);
  return [start, [start[0], middleY], [end[0], middleY], end];
}

function strictlyBetween(value, start, end) {
  return Math.min(start, end) < value && value < Math.max(start, end);
}

function properCrossing(first, second) {
  const firstHorizontal = first.start[1] === first.end[1] && first.start[0] !== first.end[0];
  const firstVertical = first.start[0] === first.end[0] && first.start[1] !== first.end[1];
  const secondHorizontal = second.start[1] === second.end[1] && second.start[0] !== second.end[0];
  const secondVertical = second.start[0] === second.end[0] && second.start[1] !== second.end[1];
  if (!((firstHorizontal && secondVertical) || (firstVertical && secondHorizontal))) return null;
  const horizontal = firstHorizontal ? first : second;
  const vertical = firstVertical ? first : second;
  const x = vertical.start[0];
  const y = horizontal.start[1];
  if (!strictlyBetween(x, horizontal.start[0], horizontal.end[0]) ||
      !strictlyBetween(y, vertical.start[1], vertical.end[1])) return null;
  return {
    edges: [first.edgeId, second.edgeId],
    point: [x, y],
    horizontal: {edgeId: horizontal.edgeId, segment: horizontal.segment},
    vertical: {edgeId: vertical.edgeId, segment: vertical.segment},
  };
}

function detectCrossings(routeList) {
  const segments = [];
  for (const route of routeList) {
    for (let segment = 0; segment < route.points.length - 1; segment += 1) {
      segments.push({
        edgeId: route.id,
        segment,
        start: route.points[segment],
        end: route.points[segment + 1],
      });
    }
  }
  const found = [];
  for (let index = 0; index < segments.length; index += 1) {
    for (let other = index + 1; other < segments.length; other += 1) {
      if (segments[index].edgeId === segments[other].edgeId) continue;
      const crossing = properCrossing(segments[index], segments[other]);
      if (crossing) found.push(crossing);
    }
  }
  return found;
}

function bridgeId(edgeId, segment, firstX, lastX) {
  return `${edgeId}:${segment}:${firstX}:${lastX}`;
}

function allocateBridges(routeList, detected) {
  const byEdge = new Map(routeList.map((route) => [route.id, route]));
  const candidates = new Map();
  const seen = new Set();
  for (const crossing of detected) {
    const owner = crossing.horizontal;
    const route = byEdge.get(owner.edgeId);
    const start = route.points[owner.segment];
    const end = route.points[owner.segment + 1];
    const key = `${owner.edgeId}:${owner.segment}:${crossing.point[0]}:${crossing.point[1]}`;
    if (seen.has(key)) continue;
    seen.add(key);
    const distanceToTurn = Math.min(
      Math.abs(crossing.point[0] - start[0]),
      Math.abs(end[0] - crossing.point[0]),
    );
    if (distanceToTurn < BRIDGE_RADIUS + CLEARANCE) continue;
    const segmentKey = `${owner.edgeId}:${owner.segment}`;
    if (!candidates.has(segmentKey)) candidates.set(segmentKey, []);
    candidates.get(segmentKey).push({edgeId: owner.edgeId, segment: owner.segment, point: crossing.point});
  }

  const bridges = new Map(routeList.map((route) => [route.id, []]));
  for (const segmentCandidates of candidates.values()) {
    segmentCandidates.sort((left, right) => left.point[0] - right.point[0]);
    let cluster = [];
    const flush = () => {
      if (!cluster.length) return;
      const first = cluster[0];
      const last = cluster[cluster.length - 1];
      const startX = first.point[0] - BRIDGE_RADIUS;
      const endX = last.point[0] + BRIDGE_RADIUS;
      bridges.get(first.edgeId).push({
        id: bridgeId(first.edgeId, first.segment, first.point[0], last.point[0]),
        edgeId: first.edgeId,
        segment: first.segment,
        startX,
        endX,
        y: first.point[1],
        radiusX: (endX - startX) / 2,
        radiusY: BRIDGE_RADIUS,
        points: cluster.map((item) => item.point),
      });
      cluster = [];
    };
    for (const candidate of segmentCandidates) {
      const previous = cluster[cluster.length - 1];
      if (previous && candidate.point[0] - previous.point[0] >= 2 * BRIDGE_RADIUS + CLEARANCE) flush();
      cluster.push(candidate);
    }
    flush();
  }

  for (const [edgeId, edgeBridges] of bridges) {
    const route = byEdge.get(edgeId);
    edgeBridges.sort((left, right) => {
      if (left.segment !== right.segment) return left.segment - right.segment;
      const start = route.points[left.segment];
      const end = route.points[left.segment + 1];
      const direction = Math.sign(end[0] - start[0]);
      return direction * (left.startX - right.startX);
    });
  }
  return bridges;
}

function svg(routePoints, bridges = []) {
  let path = `M ${routePoints[0][0]} ${routePoints[0][1]}`;
  for (let segment = 0; segment < routePoints.length - 1; segment += 1) {
    const start = routePoints[segment];
    const end = routePoints[segment + 1];
    const direction = Math.sign(end[0] - start[0]);
    const segmentBridges = bridges.filter((bridge) => bridge.segment === segment);
    for (const bridge of segmentBridges) {
      const before = direction > 0 ? bridge.startX : bridge.endX;
      const after = direction > 0 ? bridge.endX : bridge.startX;
      const sweep = direction > 0 ? 1 : 0;
      path += ` L ${before} ${bridge.y} A ${bridge.radiusX} ${bridge.radiusY} 0 0 ${sweep} ${after} ${bridge.y}`;
    }
    path += ` L ${end[0]} ${end[1]}`;
  }
  return path;
}

function labelSegment(route) {
  const index = route.points.length === 4 ? 1 : 0;
  return {index, points: [route.points[index], route.points[index + 1]]};
}

function labelRect(segment, width, x, side) {
  const lineY = (segment[0][1] + segment[1][1]) / 2;
  const y = side === 'below' ? lineY + 16 : lineY - 14;
  return {x1: x - width / 2, x2: x + width / 2, y1: y - LABEL_HEIGHT / 2,
    y2: y + LABEL_HEIGHT / 2, x, y, rectY: y - LABEL_HEIGHT / 2, below: side === 'below'};
}

function bridgeIntersectsRect(bridge, rect) {
  return rect.x1 < bridge.endX + CLEARANCE && bridge.startX - CLEARANCE < rect.x2 &&
    rect.y1 < bridge.y + CLEARANCE && bridge.y - bridge.radiusY - CLEARANCE < rect.y2;
}

function conflicts(rect, bridges) {
  return bridges.filter((bridge) => bridgeIntersectsRect(bridge, rect));
}

function horizontalCandidates(segment, width, bridges) {
  const left = Math.min(segment[0][0], segment[1][0]) + width / 2;
  const right = Math.max(segment[0][0], segment[1][0]) - width / 2;
  if (left > right) return [];
  const middle = (segment[0][0] + segment[1][0]) / 2;
  const values = new Set([Math.max(left, Math.min(right, middle))]);
  for (const bridge of bridges) {
    values.add(Math.max(left, Math.min(right, bridge.startX - CLEARANCE - width / 2)));
    values.add(Math.max(left, Math.min(right, bridge.endX + CLEARANCE + width / 2)));
  }
  return [...values].sort((first, second) => Math.abs(first - middle) - Math.abs(second - middle) || first - second);
}

function placeLabel(route, width, bridges) {
  const selected = labelSegment(route);
  const segment = selected.points;
  const middle = (segment[0][0] + segment[1][0]) / 2;
  const horizontal = segment[0][1] === segment[1][1];
  const centeredAbove = labelRect(segment, width, middle, 'above');
  if (!conflicts(centeredAbove, bridges).length) return {...centeredAbove, segment: selected.index};
  if (!horizontal) return null;
  const centeredBelow = labelRect(segment, width, middle, 'below');
  if (!conflicts(centeredBelow, bridges).length) return {...centeredBelow, segment: selected.index};
  const candidates = [];
  for (const x of horizontalCandidates(segment, width, bridges)) {
    if (x === middle) continue;
    for (const side of ['above', 'below']) {
      const candidate = labelRect(segment, width, x, side);
      if (!conflicts(candidate, bridges).length) candidates.push({...candidate, segment: selected.index});
    }
  }
  candidates.sort((first, second) => Math.abs(first.x - middle) - Math.abs(second.x - middle) ||
    Number(first.below) - Number(second.below) || first.x - second.x);
  return candidates[0] || null;
}

function fallbackLabel(route, width) {
  const selected = labelSegment(route);
  const segment = selected.points;
  const middle = (segment[0][0] + segment[1][0]) / 2;
  return {...labelRect(segment, width, middle, 'above'), segment: selected.index};
}

function resolveLabels(routeList, labelSpecs) {
  const byEdge = new Map(routeList.map((route) => [route.id, route]));
  const allBridges = routeList.flatMap((route) => route.bridges);
  const suppressed = new Set();
  for (const spec of labelSpecs) {
    const route = byEdge.get(spec.edgeId);
    if (placeLabel(route, spec.width, allBridges)) continue;
    const fallback = fallbackLabel(route, spec.width);
    for (const bridge of conflicts(fallback, allBridges)) suppressed.add(bridge.id);
  }
  const routes = routeList.map((route) => {
    const bridges = route.bridges.filter((bridge) => !suppressed.has(bridge.id));
    return {...route, bridges, path: svg(route.points, bridges)};
  });
  const visibleBridges = routes.flatMap((route) => route.bridges);
  const resolvedByEdge = new Map(routes.map((route) => [route.id, route]));
  const labels = labelSpecs.map((spec) => {
    const route = resolvedByEdge.get(spec.edgeId);
    const placement = placeLabel(route, spec.width, visibleBridges) || fallbackLabel(route, spec.width);
    return {...spec, placement};
  });
  return {routes, labels, suppressed: [...suppressed]};
}

function routes(canvas) {
  if (canvas.metadata?.proofRouting?.profile !== PROFILE) throw Error('inactive profile');
  const base = canvas.edges.map((edge) => ({...edge, points: points(canvas, edge)}));
  const detected = detectCrossings(base);
  const bridgeMap = allocateBridges(base, detected);
  return base.map((edge) => {
    const crossings = detected.filter((crossing) => crossing.edges.includes(edge.id));
    const bridges = bridgeMap.get(edge.id);
    return {...edge, crossings, bridges, path: svg(edge.points, bridges)};
  });
}

module.exports = {
  PROFILE,
  BRIDGE_RADIUS,
  CLEARANCE,
  port,
  points,
  properCrossing,
  detectCrossings,
  allocateBridges,
  svg,
  bridgeIntersectsRect,
  placeLabel,
  resolveLabels,
  routes,
};
