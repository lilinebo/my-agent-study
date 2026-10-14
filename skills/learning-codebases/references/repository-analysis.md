# Repository Analysis

Use this reference for the first inspection of a repository, when the active path is uncertain, or when saved project knowledge may be stale.

## 1. Establish the boundary cheaply

Confirm before deep reading:

- Real project root and repository instructions such as `AGENTS.md`.
- Git branch, revision, and dirty state when applicable.
- README, manifests, startup commands, build/test entry points, and primary languages.
- Source, tests, configuration, data, generated code, vendored code, caches, artifacts, and model weights.

Prefer `rg --files`, targeted `rg`, manifest inspection, and shallow directory views. Exclude generated, vendored, cached, and large binary/data paths unless the learning goal depends on them.

## 2. Select a depth mode

| Mode | Deliverable | Expand when |
|---|---|---|
| Quick | Purpose, active entry, one flow, unknowns | The user asks why/how or evidence conflicts |
| Standard | Compass, one supported flow, key concepts, checkpoint | A downstream relationship remains unclear |
| Deep | Alternatives, tests, errors, runtime behavior, more subsystems | The user's goal requires implementation confidence |

Use Standard unless the user chooses otherwise.

## 3. Find the active path

Rank evidence in this order:

1. Startup or runtime command actually used.
2. Active configuration and dependency wiring.
3. Tests that execute the path.
4. Imports, callers, registrations, and runtime composition.
5. README and design documentation.
6. Comments, names, and directory placement.

When candidates conflict, show a small table with candidate, evidence, and current judgment. Do not call a plausible filename active without wiring evidence.

## 4. Build a compact project compass

Include only:

- One-sentence purpose.
- External input and final output.
- Active entry point and evidence.
- Five to twelve important modules and their relationships.
- Relevant online/offline, frontend/backend, or training/inference split.
- Deterministic code versus model, agent, or human judgment when applicable.
- Confirmed facts, inferences, unknowns, and the recommended first flow.

Do not enumerate the whole repository.

## 5. Trace one real flow

Prefer a user-visible or data-producing scenario:

```text
input -> entry -> orchestration -> core logic -> data structure
      -> external adapter/dependency -> output -> relevant test
```

At each stop record:

- Real path and symbol.
- Input state.
- Meaningful decision or transformation.
- Output state.
- Next destination.

Read one dependency hop at a time. Expand only when the current claim needs it.

## 6. Manage context

- Reuse the compass and verified findings while the revision is unchanged.
- Search for a symbol before reopening broad files.
- Avoid rereading unchanged files unless a new question needs different lines.
- Summarize established facts instead of pasting large excerpts.
- Prefer exact short excerpts only when syntax or branching is the lesson.

Stop the pass when the immediate question has path/symbol support, the next learning step is clear, and additional reading is unlikely to change the conclusion. State the stop reason and what would justify deeper inspection.

## 7. State the evidence level

- **Code-confirmed:** directly visible in current code and wiring.
- **Runtime-confirmed:** observed through a command, test, log, or process in this session.
- **Documented:** stated by project docs but not independently verified.
- **Inferred:** reasoned from evidence.
- **Unknown:** requires missing files, environment, credentials, data, or execution.

If the project cannot run, separate static confirmation, runtime requirements, missing prerequisites, the smallest safe check, and remaining unknowns.

## 8. Protect the target project

Stay read-only unless the user separately asks for a change. Never place private code or identifiers into web searches. Do not install dependencies, call production systems, or write a learning journal as an implicit part of explanation.
