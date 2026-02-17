# Savegame Structure Investigation
# Tier Evaluation: Data Sources and Key Mappings

**Date:** 2026-02-17
**Savegame:** Resistsave00004_2027-8-1.gz (Resistance, 2027-08-01)

---

## Overview

Tier evaluation needs to calculate readiness from the savegame DB. This document
records the confirmed JSON key paths and resolution chains for each tier condition.

All data lives under `gamestates` in the savegame JSON, stored as arrays of
`{ "Key": {"value": N}, "Value": {...} }` objects.

---

## Finding the Player Faction

```
TIPlayerState[]
  .Value.isAI == false           → human player
  .Value.faction.value           → player_faction_key

TIFactionState[]
  .Key.value == player_faction_key
  .Value                         → pf (player faction, used throughout)
```

---

## Tier Condition Data Sources

### 1. Mission Control (MC) Capacity

**Condition:** 10+ MC (Tier 2), 25+ MC (Tier 3)

MC is a *capacity* resource, not a stockpile. The meaningful value is:

```
pf.baseIncomes_year.MissionControl    # annual MC income = total MC capacity
```

`pf.missionControlUsage` = slots currently occupied by missions (not useful for tier eval).
`pf.resources.MissionControl` = current unspent MC stockpile (also not the right value).

**Confirmed values (2027-08-01):** capacity=2, usage=4, stockpile=0.0

---

### 2. Habs Owned (count and location)

**Conditions:**
- Tier 2: Operative on Luna or Mars mine
- Tier 2: Operative on Earth shipyard
- Tier 3: Control 10+ habs

**Resolution chain:**

```
TIHabState[]
  .Value.faction.value == player_faction_key   → player-owned habs

For each hab:
  .Value.habType        → "Base", "Station", "Platform", etc.
  .Value.tier           → 1, 2, 3
  .Value.inEarthLEO     → bool (Earth orbit station)
  .Value.habSite.value  → site_key

TIHabSiteState[]
  .Key.value == site_key
  .Value.parentBody.value  → body_key

TISpaceBodyState[]
  .Key.value == body_key
  .Value.displayName   → "Luna", "Mars", "Earth", etc.
```

**Known body keys (stable across saves):**
- 2: Sol, 3: Mercury, 4: Venus, 5: Earth, 6: Luna, 7: Mars
- 8: Phobos, 9: Deimos, 10: Jupiter, 28: Saturn, 55: Uranus, 85: Neptune
- 102: Ceres, 314: Pluto

**Confirmed player habs (2027-08-01):**
- Base tier 1 @ Shackleton Crater, Luna
- Base tier 1 @ Peary Crater, Luna

---

### 3. Earth Shipyard (Operative on Earth Shipyard)

**Condition:** Tier 2: operative (councilor) assigned to an Earth-orbit station shipyard

Shipyard detection:

```
TIHabModuleState[]
  .Value.templateName  contains "Shipyard"   → shipyard module
  .Value.sector.value  → sector_key

Sector → Hab: build map from TIHabState[].Value.sectors[]

Hab:
  .Value.inEarthLEO == true   → in Earth orbit
  .Value.faction.value        → owning faction
```

Note: No shipyard modules exist in the 2027-08-01 save (early game).
Module templateName pattern to be confirmed when one is built.

**Councilor on hab:**
```
TICouncilorState[]
  .Value.location.$type == "PavonisInteractive.TerraInvicta.TIHabState"
  .Value.location.value  → hab_key
```

---

### 4. Space Stations (Control 3+ stations)

**Condition:** Tier 2: control 3+ space stations

```
TIHabState[]
  .Value.faction.value == player_faction_key
  .Value.habType == "Station"
```

**Confirmed (2027-08-01):** 0 stations (player has only Bases on Luna)

---

### 5. Federations (Member of 3+ nation federation)

**Condition:** Tier 2: member of 3+ nation federation

The player's nations each have a `.federation` field pointing to a TIFederationState.
The federation has a `.members[]` array of nation keys.

