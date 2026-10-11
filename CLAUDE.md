# Math Contest Trainer

A practice app for a grade 5-6 student preparing for Math Kangaroo and the International Math Contest (IMC). It runs as a single page hosted inside Claude. Claude writes each problem, a second Claude call checks the answer, and the app adapts difficulty per skill.

## Files

- `app.src.html`: the whole app (HTML, CSS, JavaScript). Contains the placeholder `__SKILLMAP__`.
- `skill_map.json`: contests, topics, skills, level anchors, the Kangaroo style guide, and which figure types each skill may use.
- `build.py`: embeds the skill map into the source to produce the built page.
- `math-contest-trainer.html`: the built page that gets published. Generated, never edited by hand.

## Build and publish

1. Edit `app.src.html` or `skill_map.json`.
2. Run `python3 build.py`, then `python3 build.py --check`.
3. Commit the source and the built page together.
4. The live page is a Claude artifact published from `math-contest-trainer.html` with the `sample`, `db` and `user` capabilities. Republish to the same artifact so the link and saved progress are kept.

## Rules

- **No copied contest problems.** The Kangaroo style guide was written in our own words from a purchased, copyrighted problem book. Never put that book, its problems, or close paraphrases of them into this repo or into any prompt. Example problems must be original.
- **Every problem passes the answer check before it is shown.** `makeProblem` writes a draft, then a second independent call solves it. A mismatch discards the draft. Do not add a path that skips this.
- **Figures are data, drawn by code.** The generator returns a figure spec (`grid`, `shape`, `bars`, `table`, `clock`). `validFigure` checks it, `figureEl` draws it, and `figText` gives the same data to the answer check and the tutor. Never render model-written SVG or HTML.
- **Model and learner text goes in with `textContent`.** The `h()` helper does this. Do not use `innerHTML` for generated or typed text.
- **The tutor must not reveal an answer before the student has tried.** Keep that rule in `tutorRules`.
- **Leveling stays in plain code.** `applyResult` and `pickNext` decide levels and the next skill. Claude is used for writing, checking and tutoring only.
- **Claude calls are bounded.** At most two drafts per problem, a time limit per call, and no retry loops. Calls start from a learner action.
- **No secrets in the page.** It runs in the viewer's browser.

## Data

- Learner state is one document at `data/users/<id>/state`, mirrored to `localStorage` as a fallback. It includes topics a parent added (`custom`).
- Each answered problem is appended to `data/users/<id>/log/attempts`. Nothing reads this log yet.
- Tutor chats are not saved.

## Skill map conventions

- Skill ids are `topic.name`. Skills added by a parent in the app get `custom.<id>` and live in learner state, not in this file.
- `levels` holds anchors for levels 1, 3 and 5. Levels 2 and 4 are interpolated by the generator.
- `figures` lists the figure types a skill may use. Leave it out for text-only skills.
- To add a contest: add it under `contests`, tag existing skills that overlap, and add new skills for the rest. `build.py` rejects unknown prerequisite ids.

## Testing

There is no test suite yet. Changes have been checked with a headless browser and stand-ins for Claude and storage, which proves the flow but not the quality of real generated problems. Say which of the two a change was tested with.

## Working agreement

- One change per branch, with a pull request into `main`. Do not push to `main` directly.
- Keep user-facing copy plain and short. The reader is 10 or 11 years old.
- The page must work at phone width. It uses one light look in every viewer theme, by the owner's choice, with all colors taken from the tokens at the top of the stylesheet.
