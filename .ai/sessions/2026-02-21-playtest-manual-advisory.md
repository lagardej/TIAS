# Session: Live Advisory Playtest (Manual Mode)
**Date:** 2026-02-21
**Type:** Playtest / Requirements gathering (separate chat, not a dev session)
**Status:** Complete — findings archived for schema/pipeline planning

## Context
Live advisory session on a fresh campaign, epoch 2029→2032. Manual mode —
no TIAS pipeline, advisors answered from raw JSON templates + user-provided data.
Purpose: stress-test what data TIAS needs to surface automatically.

## Campaign state at session end
- Epoch: 2032-07-16
- Fission Pulse Drive: queued (ETA ~Dec 2032)
- Shipyards: dual online (LEO1 + Mars orbit)
- First cruiser design: pending drive completion

## Critical data gaps (every exchange required manual alt-tab)
These are non-negotiable for useful advisory output:

### Per-faction (save state)
- CP total/cap
- MC total/cap
- Fund/boost/research income
- Space site list with resource output

### Per-nation (save state)
- CP count and institutional control
- Public opinion
- Priority profile and income effects
- Faction holder

### Player resource state
- All six resource types (stockpile + income)

### Space infrastructure (save state)
- Hab type, tier, modules installed
- Crew count and requirements
- Power balance per site
- Construction queue (what/where/ETA)

### Tech tree (template + save state)
- Researched vs available vs locked
- Prereq chains

### Ship designs
- Hull class, drive type, weapons, armor

## Advisor domain validation
All five advisors confirmed viable with correct data access:

- **Jonny** (Orbital/Space): outpost dev path, module tiers, shipyard strategy, drive sequencing,
  resource stockpile vs consumption. Needs TIHabModuleTemplate + TITechTemplate + save.
- **Valentina** (Diplomacy/Intel): faction ground footprint, MC cap analysis, coup assessment.
  Needs faction CP/MC/resource state from save.
- **Lin** (Political): unification chains, CP/MC sequencing, nation priority profiles.
  Needs nation control state from save.
- **Wale** (Covert): disruption timing, Servants collapse tracking, threat assessment.
  Needs faction health metrics from save.
- **CODEX**: income vs expenditure, faction threat ranking. Needs full parsed save state.

## Key technical finding: module/tech cross-reference
TIHabModuleTemplate.json has NO tech prereq field.
Unlock gates are via `requiredProjectName` (game project system) + crew capacity thresholds.
TITechTemplate.json prereqs are the research gates.
To answer "what can I build now": cross-reference via project system.
Pipeline implication: need to index TIProjectTemplate + link to modules + techs.

## Mining data
Session used user-provided CSV of hab site mining profiles.
This data exists in TIHabSiteTemplate — should be in SQLite after `tias load`.
Confirmed useful for enemy resource trajectory assessment.

## Pipeline value confirmed
Reading raw JSON templates live was functional but slow.
`tias load` indexing into SQLite makes these queries instant.

## Schema gaps this session exposes (V2 candidates)
- `gs_faction_resources`: add income breakdown (fund/boost/research income, not just stockpile)
- `gs_nations`: add priority_profile, institutional_control columns
- `gs_habs`: add modules (separate table), crew, power_balance, construction_queue
- `gs_tech`: new table — tech_name, status (researched/available/locked), prereqs
- `gs_ship_designs`: new table — hull, drive, weapons, armor
- `gs_hab_sites`: mining profile from TIHabSiteTemplate (tias load phase)
- Project system cross-reference: TIProjectTemplate → modules + techs
