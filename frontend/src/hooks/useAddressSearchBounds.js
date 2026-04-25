/**
 * Debounced address-search → bounding box lookup.
 *
 * Used by MapPage so that typing "newberry grove" in the FilterBar
 * flies the map to that subdivision instead of leaving the user at
 * a county-wide zoom where no pins render (MIN_FETCH_ZOOM=13 gate).
 *
 * Backed by /api/properties/search-bounds which runs ILIKE against
 * our own residential parcels — no external geocoder, no rate limit,
 * and every hit is a parcel we'd render.
 */
import { useEffect, useState, useRef } from 'react';
import apiClient from '../api/client';

const DEBOUNCE_MS = 350;
const MIN_LENGTH = 2;

export function useAddressSearchBounds(query) {
  // `searched` flips true only after a network response (success or
  // failure). It's distinct from `!loading` because the 350ms debounce
  // window sits between "user typed" and "we started loading" — during
  // that gap, `loading=false` and `found=false`, which would otherwise
  // misread as "no match" and flash the empty-result state to the user.
  const [result, setResult] = useState({
    bounds: null,
    found: false,
    tooBroad: false,
    count: 0,
    loading: false,
    searched: false,
  });
  const debounceRef = useRef(null);
  const activeRequestRef = useRef(0);

  useEffect(() => {
    const q = (query || '').trim();
    if (q.length < MIN_LENGTH) {
      // Clear any stale result so MapPage doesn't keep flying to the
      // previous subdivision after the user clears the search.
      setResult({
        bounds: null, found: false, tooBroad: false,
        count: 0, loading: false, searched: false,
      });
      return;
    }

    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      const requestId = ++activeRequestRef.current;
      setResult((prev) => ({ ...prev, loading: true }));
      try {
        const resp = await apiClient.get('/api/properties/search-bounds', { params: { q } });
        if (requestId !== activeRequestRef.current) return;
        const data = resp.data?.data;
        setResult({
          bounds: data?.found ? data.bbox : null,
          found: !!data?.found,
          tooBroad: !!data?.too_broad,
          count: data?.count || 0,
          loading: false,
          searched: true,
        });
      } catch {
        if (requestId !== activeRequestRef.current) return;
        setResult({
          bounds: null, found: false, tooBroad: false,
          count: 0, loading: false, searched: true,
        });
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(debounceRef.current);
  }, [query]);

  return result;
}
