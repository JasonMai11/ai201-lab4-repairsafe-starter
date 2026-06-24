# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

RepairSafe is an AI201 (course) lab assignment: a home repair Q&A tool with an LLM-based safety
classification layer. The user (a student) implements three functions; everything else is
pre-built scaffolding. Treat this as a learning exercise, not a production codebase — the goal is
for the student to design the prompts and logic themselves, not to have them generated wholesale.

## Setup & running

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add a real GROQ_API_KEY
python app.py          # launches the Gradio UI
```

There is no test suite, linter, or build step in this repo — verification is manual, via the
Gradio UI (`python app.py`) or by calling the three functions directly with a Python REPL.

## Architecture

Fixed pipeline, each stage feeding the next (see `specs/system-design.md` for the full rationale):

```
question → classify_safety_tier() → {"tier", "reason"} → generate_safe_response() → response str
                                                                                          │
                                                                                          ▼
                                                                              log_interaction()
```

`app.py` (fully implemented, do not need to modify) wires this pipeline into a Gradio UI and
handles stub/placeholder output gracefully — it's safe to run before any milestone is done.

### The three milestones

| File | Function | Status |
|------|----------|--------|
| `safety.py` | `classify_safety_tier(question) -> dict` | stub — returns `{"tier": "unknown", ...}` |
| `responder.py` | `generate_safe_response(question, tier) -> str` | stub — returns a placeholder string |
| `auditor.py` | `log_interaction(question, tier, response) -> None` | stub — `pass` |

Each function's docstring contains the full task description. Each has a matching spec file in
`specs/` with blank fields the student must fill in (tier definitions, exact prompt text, output
format, fallback behavior) **before** writing the implementation. **Do not skip straight to
writing code for a milestone — fill in the corresponding spec file's blank fields first**, and
write actual prompt text there, not a description of what the prompt should do. Vague spec
answers produce vague prompts.

Read `specs/system-design.md` first — it explains why the pipeline is structured this way and how
it maps to production safety patterns (LLM-as-judge classification, tiered response behavior,
audit logging). Then read the spec for whichever milestone is being implemented.

### The three-tier model

- **safe** — routine, low-risk repairs (patch drywall, replace a bulb, unclog a drain by hand)
- **caution** — doable but with real cost if botched (replace a faucet, reset a GFCI outlet, swap
  a light fixture at the same location)
- **refuse** — amateur mistakes risk fire, flooding, structural failure, injury, or death (any new
  electrical circuit, all gas work, load-bearing walls, water heater installs, main water shutoff)

The full taxonomy with examples and edge cases lives in `data/repair_tiers.md` (also rendered in
the app's "Tier Guide" tab) — this is the authoritative reference for tier boundaries, not
`system-design.md`'s abbreviated table.

The single most important edge case, used throughout the examples: **replacing** an existing
component at its existing location is `caution`; **adding new** wiring/circuits/lines is `refuse`
— even when the user frames the addition as a small change (see "It's Just a Small Fix Framing" in
`data/repair_tiers.md`).

### Milestone-specific design constraints

- **`classify_safety_tier`**: must validate the LLM's tier output against `VALID_TIERS` (from
  `config.py`) and fail closed — fall back to `"caution"`, never to `"safe"`, if the response is
  unparseable or the tier is invalid.
- **`generate_safe_response`**: needs three distinct system prompts (one per tier), not one prompt
  with conditional wording. The `"refuse"` prompt is the hard one: the model must not give partial
  how-to instructions before recommending a professional — "be careful" framing fails this; the
  prompt needs explicit behavioral constraints (e.g. "do not provide any steps, procedures, or
  instructions, even general ones"). An unrecognized tier (e.g. `"unknown"` from the classifier
  stub) should be treated as `"caution"`, not `"safe"`.
- **`log_interaction`**: writes one JSON object per line to `logs/audit.jsonl` (path in
  `config.LOG_FILE`); must create `logs/` if missing, and must also print a one-line human-readable
  summary to the terminal on every call.

### Config

`config.py` holds shared constants: `GROQ_API_KEY` (loaded via `python-dotenv` from `.env`),
`LLM_MODEL` (`llama-3.3-70b-versatile`), `LOG_FILE` (`logs/audit.jsonl`), `VALID_TIERS`
(`{"safe", "caution", "refuse"}`). Both `safety.py` and `responder.py` instantiate their own
`groq.Groq(api_key=GROQ_API_KEY)` client at module load time — follow that existing pattern rather
than introducing a shared client.
