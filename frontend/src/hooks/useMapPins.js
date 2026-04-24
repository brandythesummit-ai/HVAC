/**
 * Viewport-scoped map pin fetching for the parcels-first scale.
 *
 * Pre-pivot, MapPage fetched 12K leads all at once. With ~450K residential
 * parcels, that's infeasible. This hook fetches only pins inside the
 * current map viewport via /api/map-pins, debounces on pan/zoom events,
 * and passes filter state through (tier, owner_occupied, year_built).
 *
 * Usage: called by a child of <MapContainer> that uses useMapEvents to
 * propagate bbox changes up (or reads the map via useMap()).
 */
import { useEffect, useState, useCallback, useRef } from 'react';
import apiClient from '../api/client';

const DEBOUNCE_MS = 250;

export function useMapPins({ bbox, filters = {}, enabled = true, limit = 15000 }) {
  const [pins, setPins] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [truncated, setTruncated] = useState(false);
  const debounceRef = useRef(null);
  const activeRequestRef = useRef(0);
  const abortRef = useRef(null);

  const fetchPins = useCallback(async (b) => {
    if (!b) return;
    // Abort any in-flight request so a rapid pan doesn't leave 5-10
    // zombie HTTP requests chewing bandwidth + backend connections.
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const requestId = ++activeRequestRef.current;
    setIsLoading(true);
    setError(null);
    const params = {
      bbox_ne_lat: b.ne_lat,
      bbox_ne_lng: b.ne_lng,
      bbox_sw_lat: b.sw_lat,
      bbox_sw_lng: b.sw_lng,
      limit,
    };
    if (filters.tier && filters.tier.length > 0) {
      params.lead_tier = Array.isArray(filters.tier) ? filters.tier.join(',') : filters.tier;
    }
    if (filters.ownerOccupied != null) {
      params.owner_occupied = filters.ownerOccupied;
    }
    if (filters.yearBuiltMin != null) {
      params.year_built_min = filters.yearBuiltMin;
    }
    if (filters.yearBuiltMax != null) {
      params.year_built_max = filters.yearBuiltMax;
    }

    try {
      const resp = await apiClient.get('/api/map-pins', {
        params,
        signal: controller.signal,
      });
      if (requestId !== activeRequestRef.current) return;
      const data = resp.data?.data;
      if (data) {
        setPins(data.pins || []);
        setTruncated(!!data.truncated);
      } else {
        setPins([]);
        setTruncated(false);
      }
    } catch (e) {
      // Cancelled requests aren't errors — just ignore.
      if (e?.name === 'CanceledError' || e?.name === 'AbortError' || e?.code === 'ERR_CANCELED') return;
      if (requestId !== activeRequestRef.current) return;
      setError(e);
      setPins([]);
    } finally {
      if (requestId === activeRequestRef.current) {
        setIsLoading(false);
      }
    }
  }, [filters.tier, filters.ownerOccupied, filters.yearBuiltMin, filters.yearBuiltMax, limit]);

  useEffect(() => {
    if (!enabled || !bbox) return;
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => { fetchPins(bbox); }, DEBOUNCE_MS);
    return () => clearTimeout(debounceRef.current);
  }, [
    enabled,
    bbox?.ne_lat, bbox?.ne_lng, bbox?.sw_lat, bbox?.sw_lng,
    fetchPins,
  ]);

  return { pins, isLoading, error, truncated };
}
