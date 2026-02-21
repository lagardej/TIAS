"""
orchestrator.py — Main call graph for TIAS V2.

Wires all nodes together into a single turn() function.
play/command.py calls this; everything else is internal.

Call graph:
    identify_actor → tier_check → fragment_fetch → prompt_assemble
    → llm_call → parse_response → validate_action → commit_log → display
"""

import logging
import random
import tomllib
from pathlib import Path

from src.core.core import get_project_root, load_env
from src.orchestrator.commit_log import CommitContext, commit_log, make_session_id
from src.orchestrator.display import display
from src.orchestrator.fragment_fetch import fragment_fetch
from src.orchestrator.identify_actor import (
    ActorSpec,
    FlowType,
    IdentifyResult,
    load_actor_specs,
    identify_actor,
)
from src.orchestrator.llm_call import llm_call
from src.orchestrator.parse_response import parse_response
from src.orchestrator.prompt_assemble import HistoryTurn, prompt_assemble
from src.orchestrator.tier_check import TierConfidence, tier_check_all, _is_codex
from src.orchestrator.validate_action import validate_action


# ---------------------------------------------------------------------------
# Orchestrator state (session-scoped)
# ---------------------------------------------------------------------------

class OrchestratorState:
    """Holds mutable session state. One instance per play session."""

    def __init__(self, date: str, faction: str, tier: int):
        root = get_project_root()
        self.date         = date
        self.faction      = faction
        self.tier         = tier
        self.session_id   = make_session_id()
        self.history: list[HistoryTurn] = []
        self.debate_turn  = 0

        self.actors_dir    = root / "resources" / "actors"
        self.system_path   = root / "resources" / "prompts" / "system.txt"
        self.campaign_dir  = root / "campaigns" / faction   # flat — no date subdir
        self.codex_spec    = root / "resources" / "actors" / "codex" / "spec.toml"
        self.logs_dir      = root / "logs"
        self.decision_log  = root / "campaigns" / faction / f"decision_log_{date}.json"

        self.specs: list[ActorSpec] = load_actor_specs(self.actors_dir)


# ---------------------------------------------------------------------------
# Debate interrupt selector
# ---------------------------------------------------------------------------

def _select_interruptor(specs: list[ActorSpec], debating: list[ActorSpec]) -> ActorSpec | None:
    """
    Weighted random selection of interrupt actor.
    Reads interrupt.weight and interrupt.can_interrupt_own_debate from spec.toml.
    Actors with weight=0 or excluded from own debate are filtered out.
    """
    debating_names = {s.first_name.lower() for s in debating}
    pool: list[tuple[ActorSpec, int]] = []

    for spec in specs:
        spec_path = spec.actor_dir / "spec.toml"
        with open(spec_path, "rb") as f:
            data = tomllib.load(f)
        interrupt = data.get("interrupt", {})
        weight = interrupt.get("weight", 0)
        can_own = interrupt.get("can_interrupt_own_debate", False)

        if weight == 0:
            continue
        if spec.first_name.lower() in debating_names and not can_own:
            continue
        pool.append((spec, weight))

    if not pool:
        return None

    actors, weights = zip(*pool)
    return random.choices(actors, weights=weights, k=1)[0]


# ---------------------------------------------------------------------------
# Stage direction display (no LLM call)
# ---------------------------------------------------------------------------

def _stage_direction(note: str) -> str:
    return f"[{note}]"


# ---------------------------------------------------------------------------
# Single turn
# ---------------------------------------------------------------------------

def turn(query: str, state: OrchestratorState) -> str:
    """
    Process one user query. Returns formatted string for display.
    Updates state.history and state.debate_turn in place.
    """

    # --- identify_actor ---
    result: IdentifyResult = identify_actor(query, state.specs)

    if result.flow_type in (FlowType.TOO_VAGUE, FlowType.TOO_BROAD, FlowType.NO_MATCH):
        return _stage_direction(result.stage_note or "The council does not respond.")

    if result.flow_type == FlowType.AMBIGUOUS:
        # Actors resolve ambiguity in character — pass to LLM with all matched actors
        pass  # falls through to normal processing below

    # --- tier_check ---
    tier_results = tier_check_all(result.actors, state.tier)

    # Handle blocked actors
    active = []
    output_lines = []
    for tr in tier_results:
        if tr.confidence == TierConfidence.BLOCKED:
            # In-character drop-out line — use debate_interrupt config (short, punchy)
            output_lines.append(f"{tr.actor.spec.display_name.upper()}: {tr.error_message}")
        else:
            active.append(tr)

    if not active:
        return "\n\n".join(output_lines) if output_lines else _stage_direction("No advisor can help with this at the current tier.")

    # Collapse to standard if debate lost an actor to blocking
    flow_type = result.flow_type
    if flow_type == FlowType.DEBATE and len(active) == 1:
        flow_type = FlowType.STANDARD

    # --- debate soft/hard limits ---
    if flow_type == FlowType.DEBATE:
        state.debate_turn += 1
        if state.debate_turn == 3:
            output_lines.append(_stage_direction("Positions are clear. A decision is needed."))
        elif state.debate_turn >= 5:
            debating_specs = [tr.actor.spec for tr in active]
            interruptor = _select_interruptor(state.specs, debating_specs)
            if interruptor:
                interrupt_fetch = fragment_fetch(
                    interruptor, query, TierConfidence.FULL, spectator_only=False
                )
                interrupt_prompt = prompt_assemble(
                    [interrupt_fetch], query,
                    state.system_path, state.campaign_dir, state.codex_spec,
                    history=state.history, tier=state.tier, date=state.date,
                )
                interrupt_llm = llm_call(interrupt_prompt, "debate_interrupt")
                interrupt_parsed = parse_response(interrupt_llm)
                output_lines.append(display(interrupt_parsed, "debate_interrupt", interruptor.display_name))
                state.debate_turn = 0
                return "\n\n".join(output_lines)
    else:
        state.debate_turn = 0

    # --- fragment_fetch ---
    other_names = [tr.actor.spec.display_name for tr in active]
    fetches = []
    for tr in active:
        others = [n for n in other_names if n != tr.actor.spec.display_name]
        fetches.append(
            fragment_fetch(tr.actor.spec, query, tr.confidence, other_actor_names=others or None)
        )

    # --- prompt_assemble ---
    prompt = prompt_assemble(
        fetches, query,
        state.system_path, state.campaign_dir, state.codex_spec,
        history=state.history, tier=state.tier, date=state.date,
    )

    # --- llm_call ---
    llm_flow = "codex" if any(_is_codex(tr.actor.spec) for tr in active) else ("debate_turn" if flow_type == FlowType.DEBATE else "standard")
    llm_result = llm_call(prompt, llm_flow)

    # --- parse_response ---
    parsed = parse_response(llm_result)

    # --- validate_action ---
    action_result = None
    if parsed.action and parsed.action_valid:
        action_result = validate_action(parsed.action, state.decision_log)

    # --- commit_log ---
    speaker = active[0].actor.spec.display_name
    ctx = CommitContext(
        session_id=state.session_id,
        flow_type=llm_flow,
        tier=state.tier,
        speaker=speaker,
        query=query,
        parsed=parsed,
        action_result=action_result,
    )
    commit_log(ctx, state.logs_dir)

    # --- update history ---
    state.history.append(HistoryTurn(role="user", speaker="User", content=query))
    state.history.append(HistoryTurn(role="advisor", speaker=speaker, content=parsed.chat))
    state.history = state.history[-20:]  # rolling window

    # --- display ---
    output_lines.append(display(parsed, llm_flow, speaker))
    return "\n\n".join(output_lines)
