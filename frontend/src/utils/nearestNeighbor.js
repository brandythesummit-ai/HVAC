/**
 * Nearest-neighbor TSP heuristic for planning a door-knock route.
 *
 * Given N leads with (latitude, longitude) coordinates, produce an
 * ordered list that approximates a short round trip. This is a
 * classic greedy heuristic — at each step, pick the nearest
 * unvisited lead. O(n²) time; for N ≤ 30 (the plan-for-today cap)
 * that's trivially fast (~900 distance calcs).
 *
 * Result is typically within 20-25% of optimal — good enough for
 * field sales where "minimize driving" is a soft goal, not a
 * strict optimization target.
 */

// Haversine distance in kilometers between two lat/lng points.
export function haversineKm(lat1, lon1, lat2, lon2) {
  const toRad = (deg) => (deg * Math.PI) / 180;
  const R = 6371;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/**
 * Nearest-neighbor ordering. Accepts either a start point or picks
 * the first lead as the start. Returns the ordered lead list and
 * total estimated distance in km.
 */
export function orderByNearestNeighbor(leads, start) {
  const plottable = leads.filter(
    (l) => typeof l.latitude === 'number' && typeof l.longitude === 'number',
  );
  if (plottable.length === 0) return { ordered: [], totalKm: 0 };

  // Use explicit start point if given; otherwise start at the lead
  // with the highest lead_score (most promising first)
  const sortedByScore = [...plottable].sort(
    (a, b) => (b.lead_score ?? 0) - (a.lead_score ?? 0),
  );
  const first = start
    ? plottable[0]
    : sortedByScore[0];

  const remaining = new Set(plottable.map((l) => l.id));
  remaining.delete(first.id);
  const ordered = [first];
  let current = first;
  let totalKm = 0;

  while (remaining.size > 0) {
    let best = null;
    let bestDist = Infinity;
    for (const id of remaining) {
      const lead = plottable.find((l) => l.id === id);
      const d = haversineKm(
        current.latitude,
        current.longitude,
        lead.latitude,
        lead.longitude,
      );
      if (d < bestDist) {
        bestDist = d;
        best = lead;
      }
    }
    totalKm += bestDist;
    remaining.delete(best.id);
    ordered.push(best);
    current = best;
  }

  return { ordered, totalKm };
}

/**
 * Build a Google Maps directions URL for an ordered route.
 * Google supports `waypoints=...&destination=...` with up to ~25 stops.
 */
export function buildGoogleMapsUrl(orderedLeads) {
  if (orderedLeads.length === 0) return '';
  const points = orderedLeads.map((l) => `${l.latitude},${l.longitude}`);
  const destination = points.pop();
  const waypoints = points.slice(1).join('|'); // skip first (origin)
  const origin = points[0] || destination;
  const params = new URLSearchParams({
    api: '1',
    origin,
    destination,
  });
  if (waypoints) params.set('waypoints', waypoints);
  return `https://www.google.com/maps/dir/?${params.toString()}`;
}

/**
 * Apple Maps URL. Supports fewer stops but the syntax is simpler.
 */
export function buildAppleMapsUrl(orderedLeads) {
  if (orderedLeads.length === 0) return '';
  const points = orderedLeads.map((l) => `${l.latitude},${l.longitude}`);
  const query = points.join('+to:');
  return `https://maps.apple.com/?saddr=${encodeURIComponent(query)}`;
}
