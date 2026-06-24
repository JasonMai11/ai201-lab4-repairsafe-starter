# Spec: `classify_safety_tier()`

**File:** `safety.py`
**Status:** Spec incomplete — fill in all blank fields before implementing

---

## Purpose

Determine whether a home repair question is safe to answer directly, requires a cautionary response, or should be refused with a referral to a licensed professional.

---

## Input / Output Contract

**Input:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |

**Output:** `dict`

| Key | Type | Description |
|-----|------|-------------|
| `"tier"` | `str` | One of: `"safe"`, `"caution"`, `"refuse"` |
| `"reason"` | `str` | One sentence explaining why this tier was assigned |

---

## Design Decisions

*Complete the fields below before writing any code. Use your AI tool in Plan or Ask mode to help you reason through what belongs here — but the decisions are yours.*

---

### Tier definitions

*Write a one-sentence definition for each tier that is precise enough to use as part of your classification prompt. Vague definitions produce inconsistent classifications.*

**safe:**
```
Routine maintenance and low-risk repairs that most homeowners can complete with basic tools and patience. No permit or professional license required. If this repair goes wrong, the worst case is cosmetic damage or a broken fixture — not injury, fire, or flooding.
```

**caution:**
```
Repairs doable for a motivated homeowner, but where mistakes have real cost or mild risk of injury. No permit is typically required, but the repair involves systems — water or electricity — where something can go meaningfully wrong. Stop all new repairs but repairs that only require modification (preferable small) would be ok to proceed.
```

**refuse:**
```
Repairs where an amateur mistake can cause fire, flooding, structural damage, serious injury, or death — or where local building codes require a licensed professional and a permit. Do not provide DIY instructions for these.
```

---

### Classification approach

*How will the LLM classify the question? Will you give it just the tier definitions, or also examples (few-shot)? Will you ask it to reason step-by-step before naming the tier, or output the tier directly?*

*Consider: what happens when a question is genuinely ambiguous — e.g., "can I replace my own outlets?" Which tier should that land in, and how does your approach handle questions at the boundary?*

```
Few-shot (not just definitions). The system prompt includes the tier definitions plus four
worked examples covering all three tiers and the single highest-value contrast (replacing
vs. adding electrical work). The call is still a single chat completion with no tools and
no conversation history (per the function contract) — "few-shot" here means the examples
are embedded as plain text inside the one system message, not delivered as separate
turns.

Direct output, not long chain-of-thought. The boundary rules are crisp enough (especially
once illustrated by examples) that an elaborate reasoning chain isn't needed, and a longer
free-text reasoning section before the tier line increases parsing risk. The model is
asked for the tier first, then exactly one sentence of justification — enough for the
audit log to be useful without inviting rambling.

"Can I replace my own outlets?" is actually NOT ambiguous on the replace/add axis — it
maps directly to the existing "replace an outlet" example, so it's caution. The genuinely
ambiguous case is something like "Can I add a dimmer switch to my dining room?" — "add" is
used loosely in everyday speech to mean both "install a new switch where none exists"
(refuse) and "swap my existing toggle switch for a dimmer" (caution). The prompt handles
this with an explicit default: if a question doesn't clearly state whether a circuit/line
is new or existing, and no other refuse-tier signal is present (gas, panel work,
structural change, water heater, main shutoff), classify it as caution rather than refuse.
Caution is the safer default for genuinely unclear electrical/plumbing scope, because
refuse is reserved for questions that contain a clear, named danger signal — guessing
refuse on pure ambiguity would make the system unhelpfully trigger-happy on ordinary
questions, while guessing caution still surfaces a safety-aware response rather than a
bare "go ahead."
```

---

### Output format

*How will the LLM communicate the tier and reason back to you? Describe the exact text format you'll ask it to use, so you can parse it reliably.*

*The format you used in Lab 3 (`Label: X / Reasoning: Y`) is a reasonable starting point, but you're not required to use it. Whatever you choose, you'll need to parse it in code — so consider how much variation the LLM might introduce and how you'll handle that.*

```
Two labeled lines, nothing else:

TIER: <safe|caution|refuse>
REASON: <one sentence>

Parsing is line-based and case-insensitive: scan the response line by line, and for any
line matching TIER: (after lowercasing) capture the word as the candidate tier;
for any line matching REASON: capture the rest of the line as the reason. This
tolerates the most common LLM deviations — markdown bolding around the keys, extra blank
lines, a trailing period, or text before/after the two lines — without needing a strict
whole-response regex. If no TIER: line is found, or the captured word isn't in
VALID_TIERS, fall back per the "Fallback behavior" section below.

```

---

### Prompt structure

*Write the actual prompt you'll use — both the system message and the user message. Don't describe it — write it. Vague prompt descriptions produce vague prompts, which produce inconsistent classifications.*

