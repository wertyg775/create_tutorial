---
name: checkpoint-quiz
description: Generate self-contained interactive HTML checkpoint quizzes (click-to-answer with explicit A-D letter labels and tick boxes, grading, inline explanations, score bar) from any source — a codebase, files/docs, a markdown topic outline, or any subject the model knows (e.g. operating systems, networking). Optionally emits a printable answer-schema HTML. Use when the user asks for a quiz, checkpoint quiz, test, or self-assessment on a topic, codebase, or file.
---

# Checkpoint Quiz Generator

Produces one self-contained HTML file per quiz: no external assets, inline CSS+JS.
Learner clicks answers, presses **Grade quiz**, sees correct/wrong marks, per-question
explanations, a sticky score bar, and Reset. Target score defaults to 80%.

All paths below are relative to this skill's directory.

## Inputs you may be given

| Input | How to research |
|---|---|
| Codebase, directory, or files | Read architecture docs, README, and the key source files. Quiz mechanisms, invariants, ordering, failure modes — not trivia. Cite `file:symbol` in explanations. |
| Markdown outline (e.g. `os-topics.md`) | Treat headings/sections as quiz sections and topic tags. Quiz one section per file when the user wants per-topic quizzes; the whole outline as sections when they want one big quiz. |
| Bare topic from general knowledge | Use canonical sources (textbooks like OSTEP, RFCs, specs, official docs) from memory. If depth or scope is uncertain, ask for materials or preferences first. |
| An existing quiz file | Treat it as a series: read it to match tone/depth/difficulty and continue numbering ("Checkpoint Quiz 2"). |

## Defaults (confirm only when it genuinely matters)

- 25 questions (reasonable range 10–50); one quiz file per topic/section when the source is an outline
- Difficulty: **working understanding** by default — see the Difficulty section below; always honor an explicit level the user asks for
- Target score 80% (computed automatically by the template JS)
- 4 options (A–D); exactly one best answer; 3–5 options supported
- Sections + topic tags when ≥ 12 questions
- Closed-book phrasing; difficulty per the Difficulty section below, not recall of trivia
- Output location: next to the source material (e.g. `docs/tutorial/<slug>-quiz.html`), or `./<slug>-quiz.html`; `<slug>` = topic-based and series-numbered (`cpu-scheduling-quiz.html`, `checkpoint-quiz-2.html`)

## Difficulty

The user can set the level per quiz ("quiz me on scheduling, problem-solving level").
If unspecified, use **working understanding**. Record the level in `{{QUIZ_META}}` and
`{{QUIZ_INSTRUCTIONS}}` so the learner knows what they're taking.

| Level | Stems test | Example shapes |
|---|---|---|
| **recall** (first pass) | Definitions, vocabulary, recognizing what a mechanism is | "What does X do?", "Which component owns Y?" |
| **working understanding** (default) | Mechanisms, causality, sequences, preconditions, tradeoffs | "What happens when X?", "Which sequence is correct?", "Why does the code do Z?" |
| **problem-solving** (applied) | Scenarios, edge cases, failure recovery, debugging-style reasoning | "Job X holds GPU 1 by UUID; job Y requests GPU 1 by index — what happens?", "A build is interrupted twice already and is interrupted again — what does the worker do?" |

Guidance:
- **problem-solving**: stems describe concrete scenarios, not concepts; distractors are
  plausible wrong conclusions from misapplying a mechanism; explanations walk the
  reasoning chain step by step. This level needs the learner to already have a mental
  model — say so in the instructions.
- **recall**: keep it honest — it checks familiarity, not mastery; pair with a later
  working-understanding quiz on the same material.
- **mixed** (if asked): sections per level, hardest last; tag each question's level via
  the topic-tag span (e.g. `<span class="topic-tag">applied</span>`).
- When the user names a level, every question must genuinely test at that level —
  don't dilute a problem-solving quiz with recall padding.

## Generation steps

1. **Research** the material (list/read files; or rely on the outline / your knowledge for topics).
2. **Draft questions** following the quality checklist below.
3. **Generate the HTML**: copy the template and fill every placeholder exactly once:
   ```bash
   cp assets/quiz-template.html <output>.html
   ```
   Then replace each placeholder with the edit tool (they appear only once each).
