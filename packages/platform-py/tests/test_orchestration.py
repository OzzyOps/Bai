"""The agent company's own golden set.

BAi will not ship a product without a way to measure whether it is right. Its
own operating system — twelve agents, a routing table, a phase ladder — had no
such measure, so nothing detected that the routing table and the agents' own
descriptions had already drifted apart in three places.

`scripts/validate_orchestration.py` is that measure. These tests are the measure
of the measure: each one corrupts a copy of the repo in a specific way and
asserts the validator notices. A validator nobody has watched fail is not
evidence, it is decoration — the same false green that let the tenancy suite
pass against empty tables.
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

validate_orchestration = pytest.importorskip("validate_orchestration")
check = validate_orchestration.check


# ── the repo as it stands ──────────────────────────────────────────────────


def test_the_real_repo_is_consistent() -> None:
    faults = check(ROOT)
    assert faults == [], "orchestration faults:\n  " + "\n  ".join(faults)


def test_every_agent_file_is_loadable_by_claude_code() -> None:
    """Frontmatter must parse, and `name` must match the filename — Claude Code
    resolves an agent by its frontmatter name, so a mismatch makes it
    unreachable however good the prompt is."""
    for path in sorted((ROOT / ".claude" / "agents").glob("*.md")):
        fm, body = validate_orchestration.parse_frontmatter(path)
        assert fm["name"] == path.stem
        assert fm["description"].strip()
        assert body.strip(), f"{path.name} has frontmatter but no prompt"


def test_only_the_supervisor_can_delegate() -> None:
    """The hierarchy is real only if generators cannot commission their own
    evaluations."""
    holders = set()
    for path in sorted((ROOT / ".claude" / "agents").glob("*.md")):
        fm, _ = validate_orchestration.parse_frontmatter(path)
        tools = [t.strip() for t in str(fm.get("tools", "")).split(",")]
        if any(t == "Agent" or t.startswith("Agent(") for t in tools):
            holders.add(path.stem)
    assert holders == {"overlord"}


def test_every_brief_reaches_a_gate() -> None:
    spec = yaml.safe_load((ROOT / "company" / "ORCHESTRATION.yaml").read_text())
    phases = {p["id"]: p for p in spec["phases"]}
    for name, brief in spec["briefs"].items():
        for pid in brief["phases"]:
            assert phases[pid].get("gate"), f"brief {name} routes through ungated phase {pid}"


def test_the_first_product_is_still_the_only_thing_blocking_phase_1() -> None:
    """Phase 1 is the one phase that cannot start without the CEO. If that ever
    stops being explicit, the company will start guessing what to build."""
    spec = yaml.safe_load((ROOT / "company" / "ORCHESTRATION.yaml").read_text())
    phase_1 = next(p for p in spec["phases"] if p["id"] == 1)
    assert phase_1.get("requires_from_ceo"), "phase 1 no longer records what it needs from the CEO"


# ── mutation tests: break it, and check the validator says so ──────────────


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A working copy of just the parts the validator reads."""
    dest = tmp_path / "repo"
    (dest / "company").mkdir(parents=True)
    (dest / ".claude").mkdir()
    shutil.copytree(ROOT / ".claude" / "agents", dest / ".claude" / "agents")
    shutil.copy(ROOT / "company" / "ORCHESTRATION.yaml", dest / "company" / "ORCHESTRATION.yaml")
    shutil.copy(ROOT / "CLAUDE.md", dest / "CLAUDE.md")
    for extra in ("BLACKBOARD.md", "VOID_LOG.md"):
        shutil.copy(ROOT / extra, dest / extra)
    for doc in ("BRAND_IDENTITY.md", "BUSINESS_MODEL_CANVAS.md", "COMPLIANCE.md",
                "TECH_ARCHITECTURE.md"):
        shutil.copy(ROOT / "company" / doc, dest / "company" / doc)
    scripts = dest / "scripts"
    scripts.mkdir()
    shutil.copy(ROOT / "scripts" / "validate_orchestration.py", scripts / "validate_orchestration.py")
    tokens = dest / "packages" / "tokens" / "src"
    tokens.mkdir(parents=True)
    shutil.copy(
        ROOT / "packages" / "tokens" / "src" / "bai-core.tokens.json",
        tokens / "bai-core.tokens.json",
    )
    assert check(dest) == [], "the fixture copy must start clean"
    return dest