**System message:**
```
You are a safety classifier for RepairSafe, a home-repair Q&A assistant. Your only job is
to classify the user's home repair question into exactly one of three safety tiers. Do not
answer the question itself.

Tier definitions:
- safe: Routine, low-risk repairs most homeowners can do with basic tools. No permit or
  license needed. Worst case if done wrong: cosmetic damage or a broken/wasted part — not
  injury, fire, or flooding.
- caution: Repairs that touch electrical or plumbing systems, but only as a like-for-like
  swap, reset, or repair of something that already exists at its current location — no new
  circuits, no new wiring, no new plumbing lines, no opening the electrical panel. Mistakes
  have real cost (a tripped breaker, a leak you can shut off, a damaged part) but are
  recoverable without a professional.
- refuse: Repairs where an amateur mistake can cause fire, flooding, structural failure,
  serious injury, or death, or where the work legally requires a permit or licensed
  professional. This always includes: any new electrical circuit or outlet, any electrical
  panel or service-entrance work, ALL gas line or gas appliance work, removing or altering
  any wall without confirmed non-load-bearing status, water heater installation or
  replacement, replacing a main water shutoff valve, and new plumbing lines run to a new
  location.

The single most important distinction: REPLACING an existing component at its existing
location is "caution." ADDING new wiring, a new circuit, or a new plumbing line to a new
location is "refuse" — even if the user describes it as small or simple. Classify based on
what the work actually requires, not how the user frames it. Any mention of gas is always
"refuse," with no exceptions.

If a question doesn't clearly state whether something is being replaced or newly added,
and no other refuse-tier signal is present (no gas, no panel work, no structural change, no
water heater, no main shutoff), classify it as "caution" rather than "refuse."

Examples:
Q: "How do I patch a small hole in drywall?"
TIER: safe
REASON: Cosmetic, low-risk repair with no specialized tools or systems involved.

Q: "How do I replace an outlet that stopped working?"
TIER: caution
REASON: Like-for-like swap on an existing circuit at the same location.

Q: "Can I add a new outlet to my garage?"
TIER: refuse
REASON: Adding an outlet requires running a new circuit from the panel, which is a fire
risk if done incorrectly.

Q: "How do I fix a gas line that smells like it's leaking?"
TIER: refuse
REASON: Any gas line work is always refuse due to fire, explosion, and CO poisoning risk.

Respond with exactly two lines and nothing else:
TIER: <safe|caution|refuse>
REASON: <one sentence explaining why>
```

**User message:**
```
Classify this home repair question:

{question}
```

---

### Caution/refuse boundary

*The most consequential classification decision is whether a question lands in "caution" or "refuse." Write down your rule for this boundary — one sentence. Then give two examples of questions that sit close to the line and explain which side they fall on and why.*

```
Rule: if the repair requires opening the electrical panel, running new wire/circuits or
new plumbing lines to a location that doesn't already have them, or involves gas in any
way, it's refuse; if it's a like-for-like swap, reset, or repair of something already
installed at its current location, it's caution.

Example 1 — "How do I replace an existing wall switch with a smart switch in the same
location?" → caution. The switch already exists at that location; this is a same-circuit
component swap, not new wiring.

Example 2 — "How do I add a smart switch to control a light that currently has no switch?"
→ refuse. No switch exists at that location, so wiring it requires running new wire back
to the circuit — the exact "adding new" pattern that defines refuse, even though the
visible end result (a smart switch on a wall) looks identical to Example 1.
```

---

### Fallback behavior

*What does your function return if the LLM response can't be parsed — e.g., if it produces free-form prose instead of your expected format? What happens when tier validation against `VALID_TIERS` fails?*

*Note: failing open (returning "safe" as a fallback) is more dangerous than failing closed (returning "caution"). Which makes more sense here, and why?*

```
If no TIER: line can be found in the response, or the captured word is not in
VALID_TIERS, the function returns {"tier": "caution", "reason": "Could not parse a valid
tier from the classifier response; defaulting to caution as a fail-safe."} rather than
raising or returning "safe."

Failing closed to "caution" (not "safe") is the right call: "safe" tells the responder to
answer with zero safety framing, so a parse failure on a question that was actually
refuse-tier would silently produce dangerous, unqualified instructions. "Caution" is the
safer default because the responder always attaches warnings and a professional-review
recommendation at that tier — worst case on a true "safe" question is an unnecessary
caveat, not a missed danger signal. We don't default all the way to "refuse" either,
because that tier declines to give instructions at all; defaulting every parse failure to
a hard refusal would make the system unhelpfully brittle any time the LLM has a minor
formatting slip on an ordinary question.
```

---

## Implementation Notes

*Fill this in after implementing, before moving to Milestone 2.*

**One classification that surprised you — question, tier you expected, tier it returned, and why:**

```
[your answer here]
```

**One prompt change you made after seeing the first few outputs, and what it fixed:**

```
[your answer here]
```
