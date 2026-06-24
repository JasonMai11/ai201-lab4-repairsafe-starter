import re

from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, VALID_TIERS

_client = Groq(api_key=GROQ_API_KEY)

_SYSTEM_PROMPT = """You are a safety classifier for RepairSafe, a home-repair Q&A assistant. Your only job is
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
REASON: <one sentence explaining why>"""

_TIER_RE = re.compile(r"TIER\s*:\s*\**\s*(\w+)", re.IGNORECASE)
_REASON_RE = re.compile(r"REASON\s*:\s*\**\s*(.+)", re.IGNORECASE)
_FALLBACK_REASON = (
    "Could not parse a valid tier from the classifier response; defaulting to caution as a fail-safe."
)


def classify_safety_tier(question: str) -> dict:
    """
    Classify a home repair question into a safety tier via an LLM-as-judge prompt.

    Sends a single chat completion request (no tools, no history) and parses the
    "TIER: ... / REASON: ..." response. Falls back to "caution" — never "safe" — if the
    response can't be parsed or names a tier outside VALID_TIERS.
    """
    completion = _client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Classify this home repair question:\n\n{question}"},
        ],
    )
    content = completion.choices[0].message.content or ""

    tier = None
    reason = None
    for line in content.splitlines():
        if tier is None:
            match = _TIER_RE.search(line)
            if match:
                tier = match.group(1).lower()
        if reason is None:
            match = _REASON_RE.search(line)
            if match:
                reason = match.group(1).strip()

    if tier not in VALID_TIERS:
        return {"tier": "caution", "reason": _FALLBACK_REASON}

    return {"tier": tier, "reason": reason or ""}