```
TIControlPoint[]
  .Value.faction.value == player_faction_key
  .Value.nation.value  → nation_keys (set of controlled nations)

TINationState[]
  .Key.value in nation_keys
  .Value.federation.value  → fed_key

TIFederationState[]
  .Key.value == fed_key
  .Value.members[]  → all nation keys in the federation
  len(members) >= 3   → qualifies
```

**Confirmed (2027-08-01):** Player is in European Union (18 members). Qualifies.

Note: `aggregateNation` (federation as a nation object like "European Union") also has
a `.federation` back-reference. Filter to `aggregateNation == false` for individual
nations when counting federations for Tier 2.

---

### 6. Fleet in Jupiter System or Beyond (Tier 3)

**Condition:** Tier 3: fleet in Jupiter system or beyond

```
TISpaceFleetState[]
  .Value.faction.value == player_faction_key
  .Value.barycenter.value  → body_key

body_key >= 10   → Jupiter or beyond (Jupiter key = 10)
```

Note: `barycenter` is the parent body the fleet orbits. `orbitState` may be null for
docked/grounded fleets — check `dockedLocation` and `homeport` as fallbacks.

**Confirmed:** Only alien fleets present in 2027-08-01 save, orbiting Sol (key=2).

---

### 7. Councilor on Luna or Mars Mine

**Condition:** Tier 2: operative on Luna or Mars mine

A "mine" is a Base hab on Luna or Mars (mined resources come from Base habs, not Stations).

```
TICouncilorState[]
  .Value.faction.value == player_faction_key    (need to confirm this field exists)
  .Value.location.$type == "PavonisInteractive.TerraInvicta.TIHabState"
  .Value.location.value  → hab_key

TIHabState[hab_key]
  .Value.habType == "Base"
  .Value.habSite → site → parentBody → displayName in ("Luna", "Mars")
```

Note: No player councilors are on habs in the 2027-08-01 save (all on Earth regions).
Councilor faction field not confirmed — need to verify via councilor keys from `pf.councilors`.

---

### 8. Major Powers in Federation (Tier 3)

**Condition:** Tier 3: federation of 5+ major powers

"Major power" is not a stored boolean. Likely determined by GDP threshold or game
template definition. Top GDP nations observed:
- China ~32T, USA ~23T, India ~13T, EU ~6T, Russia ~5T, Japan ~5T...

**TODO:** Check TINationTemplate or game templates for major power definition.
Possible fallback: top N nations by GDP, or nations with GDP > threshold.
Alternative: nations with `spaceFlightProgram` active may be the game's definition.

---

## Fields Confirmed Unused / Misleading

| Field | Why Not Used |
|-------|-------------|
| `pf.resources.MissionControl` | Current stockpile, not capacity |
| `pf.missionControlUsage` | Slots occupied, not total capacity |
| `pf.habSectors` | Empty in this save; hab ownership is via `TIHabState.faction` instead |
| `TIHabSectorState` | Does not exist in this save (early game) |
| `TINationState.isMajorPower` | Field does not exist |

---

## Open Questions

1. **Shipyard module templateName**: What string to match? Confirm when first
   shipyard is built in-game.

2. **Major power definition**: Is it GDP threshold, template flag, or something else?
   Check `TISpaceBodyTemplate` or nation templates.

3. **Councilor faction field**: Confirm councilors have `.faction` field, or must
   we resolve via `pf.councilors` key list to determine player ownership.

4. **Tier 3: Control orbital ring or space elevator**: What habType/module is this?
   Not observed in early save.

5. **Fleet dockedLocation**: When a fleet is docked at a hab, does `barycenter`
   reflect the parent body or is `dockedLocation` needed?

---

## Implementation Notes

- Player faction: found via `TIPlayerState[isAI=false].faction.value`
- Body key lookup is stable and can be hardcoded (Sol=2, Earth=5, Luna=6, Mars=7, Jupiter=10)
- All references use `{"value": N}` key objects — always extract `.value` to compare
- Federation membership: walk player nations → their `.federation` → count `members`
- Hab count: filter `TIHabState` by `faction.value`, not via `pf.habSectors`
