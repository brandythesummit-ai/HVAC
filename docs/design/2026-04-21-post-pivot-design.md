# HVAC Lead Gen — Post-Pivot Design Record

**Date:** 2026-04-21
**Author:** Brandy + Claude (grill-me skill)
**Status:** Approved design. Rebuild-ready.

---

## Context

The original HVAC Lead Gen platform (full-stack React/FastAPI on Supabase/Railway/Vercel, 67-county Florida Accela permit pull pipeline with Summit.AI CRM sync) was pivoted on 2026-04-21 following the user's stated direction: *"What we originally started building is not the same as where I need to take this project right now."*

This document captures every design decision reached during a ~3-hour grill-and-validate session covering 13 question branches, a meta-constraint, a UI expansion, and a rip-list. Decisions below are binding for the rebuild.

---

## Meta-constraint (always applies)

**Zero new recurring costs until revenue is generated.** Already-paid infrastructure (Railway backend tier, Supabase free tier, Vercel free tier) is fair game. Every third-party service must be free-tier or deferred. This rule drove the map provider decision (Mapbox free tier over Google Maps), the geocoder choice (US Census over commercial), the auth decision (Supabase Auth magic link over paid providers), and the routing decision (client-side nearest-neighbor over paid Optimization APIs).

---

## 1. Product Vision