4. **Validate** and fix until clean:
   ```bash
   python3 scripts/validate_quiz.py <output>.html
   ```
   It checks markup structure, KEY/WHY lengths vs question count, KEY letters vs option
   counts, JS syntax (`node --check`), and leftover placeholders.
5. **Optional answer schema**: if the user wants a printable key, create `<slug>-quiz-schema.html`
   mirroring the structure of `/home/danish/training-server/docs/tutorial/checkpoint-quiz-schema.html`
   (title, schema banner, per-section `<ol class="schema">` with
   `<li><span class="letter">X.</span><span class="why">reasoning + source</span></li>`).
   Validate the pair: `python3 scripts/validate_quiz.py <output>.html <schema>.html` —
   this asserts schema letters match the quiz KEY exactly.
6. **Report**: file path, question count, sections, target score, how to open it.

## Placeholder reference

| Placeholder | Content |
|---|---|
| `{{QUIZ_TITLE}}` | `<title>` and `<h1>`: "Topic — Quiz N: Sub-area" |
| `{{QUIZ_META}}` | Italic subtitle: unit, question count, closed book |
| `{{QUIZ_INSTRUCTIONS}}` | Inner HTML of the instructions box: goal, what's emphasized, target score, grading how-to |
| `{{QUIZ_QUESTIONS}}` | All quiz markup (see markup contract) |
| `{{QUIZ_KEY}}` | JS string expression, correct letters in question order, one quoted chunk per section with a comment: `("BCBCAD" + /* A */ "ABCCD" /* B */)`. Letters map to option positions A=1st, B=2nd, … |
| `{{QUIZ_WHY}}` | JS array literal, one single-line string per question in order: why the answer is right + the mechanism it tests (+ `file:symbol` for codebase quizzes) |
| `{{QUIZ_FOOTER}}` | Footer HTML: source material credits (files, docs, textbooks) |

## Question markup contract (must match exactly — the JS/CSS depend on it)

```html
<h2>Section A &mdash; Topic area (Q1&ndash;Q6)</h2>
<ol class="questions">

<li class="stem"><span class="topic-tag">tag</span>
<p>Stem text?</p>
<ul class="choices">
  <li>First option</li>
  <li>Second option</li>
  <li>Third option</li>
  <li>Fourth option</li>
</ul>
</li>

</ol>
```

- One `<h2>` + one `<ol class="questions">` per section; Q numbering in `h2` headers is
  continuous across the whole quiz (CSS counters handle labels automatically — do not
  add counter-reset anywhere; the template is already correct).
- Each question `<li>` (class `stem`) contains one optional `<span class="topic-tag">`,
  exactly one stem `<p>`, and one `<ul class="choices">` with 3–5 `<li>` options.
- **Choice UI is explicit by design: every option renders as `(A) [ ] option text` —
  a bold A–D letter followed by a tick box.** The box is injected by the template JS at
  load: it shows a ✓ while the option is picked, then a green ✓ on the correct option
  and a red ✗ on a wrong pick after grading. Never add checkbox/radio markup yourself —
  options must remain plain `<li>text</li>` (the validator enforces the option counts).
- Do not modify the `<style>` or `<script>` blocks.

## Question quality checklist

- Exactly one defensibly best answer; never "all/none of the above", never trick wording.
- Distractors are plausible: common misconceptions, adjacent mechanisms, near-miss details.
- Vary the cognitive level: what happens / why / which sequence / under which condition / which statement is true.
- Stems are answerable closed-book; don't leak the answer in the stem or via earlier questions.
- Explanations teach: mechanism + consequence, not a restatement of the choice text.
- Weight extra questions toward areas the learner says they understand least; tag them.
- For topic quizzes from memory, prefer conceptual depth you're confident in over trivia.

## Reference implementation

The original this skill was extracted from (tone/depth example, codebase deep-dive):
`/home/danish/training-server/docs/tutorial/checkpoint-quiz.html` and its answer schema
`checkpoint-quiz-schema.html`.