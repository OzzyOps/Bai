#!/usr/bin/env python3
"""Check that the agent company is internally consistent and can actually run.

BAi refuses to ship a product without a golden set. Its own operating system had
no test at all: twelve agent definitions, a routing table in prose, a phase
ladder referenced eleven times and defined nowhere, and three places where the
rules were written down differently.

This validator makes `company/ORCHESTRATION.yaml` the source of truth and fails
the build when the agent files, the documentation or the spec disagree.

    python3 scripts/validate_orchestration.py

Exit 0 if consistent, 1 with a numbered list of faults otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent

# Claude Code accepts family aliases, full model ids, or `inherit`.
ALLOWED_MODELS = {"opus", "sonnet", "haiku", "fable", "inherit"}

# The tool a subagent needs in order to delegate to another subagent. Only the
# supervisor may hold it: the whole point of a hierarchy is that generators
# cannot quietly commission their own evaluations.
DELEGATION_TOOL = "Agent"

VALID_ROLES = {"generate", "evaluate", "synthesise"}


class Faults:
    def __init__(self) -> None:
        self.items: list[str] = []

    def add(self, message: str) -> None:
        self.items.append(message)

    def __bool__(self) -> bool:
        return bool(self.items)


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    """Return (frontmatter, body). Raises ValueError if the file has no header."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError("no YAML frontmatter")
    _, header, body = text.split("---", 2)
    data = yaml.safe_load(header) or {}
    if not isinstance(data, dict):
        raise TypeError("frontmatter is not a mapping")
    return {str(k): v for k, v in data.items()}, body


def declared_evaluators(description: str) -> list[str]:
    """Pull the evaluators an agent's own description promises.

    This matters more than it looks: Claude Code routes on the description, so
    the description is the behaviour. A routing table that disagrees with it is
    documentation, not configuration.
    """
    match = re.search(r"evaluated by ([a-z, \-]+?) before", description)
    if not match:
        return []
    return [part.strip() for part in re.split(r",| and ", match.group(1)) if part.strip()]