def edit_spec(repo: Path, mutate: Callable[[dict], None]) -> None:
    path = repo / "company" / "ORCHESTRATION.yaml"
    spec = yaml.safe_load(path.read_text())
    mutate(spec)
    path.write_text(yaml.safe_dump(spec, sort_keys=False))


def assert_fault(repo: Path, fragment: str) -> None:
    faults = check(repo)
    assert any(fragment in f for f in faults), (
        f"expected a fault mentioning {fragment!r}; got: {faults or 'no faults at all'}"
    )


def test_catches_a_missing_agent_file(repo: Path) -> None:
    (repo / ".claude" / "agents" / "secops.md").unlink()
    assert_fault(repo, "has no .claude/agents/secops.md")


def test_catches_an_agent_file_nobody_declared(repo: Path) -> None:
    (repo / ".claude" / "agents" / "rogue.md").write_text(
        "---\nname: rogue\ndescription: Does whatever it likes.\nmodel: opus\n---\n\nHello.\n"
    )
    assert_fault(repo, "is not in ORCHESTRATION.yaml")


def test_catches_a_name_that_does_not_match_its_filename(repo: Path) -> None:
    path = repo / ".claude" / "agents" / "brand.md"
    path.write_text(path.read_text().replace("name: brand", "name: branding", 1))
    assert_fault(repo, "unreachable")


def test_catches_the_supervisor_losing_its_delegation_tool(repo: Path) -> None:
    """The single fault that would silently stop the whole company: an Overlord
    with no Agent tool cannot invoke anybody."""
    path = repo / ".claude" / "agents" / "overlord.md"
    path.write_text(path.read_text().replace("Glob, Agent, Artifact", "Glob, Artifact", 1))
    assert_fault(repo, "cannot invoke")


def test_catches_a_generator_granted_delegation(repo: Path) -> None:
    path = repo / ".claude" / "agents" / "tech-lead.md"
    path.write_text(path.read_text().replace("tools: Read, Write", "tools: Agent, Read, Write", 1))
    assert_fault(repo, "defeats the hierarchy")


def test_catches_a_producer_with_no_evaluator(repo: Path) -> None:
    edit_spec(repo, lambda s: s["evaluation"].pop("tech-lead"))
    assert_fault(repo, "no evaluator")


def test_catches_an_agent_evaluating_itself(repo: Path) -> None:
    edit_spec(repo, lambda s: s["evaluation"].__setitem__("tech-lead", ["tech-lead"]))
    assert_fault(repo, "evaluates itself")


def test_catches_the_supervisor_being_used_as_an_evaluator(repo: Path) -> None:
    edit_spec(repo, lambda s: s["evaluation"].__setitem__("brand", ["overlord"]))
    assert_fault(repo, "arbitrates")


def test_catches_the_drift_that_was_actually_in_the_repo(repo: Path) -> None:
    """The regression test for the real defect: overlord.md's routing table said
    tech-lead was evaluated by secops and data-analyst, while tech-lead's own
    description promised only secops. Claude Code routes on the description, so
    the second evaluator never ran."""
    path = repo / ".claude" / "agents" / "tech-lead.md"
    path.write_text(
        path.read_text().replace(
            "evaluated by secops and data-analyst before", "evaluated by secops before", 1
        )
    )
    assert_fault(repo, "the description is what happens")


