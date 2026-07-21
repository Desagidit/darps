# DARPS debugging case studies

Full postmortems of real play bugs. Each shows the observation, the log
diagnosis, the classification, and the layered fix — use them as templates
for writing up new cases (append new ones here).

## Case 1: Mid-conversation character switch

**Observed.** Player interrogating Halloway asked "When was the last time
you saw Sir Edmund alive?" (no addressee). Reply came from Lady Ashworth.

**Log.** The classifier prompt contained the rule "if no explicit
addressee, target the character most recently spoken with" — but nothing in
the prompt said WHO that was. The model guessed a valid character id
(widow), so the engine's only guard (`target not in chars → fallback`)
never fired.

**Class.** Rule without data. A prompt rule the model cannot apply is noise;
the model will fill the gap with a plausible guess.

**Fix (all three layers).**
1. Data: classifier prompt now includes
   `The player is currently in conversation with: <name> (id)`.
2. Contract: classifier schema gained `addressee_named` (true only for an
   explicit name/title/role reference).
3. Deterministic engine: in `_interpret`, mid-conversation +
   `addressee_named` false → target overridden to current partner
   regardless of the model's guess. The LLM classifies; the engine decides.
   Field omitted entirely → defaults true → degrades to trusting the
   classifier (never sticks wrongly).

**Test.** smoke group 9: wrong guess overridden; explicit switch honored;
context line asserted present in the classifier prompt.

## Case 2: Ventriloquizing the player

**Observed.** Character reply opened by rewriting the player's input as
embellished narration: "'I am sorry you have to endure this, sir...' you
say, gauging his reaction" — words and internal states the player never
chose.

**Log.** Character template contained POV rules (no unquoted first-person as
the character) but nothing forbade narrating the PLAYER. The model treated
restating the input as good scene-setting.

**Class.** Missing prohibition. In a game about choosing your words, the
system deciding what you "really" said is a trust-breaking failure, not a
style nit.

**Fix.** Prompt layer only (no critical state involved): explicit rule —
never restate, quote, or embellish the player's words/actions; begin
directly with the character's reaction — including the observed
anti-pattern verbatim as the wrong-example. Concrete examples outperform
abstract rules on small models.

**Test.** Prompt-content assertion in smoke group 9.

## Case 3: First-person POV drift

**Observed.** Character replies written from the character's own viewpoint
("I polish the glasses, avoiding his eye"), confusing whose eyes the player
sees through.

**Log.** Template said "Respond as {name}" — a reasonable model reads that
as writing from {name}'s POV. The world bible's "second person" line applied
to narration and didn't override the stronger local instruction.

**Class.** Ambiguous contract. The instruction was underspecified, not
absent.

**Fix.** Replaced with an explicit frame: the screen shows what the player
character perceives; character speech is first-person INSIDE quotes; all
stage direction is third-person-observed or second-person-player; plus a
wrong/right example pair. Narrator template gained the matching rule and
"never narrate inner thoughts" (which doubles as leak protection — a
narrator that can't see inside heads can't leak intent).

**Escalation path if drift persists on small models.** Cheap regex check for
unquoted sentence-initial "I " in character prose → single regeneration.
Not implemented; try prompt fix first.

## Pattern summary

| Class | Signature | First fix layer |
|---|---|---|
| Rule without data | model "ignores" an instruction it couldn't apply | supply data; engine layer if critical |
| Missing prohibition | model does something never forbidden | rule + wrong/right example |
| Ambiguous contract | instruction read differently than intended | rewrite with explicit frame + examples |
| Gate mismatch | validation strips what the author wanted allowed (or allows the reverse) | pack YAML; extend lint if it should've been caught |
| Engine bug | state transition provably wrong under stubs | code + regression test |