def check(root: Path = ROOT) -> list[str]:
    """Return the list of faults. Empty means consistent.

    Takes `root` so the test suite can run it against a deliberately corrupted
    copy of the repo — a validator nobody has watched fail is not evidence.
    """
    spec_path = root / "company" / "ORCHESTRATION.yaml"
    agent_dir = root / ".claude" / "agents"
    operating_manual = root / "CLAUDE.md"

    faults = Faults()

    spec: dict[str, Any] = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    agents: dict[str, Any] = spec["agents"]
    evaluation: dict[str, list[str]] = spec["evaluation"]
    phases: list[dict[str, Any]] = spec["phases"]
    briefs: dict[str, Any] = spec["briefs"]

    pods: dict[str, set[str]] = {}
    for name, meta in agents.items():
        pods.setdefault(meta["pod"], set()).add(name)

    supervisors = pods.get("supervisor", set())
    producers = {n for n, m in agents.items() if m["generates"]}

    # ── 1. the roster matches the files on disk ────────────────────────────
    files = {p.stem: p for p in sorted(agent_dir.glob("*.md"))}

    for name in sorted(set(agents) - set(files)):
        faults.add(f"{name!r} is in ORCHESTRATION.yaml but has no .claude/agents/{name}.md")
    for name in sorted(set(files) - set(agents)):
        faults.add(f".claude/agents/{name}.md exists but {name!r} is not in ORCHESTRATION.yaml")

    frontmatter: dict[str, dict[str, str]] = {}
    bodies: dict[str, str] = {}

    for name, path in files.items():
        try:
            fm, body = parse_frontmatter(path)
        except (ValueError, TypeError) as exc:
            faults.add(f"{path.name}: {exc}")
            continue
        frontmatter[name], bodies[name] = fm, body

        if fm.get("name") != name:
            faults.add(
                f"{path.name}: frontmatter name is {fm.get('name')!r} but the file is {name}.md — "
                f"Claude Code resolves by the frontmatter name, so one of them is unreachable"
            )
        if not str(fm.get("description", "")).strip():
            faults.add(f"{path.name}: no description — automatic routing has nothing to match on")

        model = str(fm.get("model", "inherit"))
        if model not in ALLOWED_MODELS and not model.startswith("claude-"):
            faults.add(f"{path.name}: model {model!r} is not an alias, a claude-* id, or inherit")
        if name in agents and model != str(agents[name]["model"]):
            faults.add(
                f"{path.name}: model is {model!r} but ORCHESTRATION.yaml says "
                f"{agents[name]['model']!r}"
            )

        tools = [t.strip() for t in str(fm.get("tools", "")).split(",") if t.strip()]
        has_delegation = any(t == DELEGATION_TOOL or t.startswith(f"{DELEGATION_TOOL}(") for t in tools)
        if name in supervisors and not has_delegation:
            faults.add(
                f"{path.name}: the supervisor has no {DELEGATION_TOOL} tool, so it cannot invoke "
                f"any other agent. The company cannot run."
            )
        if name not in supervisors and has_delegation:
            faults.add(
                f"{path.name}: holds the {DELEGATION_TOOL} tool but is not the supervisor — "
                f"a generator that can commission its own evaluation defeats the hierarchy"
            )

    # ── 2. every producer is evaluated, by someone who can falsify it ──────
    for name in sorted(producers):
        if name not in evaluation:
            faults.add(f"{name!r} produces artefacts but has no evaluator (locked rule: no raw "
                       f"generator output reaches the CEO)")
    for producer, assigned in evaluation.items():
        if producer not in agents:
            faults.add(f"evaluation lists {producer!r}, which is not an agent")
            continue
        if not agents[producer]["generates"]:
            faults.add(f"{producer!r} does not produce artefacts, so it needs no evaluator")
        if not assigned:
            faults.add(f"{producer!r} has an empty evaluator list")
        for ev in assigned:
            if ev not in agents:
                faults.add(f"{producer!r} is evaluated by {ev!r}, which is not an agent")
            elif ev in supervisors:
                faults.add(
                    f"{producer!r} is evaluated by the supervisor. The Overlord arbitrates "
                    f"between critiques; it does not supply them."
                )
            if ev == producer:
                faults.add(f"{producer!r} evaluates itself")

    # ── 3. the descriptions agree with the spec ────────────────────────────
    # The check that would have caught the drift already present in the repo.
    for producer, assigned in evaluation.items():
        fm = frontmatter.get(producer)
        if fm is None:
            continue
        declared = declared_evaluators(str(fm.get("description", "")))
        if sorted(declared) != sorted(assigned):
            faults.add(
                f".claude/agents/{producer}.md: description promises evaluation by "
                f"{declared or ['nobody']} but ORCHESTRATION.yaml assigns {assigned}. "
                f"Claude Code routes on the description, so the description is what happens."
            )

    # ── 4. the phase ladder is ordered and complete ────────────────────────
    ids_in_order = [p["id"] for p in phases]
    if ids_in_order != sorted(ids_in_order):
        faults.add(
            f"phases are listed as {ids_in_order}, not in ascending order — the file is read "
            f"top to bottom by humans and the order is the whole point"
        )

    seen_ids: set[int] = set()
    for phase in phases:
        pid, pname = phase["id"], phase["name"]
        label = f"phase {pid} ({pname})"

        if pid in seen_ids:
            faults.add(f"{label}: duplicate phase id")
        seen_ids.add(pid)

        if not phase.get("gate"):
            faults.add(f"{label}: no gate. An ungated phase is not a phase.")

        stages = phase.get("stages") or []
        if not stages:
            faults.add(f"{label}: no stages")
            continue

        generated_by: set[str] = set()
        saw_evaluation = False

        for index, stage in enumerate(stages):
            agent, role = stage.get("agent"), stage.get("role")
            where = f"{label} stage {index + 1}"

            if agent not in agents:
                faults.add(f"{where}: {agent!r} is not an agent")
                continue
            if role not in VALID_ROLES:
                faults.add(f"{where}: role {role!r} is not one of {sorted(VALID_ROLES)}")
                continue

            if role in {"generate", "synthesise"}:
                if not agents[agent]["generates"]:
                    faults.add(f"{where}: {agent!r} does not produce artefacts but is asked to {role}")
                generated_by.add(agent)

            if role == "evaluate":
                saw_evaluation = True
                # An evaluator must be evaluating something produced earlier in
                # this phase, and must be an assigned evaluator for it.
                targets = [g for g in generated_by if agent in evaluation.get(g, [])]
                if not generated_by:
                    faults.add(
                        f"{where}: {agent!r} evaluates before anything in this phase has been "
                        f"produced — evaluators run after generators, never before"
                    )
                elif not targets:
                    faults.add(
                        f"{where}: {agent!r} evaluates, but is not an assigned evaluator for any "
                        f"of {sorted(generated_by)} produced in this phase"
                    )

        if not saw_evaluation:
            faults.add(
                f"{label}: produces artefacts with no evaluation stage — "
                f"raw output would reach the CEO"
            )

        if stages and stages[0].get("role") == "evaluate":
            faults.add(f"{label}: opens with an evaluation stage, so there is nothing to evaluate")

    # ── 5. briefs route to phases that exist ───────────────────────────────
    reachable: set[str] = set(supervisors)
    for brief_name, brief in briefs.items():
        ids = brief.get("phases") or []
        if not ids:
            faults.add(f"brief {brief_name!r}: routes to no phases")
        if ids != sorted(ids):
            faults.add(f"brief {brief_name!r}: phases {ids} are not in ascending order")
        for pid in ids:
            if pid not in seen_ids:
                faults.add(f"brief {brief_name!r}: routes to phase {pid}, which is not defined")

        entry = brief.get("entry_agent")
        if entry not in agents:
            faults.add(f"brief {brief_name!r}: entry_agent {entry!r} is not an agent")
        elif ids:
            first = next((p for p in phases if p["id"] == ids[0]), None)
            stage_agents = [s.get("agent") for s in (first or {}).get("stages") or []]
            if first and entry not in stage_agents:
                faults.add(
                    f"brief {brief_name!r}: entry_agent {entry!r} does not appear in its first "
                    f"phase ({first['name']}), so the brief starts with an agent that never runs"
                )
            elif first and stage_agents and stage_agents[0] != entry:
                # Not pedantry: routing a compliance question to a phase that opens
                # with the tech lead drafting answers it the wrong way round.
                faults.add(
                    f"brief {brief_name!r}: entry_agent is {entry!r} but phase {first['id']} "
                    f"({first['name']}) opens with {stage_agents[0]!r}. The agent named as the "
                    f"entry point must be the one that actually runs first."
                )

        if not brief.get("match"):
            faults.add(f"brief {brief_name!r}: no match signals, so the Overlord cannot choose it")

        for pid in ids:
            phase = next((p for p in phases if p["id"] == pid), None)
            if phase:
                reachable.update(s["agent"] for s in phase.get("stages") or [] if "agent" in s)

    # ── 6. no agent is dead weight ─────────────────────────────────────────
    for name in sorted(set(agents) - reachable):
        faults.add(
            f"{name!r} is on the roster but no brief routes to a phase it appears in — "
            f"it would never run"
        )

    # ── 7. the operating manual matches the roster ─────────────────────────
    manual = operating_manual.read_text(encoding="utf-8")
    for name in agents:
        if f"`{name}`" not in manual:
            faults.add(f"CLAUDE.md does not list {name!r} — the manual and the roster disagree")
    for pod, members in pods.items():
        row = re.search(rf"\*\*{pod.capitalize()}\*\*\s*\|([^\n|]*)\|", manual, re.IGNORECASE)
        if row:
            listed = set(re.findall(r"`([a-z-]+)`", row.group(1)))
            if listed != members:
                faults.add(
                    f"CLAUDE.md lists the {pod} pod as {sorted(listed)} but the roster says "
                    f"{sorted(members)}"
                )

    # ── 8. agents are pointed at files that exist ──────────────────────────
    for name, body in bodies.items():
        for ref in sorted(set(re.findall(r"`([A-Za-z0-9_][A-Za-z0-9_./-]*\.[a-z]{2,4})`", body))):
            if "/" not in ref:
                continue  # bare filenames are prose shorthand, not paths
            if not (root / ref).exists():
                faults.add(f".claude/agents/{name}.md points at {ref}, which does not exist")

    return faults.items