def test_catches_an_evaluator_running_before_the_generator(repo: Path) -> None:
    def mutate(spec: dict) -> None:
        phase = next(p for p in spec["phases"] if p["id"] == 5)
        phase["stages"] = [
            {"agent": "secops", "role": "evaluate"},
            {"agent": "tech-lead", "role": "generate"},
        ]

    edit_spec(repo, mutate)
    assert_fault(repo, "nothing to evaluate")


def test_catches_a_phase_with_no_evaluation_at_all(repo: Path) -> None:
    def mutate(spec: dict) -> None:
        phase = next(p for p in spec["phases"] if p["id"] == 5)
        phase["stages"] = [{"agent": "tech-lead", "role": "generate"}]

    edit_spec(repo, mutate)
    assert_fault(repo, "raw output would reach the CEO")


def test_catches_an_evaluator_who_is_not_assigned_to_that_producer(repo: Path) -> None:
    def mutate(spec: dict) -> None:
        phase = next(p for p in spec["phases"] if p["id"] == 5)
        phase["stages"] = [
            {"agent": "tech-lead", "role": "generate"},
            {"agent": "user-researcher", "role": "evaluate"},
        ]

    edit_spec(repo, mutate)
    assert_fault(repo, "not an assigned evaluator")


def test_catches_an_ungated_phase(repo: Path) -> None:
    def mutate(spec: dict) -> None:
        next(p for p in spec["phases"] if p["id"] == 5).pop("gate")

    edit_spec(repo, mutate)
    assert_fault(repo, "not a phase")


def test_catches_a_brief_routed_to_a_phase_that_does_not_exist(repo: Path) -> None:
    edit_spec(repo, lambda s: s["briefs"]["gtm-launch"].__setitem__("phases", [99]))
    assert_fault(repo, "which is not defined")


def test_catches_a_brief_whose_entry_agent_never_runs(repo: Path) -> None:
    edit_spec(repo, lambda s: s["briefs"]["gtm-launch"].__setitem__("entry_agent", "brand"))
    assert_fault(repo, "starts with an agent that never runs")


def test_catches_an_agent_no_brief_can_reach(repo: Path) -> None:
    """Dead weight on the roster: an agent that exists, has a prompt and a
    model, and would never once be invoked."""
    def mutate(spec: dict) -> None:
        for brief in spec["briefs"].values():
            brief["phases"] = [p for p in brief["phases"] if p != 7]

    edit_spec(repo, mutate)
    assert_fault(repo, "would never run")


def test_catches_the_manual_disagreeing_with_the_roster(repo: Path) -> None:
    manual = repo / "CLAUDE.md"
    manual.write_text(manual.read_text().replace("`content-designer` · ", "", 1))
    assert_fault(repo, "manual and the roster disagree")


def test_catches_a_model_that_is_not_a_real_alias(repo: Path) -> None:
    path = repo / ".claude" / "agents" / "brand.md"
    path.write_text(path.read_text().replace("model: opus", "model: gpt-4", 1))
    assert_fault(repo, "is not an alias")


def test_catches_an_agent_pointed_at_a_file_that_does_not_exist(repo: Path) -> None:
    path = repo / ".claude" / "agents" / "brand.md"
    path.write_text(path.read_text() + "\n\nRead `company/DOES_NOT_EXIST.md` first.\n")
    assert_fault(repo, "which does not exist")


def test_catches_an_entry_agent_that_does_not_actually_run_first(repo: Path) -> None:
    """Not pedantry. Routing a compliance question to a phase that opens with
    the tech lead drafting answers it the wrong way round, and the brief row
    would still have looked correct."""
    edit_spec(repo, lambda s: s["briefs"]["compliance-review"].__setitem__("entry_agent", "tech-lead"))
    assert_fault(repo, "must be the one that actually runs first")


def test_catches_phases_listed_out_of_order(repo: Path) -> None:
    def mutate(spec: dict) -> None:
        spec["phases"] = list(reversed(spec["phases"]))

    edit_spec(repo, mutate)
    assert_fault(repo, "not in ascending order")
