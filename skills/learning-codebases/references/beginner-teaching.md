# Beginner Teaching

Use this reference when the learner encounters unfamiliar syntax, frameworks, architecture, non-Python code, or confusion.

## Assumed knowledge

Assume only variables, conditions, loops, functions, basic classes, and imports. Define other concepts before relying on them.

## Teach in four levels

| Level | Explain |
|---|---|
| 1 — Role | The problem solved and where this unit sits |
| 2 — Flow | Input, process, output, upstream, downstream |
| 3 — Implementation | Functions/classes, branches, state, errors |
| 4 — Code detail | Syntax, parameters, returns, alternatives |

Default to level 2. Move deeper when the learner asks, predicts correctly, or needs implementation confidence. Move up one level when the learner is lost.

## Introduce a new term

Use this order:

1. One plain-language definition.
2. The problem it solves.
3. Its real location in this project.
4. A minimal Python analogy when useful.
5. Where the analogy becomes inaccurate.

Do not front-load a glossary. Define terms just in time.

## Explain meaningful code blocks

Group lines by purpose rather than translating line by line:

- State before execution.
- Decision or transformation.
- State after execution.
- Next control or data destination.

Quote only the lines needed for the lesson. Keep the real path and symbol visible.

## Explain non-Python code

First explain the language-independent responsibility. Then map it to familiar Python, state the mismatch, and return to the real implementation.

Never claim that TypeScript interfaces, Java annotations, JavaScript promises, Go goroutines, Rust ownership, or similar constructs are identical to their nearest Python analogy.

## Adapt to the learner

- **Correct:** confirm briefly and continue downstream.
- **Partially correct:** preserve the correct part, name one missing relationship, and ask one focused follow-up.
- **Stuck:** narrow the scope, move up one level, use a concrete input or minimal Python example, then return to the repository.

Do not repeat the same explanation with cosmetic rewording.

## Keep interaction efficient

- Ask one learner-check question at a time.
- Do not repeat the complete project map in every answer.
- Use one concrete flow before introducing alternatives.
- Offer deeper detail instead of delivering every layer immediately.
- Never shorten an explanation by removing decisive evidence or hiding uncertainty.

When the user asks for a quick factual answer, answer directly and offer the learning loop rather than forcing a quiz.
