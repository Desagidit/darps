---
name: playtest-debug
description: Diagnose and fix DARPS runtime misbehavior observed in play — characters leaking or withholding wrongly, wrong perspective/POV, wrong conversation target, hallucinated or missing discoveries, hints too eager or absent, tone/track weirdness, broken events JSON, or any "the game did something odd" report, including pasted gameplay transcripts. Use this BEFORE editing any prompt or engine file in response to observed play, even if the cause looks obvious.
---

# Debugging DARPS play behavior

Prime fact: nearly every play bug so far has been a **prompt-contract
failure**, not an engine failure — the state machine did what it was told;
the telling was flawed. Resist jumping to code.

## Procedure

1. **Read the log first.** `logs/calls.jsonl` has every call: tag
   (`classifier` / `character:<id>` / `narrator`), full prompt, full
   response. Find the exact turn; read what the model was actually given and
   what it actually returned. Useful one-liner:
   `python -c "import json,sys;[print(json.dumps(json.loads(l),indent=1)[:2000]) for l in open('logs/calls.jsonl') if '<tag>' in l]"`
2. **Localize the layer.**
   - Wrong tone/topics, missed meta/injection screening → classifier call
     (`_interpret`). Note: targets are HOST-supplied; the engine never picks
     an addressee, so "talked to the wrong character" is a host-call bug.
   - Wrong words/behavior from a character → character call.
   - Wrong discovery/scenery/POV in narration → narrator call + engine
     authorization (`_authorized_discoveries`).
   - Prose said X but state shows Y → that's validation WORKING (stripped
     event); the fix is upstream (why did the model propose it?) or in
     gating, not in validate.py.
3. **Classify the failure.**
   - **Rule without data**: template states a rule the model lacks inputs to
     apply. Fix: supply the data; add deterministic engine enforcement if
     the behavior is critical.
   - **Missing prohibition**: model does something never forbidden. Fix: add
     the rule WITH a concrete wrong/right example (small models need the
     example more than the rule).
   - **Gate mismatch**: content gates don't express the author's intent
     (threshold too high, missing trigger synonym, requires wrong). Fix in
     pack YAML; check whether lint should have caught it — if yes, extend
     lint.
   - **Genuine engine bug**: state transition wrong. Rare; prove it with a
     stub test before fixing.
4. **Fix at the right layer** (data → prompt → engine), then add a smoke-test
   group reproducing the failure. For prompt fixes, assert the new
   instruction or data string appears in assembled prompts.
5. **Generalize**: if the fix helps every pack, it belongs in
   `darps/prompts/` defaults or the engine — not a pack override.

## Worked cases (read `references/case-studies.md` for full detail)

- Character switched mid-conversation → classifier told to "default to
  current partner" but never given who that was; fixed by supplying
  `in_conversation_with` + `addressee_named` field + deterministic engine
  stickiness. Rule-without-data.
- Replies narrated the player's own words/feelings ("...you say, gauging his
  reaction") → no prohibition existed; fixed with an explicit
  never-ventriloquize rule + wrong/right example. Missing prohibition.
- First-person character narration confusing POV → "respond as X" read as
  X's viewpoint; fixed by specifying the frame (speech quoted first-person;
  ALL stage direction third-person-observed or second-person-player).

## Small-model calibration

When the configured model is small/local (o4-mini, 8B class): expect events
JSON drift (extract_json is lenient; check what it salvaged), rubric drift on
story_relevance (audit a session's values in the log before retuning hint
thresholds), and instruction-following that needs examples over rules. Fixes
must degrade gracefully: safe defaults for omitted fields, never
stuck-states.