| Area | Decision | Reasoning |
|---|---|---|
| **Core purpose** | Identify houses most likely to need a new HVAC system. Permit-driven lead gen for field sales. | Buddy door-knocks; goal is closing HVAC replacements, not nurturing relationships. |
| **Scope** | 1 user (user's buddy in HVAC sales) for V1. Hillsborough County FL only. Pinellas as fast-follow once the current API-access blocker is resolved. | Revenue validation before multi-county complexity. |
| **Product shape** | Standalone, Hale-Recon-inspired map-first field sales tool. Not a CRM. Not a dashboard. Not a listings exchange. | Buddy's workflow is knock-driven; GHL is downstream for nurture. |
| **Inspiration** | Hale Recon (roofing sales tool for hailstorm territory prospecting). Similar model, adapted to HVAC signals. | User hasn't personally demoed Hale Recon but has second-hand praise from roofing-industry contacts. |

## 2. Signal & Data Pipeline

| Area | Decision | Reasoning |
|---|---|---|
| **Signal A — Permits** | Ship first. Filter HVAC permits from Accela V4 API (`module=Building`, `type.value=Building/Residential/Trade/Mechanical`) opened 5+ years ago. | Empirical validation confirmed 100% enrichment completeness for HCFL in 2020–2025. ~13K–26K candidate permits accessible. |
| **Signal A threshold** | **5+ years** (revised from 8+ during validation) | Hillsborough County's Accela API has a hard retention cutoff at approximately 2020. Permits opened in 2019 or earlier return zero records. 5+ years is the deepest reliably retrievable window. |
| **Signal B — House age via GIS** | Deferred to fast-follow. Will use as primary signal for any county where Accela API access is blocked, and as an enrichment overlay for HCFL. | Richer signal (identifies houses with aging original HVAC, regardless of permit activity) but bigger build. Revenue-first rule says prove Signal A first. |
| **Pull cadence** | 7-day rolling pulls. Each pull fetches last 8 days of HCFL permits (1-day overlap prevents gaps). | Low API load, scales cleanly across future counties without re-architecture. |
| **Enrichment** | Single API call per batch via Accela `expand=addresses,owners,parcels`. Confirmed 100% completeness for HCFL 2020–2025 residential mechanical permits. | Eliminates the old 4-call-per-permit pattern. Rate-limit safe. |
| **HVAC type (HCFL)** | `Building/Residential/Trade/Mechanical` — hierarchical path format, NOT the human-readable display label. | 13% of all HCFL Building permits. Verified via `discover_permit_types.py` logic. |

## 3. UI / UX

### Core shape
- **Map view** is the hero. Mobile-first. Built for a salesman in a truck cab with one hand free.
- **List view** is a peer surface, not a replacement. Toggle at top switches between the two — both render full-screen.
- **Detail sheet** (bottom-sheet on mobile, modal on desktop) shows per-lead context when a pin or row is tapped.

### Component set for V1

| Component | Purpose |
|---|---|
| **Map view** (Leaflet + Mapbox tiles) | Pins geo-clustered at zoom-out. Tap pin → detail sheet. Bounding-box filter updates list view. |
| **List view** (TanStack virtual-scrolling table) | Sorted by score by default. Filter bar above. Tap row → detail sheet. |
| **Map/List toggle** | Top-of-screen button. One view full-screen at a time. Shared data model. |
| **Filter bar** | Rich filter set (9 of 10 filters functional on V1; year-built deferred to Signal B) |
| **"Plan for today" flow** | Header button → modal showing top-30 ranked leads → user multi-selects → client-side nearest-neighbor routing → ordered list + export to Google/Apple Maps. |
| **Detail sheet** | Full permit context. Status-update buttons. Notes field. "Push to GHL" button. |

### Filter specification

| Filter | V1 source | Status |
|---|---|---|
| Address search (free-text) | `permits.addresses[0].addressLine1` | Functional |
| Permit date range | `permits.openedDate` | Functional |
| Status multiselect | App's lead-status column | Functional |
| Property value range | `permits.parcels[0].improvedValue` (from Accela enrichment) | Functional |
| Permit type multiselect | `permits.type.value` | Functional |
| Owner-occupied toggle | Heuristic: `parcel.exemptionValue > 0` (FL homestead exemption) OR owner mail-address matches property address | ~80% accurate from Accela; upgrade with GIS (Signal B) later |
| Neighborhood / ZIP | `permits.addresses[0].postalCode` | Functional |
| Days-since-permit slider | Computed from `openedDate` | Functional |
| HVAC system age slider | Same as days-since-permit, framed differently | Functional |
| Year built | Not in Accela | Greyed out in V1 with "Signal B coming soon" tooltip |

### Map + geocoder

| Layer | Pick | Cost |
|---|---|---|
| Library | **Leaflet** (open-source, framework-agnostic) | $0 |
| Tiles | **Mapbox** via Leaflet tile URL (modern aesthetic, free 50K loads/month, no credit card required) | $0 on free tier |
| Geocoder | **US Census Geocoder** (unlimited free, US-gov service, ~97% residential accuracy) | $0 |
| Fallback geocoder for Census misses | **Nominatim (OSM)**, rate-limited to 1 req/sec | $0 |

Google Maps was rejected after direct comparison — the universal $200/month credit expired 2025-02-28 per Google's own docs, mandatory credit card on file, 5x smaller free tier (10K vs 50K loads/month), 14x higher post-free-tier rate ($7 vs $0.50 per 1K).

### Ranking

V1 retains the existing scoring algorithm (70% HVAC age / 15% property value / 15% permit history). Local filtering preferred over global ranking — buddy works out of whatever neighborhood he's in. Route planning is client-side nearest-neighbor heuristic. No paid optimization APIs until close-rate data proves the ranking matters enough to reweight.

## 4. Workflow & Close-loop

### Lead status machine

```
NEW
 └─(buddy knocks)→ KNOCKED:NO_ANSWER      ──(7 days)───→ resurface on map
 └─(buddy knocks)→ KNOCKED:SPOKE_TO_NON_DM ──(manual)───→ can re-knock anytime
 └─(buddy knocks)→ KNOCKED:WRONG_PERSON    ──permanent removal; owner-of-record pushed to GHL direct-mail
 └─(buddy knocks)→ KNOCKED:NOT_INTERESTED  ──180 days (configurable)──→ resurface
 └─(buddy knocks)→ INTERESTED              ──(manual)───→ creates GHL Opportunity
                       │
                       ├→ APPOINTMENT_SET
                       ├→ QUOTED
                       ├→ WON  (rev-share counted)
                       └→ LOST (Opportunity closes)
```

Not-Interested cooldown is a configurable setting (180 days default) so it can be tuned per agency.

### GHL handoff

- **Trigger:** Only after a knock. Never pre-knock. Keeps GHL lean and matches rev-share alignment.
- **Payload shape:** Contact + Opportunity model (both, not just one).
  - **Contact** keyed on property (address + owner). Dedupes across multiple knock attempts over years.
  - Contact custom fields: `HVAC Permit Age`, `Permit Type`, `Permit Date`, `Property Value`, `Parcel Number`, `Year Built`, `Owner Occupied flag`
  - Full permit `raw_data` JSON attached as a Contact note.
  - **Opportunity** created when lead moves to `INTERESTED`. One Opportunity per sales cycle.
  - Opportunity pipeline stages map to our app's post-interested statuses (Interested → Appointment Set → Quoted → Won/Lost).
- **Re-knocks after cooldown** create a new Opportunity on the existing Contact. Property-keyed Contact gives buddy a rich multi-attempt timeline.
- **Owner changes** (house sold mid-cycle): when enrichment shows a different owner name at the same address, create a new Contact and archive the old.

### Summit.AI = GoHighLevel (revealed during grill)

Summit.AI is a white-label of GHL under the user's marketing agency. The existing `summit_client.py` is already a working GHL client. Rename variables and identifiers from `summit_*` to `ghl_*` for clarity. Do not rip out the integration.

Each future HVAC-company customer = one GHL sub-account under the user's agency. Agency-level reporting in GHL becomes the natural revenue-tracking surface.

## 5. Business Model

| Area | Decision |
|---|---|
| **Buddy (V1 user)** | Rev-share or flat-rate. Trust-based, no subscription. Skin-in-the-game economics align interests on lead quality. |
| **Future HVAC-company customers** | Subscription billing. Priced later. |
| **Scale expectation** | "At least a few" customers if the thesis proves. Plan for 2–10 customer orgs within 12 months. Not 100s. |
| **Productization** | Stealth SaaS. Multi-tenant-aware schema (`agencies`, `county_id` keys, GHL sub-account primitive). No onboarding / billing / marketing UI yet. Customer #2 and #3 are hand-rolled setup. |

## 6. Technical Architecture

### Authentication
- **Magic link (passwordless)** via Supabase Auth — primary login method.
- **Session length** extended to 30 days for field reliability.
- **Google SSO** added as second option once a second customer onboards.
- Mobile-first: buddy taps the link in his email, app opens, he's in.

### Multi-tenancy
Preserved from original schema. `agencies` table stays. `permits.county_id` stays. GHL sub-account per customer. No self-serve onboarding UI — each new customer is manually added in the first year.

### Keep / Rip / Revise

**KEEP:**
- Accela V4 client (`backend/app/services/accela_client.py`)
- Rate limiter (header-based adaptive throttling with fallback delays)
- Encryption service (Fernet)
- OAuth refresh_token flow (both authorization_code and password grants)
- Summit/GHL client (rename `summit_*` → `ghl_*`)
- `agencies` / `county_id` / `permits` / `leads` schema primitives
- 7-day pull schedule logic
- Self-healing county code discovery (`backend/app/services/agency_discovery.py`)

**RIP OUT:**
- Desktop-first Leads table UI (replaced by Map + List + Detail-sheet trio)
- County-configuration admin UI (no self-serve; stealth SaaS model)
- 67-county statewide rollout scaffolding (over-built; HCFL-only V1)
- Public-facing marketing pages / landing site (deferred until sales motion begins)

**REVISE:**
- HVAC age threshold: 5+ years (forced by HCFL's ~5-year Accela API retention horizon)
- "Summit" terminology → "GHL" terminology throughout code/docs
- "67 counties" vision → "HCFL-only V1 + Pinellas as fast-follow"
- Frontend: gut desktop-first Leads table, rebuild around map-first, list-toggle, detail-sheet, filter-bar, plan-for-today

## 7. Open / Parked Items

### Pinellas + other FL Accela counties — API 500 blocker

Empirical state (2026-04-21):
- Same app `638985987877722511` + same credentials
- ✅ HCFL → 200, returns permits
- ❌ 7 other FL counties (PINELLAS, BOCC, LEECO, LEONCO, MARTINCO, PASCO, POLKCO) → HTTP 500 `internal_server_error` with trace IDs

Accela docs attribute this to agency-side EMSE (Event Manager Scripting Engine) before-event script failures or agency-level third-party-app allowlists. HCFL's admins accepted the app at some point; other agencies have not.

**User recalls a prior breakthrough that solved this in the original build.** The breakthrough is not present in the current `main` codebase (current code's request pattern is identical to what I tested today). Possible locations:
- Unmerged branches from Nov–Dec 2025
- External systems (Notion, Linear, Google Docs, Slack DMs, Gmail threads)
- Pinellas admin having revoked the allowlist since

**Resolution path:**
1. Search external systems for the breakthrough (user's homework)
2. If not found: email Jeff Rohrs (Pinellas BTS CIO, `jrohrs@pinellascounty.org`) with the 500 trace IDs and app ID to request enablement
3. In the meantime: use PCPAO GIS (Pinellas Property Appraiser) for Signal B data at no cost and no approval

**Does NOT block V1 rebuild on HCFL.**

### Supabase DB rebuild

Old project deleted. ~30-minute task:
- User creates new Supabase project (~3 minutes)
- Claude runs 18 schema migrations, seeds Accela app credentials in `app_settings`, adds HCFL county record (~27 minutes)

### Frontend rebuild

Multi-session. Gut desktop-first React table, rebuild around:
1. Leaflet map + Mapbox tiles
2. List view with TanStack virtual scroll
3. Map/List toggle, filter bar, detail sheet
4. Plan-for-today flow with nearest-neighbor routing
5. Lead-status-update flows with GHL push

## 8. Concrete Next Steps

1. **[User, 15 min, optional but high-leverage]** Search Notion/Slack/Google Docs/Gmail Nov–Dec 2025 for the Pinellas API breakthrough. Keywords: `PINELLAS`, `500`, `EMSE`, `Accela agency`, `Hunter_s.5`.
2. **[User, 3 min]** Create new Supabase project at https://supabase.com. Share Project URL + anon key + service_role key.
3. **[Claude, 30 min]** Update `backend/.env` with new Supabase credentials. Run 18 migrations in order. Seed Accela app credentials + HCFL county. Verify backend starts and `GET /api/counties` returns Hillsborough.
4. **[Claude, multi-session]** Frontend rebuild per the UI component plan in §3.
5. **[Claude, multi-session]** GHL handoff implementation (Contact + Opportunity upsert, custom fields, pipeline stage mapping).
6. **[Claude, short]** Deploy to existing Railway + Vercel infrastructure.
7. **[User]** Hand V1 to buddy. Measure close rate. Validate rev-share economics.
8. **[Follow-up]** Revisit Pinellas (breakthrough-found, or PCPAO GIS fallback).

---

## Decision provenance

Every decision in this document is traceable to a specific grill question (Q1–Q14) documented in Claude's task-tracking system during the 2026-04-21 session. If a decision here conflicts with code written later, this design is the source of truth — the code should be updated to match, not the other way around.

When future Claude sessions, code reviewers, or the user themselves have doubts about why something is built a certain way, read the relevant section of this document first.