def plan(brief_name: str, root: Path = ROOT) -> int:
    """Print the run plan for a brief type — who runs, in what order.

    The Overlord does this from the spec at runtime. This exists so a human can
    see the same thing without starting an agent, and so the order can be read
    at a glance rather than inferred from prose.
    """
    spec = yaml.safe_load((root / "company" / "ORCHESTRATION.yaml").read_text(encoding="utf-8"))
    briefs, phases = spec["briefs"], {p["id"]: p for p in spec["phases"]}

    brief = briefs.get(brief_name)
    if brief is None:
        print(f"unknown brief {brief_name!r}. Known: {', '.join(sorted(briefs))}")
        return 1

    print(f"\nBRIEF   {brief_name} — {brief['description']}")
    print(f"ENTRY   {brief['entry_agent']}")
    if brief.get("notes"):
        print(f"NOTE    {' '.join(brief['notes'].split())}")
    print(f"PHASES  {brief['phases']}\n")

    for pid in brief["phases"]:
        phase = phases[pid]
        print(f"  ── phase {pid} · {phase['name']} " + "─" * max(0, 46 - len(phase["name"])))
        print(f"     {phase['question']}")
        if phase.get("requires_from_ceo"):
            print(f"     NEEDS FROM CEO: {phase['requires_from_ceo']}")
        step = 0
        for stage in phase.get("stages") or []:
            marker = "  ∥ " if stage.get("parallel") else f"{step + 1:>3}. "
            if not stage.get("parallel"):
                step += 1
            print(f"     {marker}{stage['agent']:<20} {stage['role']}")
        print(f"     GATE: {' '.join(str(phase['gate']).split())}\n")

    return 0


