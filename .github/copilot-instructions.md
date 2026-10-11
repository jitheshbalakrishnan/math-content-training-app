# Review instructions for this repository

This is a single-page practice app for a grade 5-6 student preparing for math contests. Claude writes problems at run time; the page checks, displays and levels them. See `CLAUDE.md` for the full project rules.

When reviewing a pull request, check these first:

1. **Built page is current.** If `app.src.html` or `skill_map.json` changed, `math-contest-trainer.html` must change too and match `python3 build.py`. Flag hand edits to the built page.
2. **Answer check is honest.** Every problem shown must come from `makeProblem`. The second solve runs only when `verify` is on (off by default, the owner's decision). Flag any copy or tutor rule that calls an answer checked or verified when `checked` is false, and any change that weakens the check when it is on.
3. **No copied contest material.** Flag text that looks like a published contest problem, including in prompts, examples and `skill_map.json`.
4. **Figures stay data-driven.** Figures must pass `validFigure` and be drawn by `figureEl`. Flag any rendering of model-written SVG or HTML, and any new figure type without validation and a `figText` branch.
5. **No `innerHTML` with generated or typed text.** Generated problems, tutor replies and parent-entered topics must be inserted as text.
6. **Tutor rule.** `tutorRules` must keep the rule against revealing the answer before the student has answered.
7. **Bounded Claude calls.** No retry loops, no calls on a timer, and a limit on drafts and call time.
8. **State changes are saved and backward compatible.** New fields in learner state need a default in `newState` and must tolerate older saved documents.
9. **Leveling logic.** Changes to `applyResult`, `pickNext`, `nextTarget` or `advance` should state the intended behavior, since there are no automated tests.
10. **Accessibility and layout.** Controls need labels and visible focus, colors must come from the tokens on `:root` (the page is light only, by choice), and nothing may overflow at 400px width.

Prefer specific, verifiable comments over style suggestions. This project has no build tooling beyond `build.py` and no framework, by design.