def main(root: Path = ROOT) -> int:
    found = check(root)
    if found:
        print(f"✗ orchestration is inconsistent — {len(found)} fault(s):\n")
        for i, fault in enumerate(found, 1):
            print(f"  {i:2}. {fault}")
        print("\n`company/ORCHESTRATION.yaml` is the source of truth. Fix there first.")
        return 1

    spec = yaml.safe_load((root / "company" / "ORCHESTRATION.yaml").read_text(encoding="utf-8"))
    pods = {m["pod"] for m in spec["agents"].values()}
    stages = sum(len(p.get("stages") or []) for p in spec["phases"])
    print(
        f"✓ orchestration consistent — {len(spec['agents'])} agents in {len(pods)} pods, "
        f"{len(spec['phases'])} phases, {stages} stages, {len(spec['briefs'])} brief routes, "
        f"{len(spec['evaluation'])} evaluator pairings, 0 faults"
    )
    return 0


if __name__ == "__main__":
    args = sys.argv[1:]
    if args and args[0] == "--plan":
        if len(args) < 2:
            spec_briefs = yaml.safe_load(
                (ROOT / "company" / "ORCHESTRATION.yaml").read_text(encoding="utf-8")
            )["briefs"]
            print("usage: validate_orchestration.py --plan <brief>")
            print("briefs: " + ", ".join(sorted(spec_briefs)))
            sys.exit(1)
        sys.exit(plan(args[1]))
    sys.exit(main(Path(args[0]) if args else ROOT))
