# Math Contest Trainer

A practice app for a grade 5-6 student preparing for Math Kangaroo, the International Math Contest (IMC) and the CREST Mathematics Olympiad (CMO). It runs as a single page hosted inside Claude. Claude writes each problem, a second Claude call can check the answer (a setting, off by default), and the app adapts difficulty per skill.

## Files

- `src/index.html`: the page shell, with a slot for styles and a slot for scripts.
- `src/css/*.css` and `src/js/*.js`: the styles and scripts, pasted in by file-name order. The numbers at the start of each name set the order. The scripts share one scope and have no imports, so a file may use anything defined in an earlier file. The README lists what each script holds.
- `skill_map.json`: contests, topics, skills, level anchors, style guides, paper layouts, and which figure types each skill may use. `src/js/01-setup.js` contains the placeholder `__SKILLMAP__`.
- `build.py`: assembles the built page.
- `math-contest-trainer.html`: the built page that gets published. Generated, never edited by hand.

## Build and publish

1. Edit files under `src/` or `skill_map.json`.
2. Run `python3 build.py`, then `python3 build.py --check`.
3. Commit the source and the built page together.
4. The live page is a Claude artifact published from `math-contest-trainer.html` with the `sample`, `db` and `user` capabilities. Republish to the same artifact so the link and saved progress are kept.

## Rules

- **No copied contest problems.** The Kangaroo and CREST style guides were written in our own words from a purchased, copyrighted problem book and a copyrighted sample paper. Never put those sources, their problems, or close paraphrases of them into this repo or into any prompt. Example problems must be original.
- **The answer check is optional and off by default, by the owner's decision.** When `verify` is on in learner state (Parents tab), `makeProblem` has a second independent call solve each draft and discards it on a mismatch. When it is off, drafts are shown as written, each problem is marked `checked: false`, and the tutor is told the key is unchecked. Never tell the student an answer was checked when it was not. `cleanProblem` always validates the draft's structure.
- **Figures are data, drawn by code.** The generator returns a figure spec (`grid`, `shape`, `bars`, `table`, `clock`). `validFigure` checks it, `figureEl` draws it, and `figText` gives the same data to the answer check and the tutor. Never render model-written SVG or HTML.
- **Model and learner text goes in with `textContent`.** The `h()` helper does this. Do not use `innerHTML` for generated or typed text.
- **The tutor must not reveal an answer before the student has tried.** Keep that rule in `tutorRules`.
- **Leveling stays in plain code.** `applyResult` and `pickNext` decide levels and the next skill. Claude is used for writing, checking and tutoring only.
- **Claude calls are bounded.** At most two drafts per problem, a time limit per call, and no retry loops. Calls start from a learner action.
- **Mock tests measure, practice teaches.** A mock test gives no hints, tutor or feedback until it ends, takes its remaining time from the stored end time, and never changes skill levels.
- **No secrets in the page.** It runs in the viewer's browser.

## Data

- Documents read from the database are frozen. Clone them before using them as working state (`loadState`, `loadMock`), or changes are silently ignored.
- Learner state is one document at `data/users/<id>/state`, mirrored to `localStorage` as a fallback. It includes topics a parent added (`custom`).
- Each answered problem is appended to `data/users/<id>/log/attempts`. Nothing reads this log yet.
- Tutor chats are not saved.
- Learner state also holds `days` (problems answered per local day, about four months) and `goals` (daily and weekly). The daily set, the weekly total and the streak are read from `days`.
- A mock test in progress or just finished is one document at `data/users/<id>/mock`, also mirrored to `localStorage`. The last 20 results are kept in learner state as `mocks`.

## Skill map conventions

- Skill ids are `topic.name`. Skills added by a parent in the app get `custom.<id>` and live in learner state, not in this file.
- `levels` holds anchors for levels 1, 3 and 5. Levels 2 and 4 are interpolated by the generator.
- `figures` lists the figure types a skill may use. Leave it out for text-only skills.
- A contest entry may carry `short` (display name), `choices` (4 or 5 answer choices), `style` (rules, tiers with levels, original examples) and `paper` (minutes, unit, sections) for mock tests. A contest without a `paper` borrows Kangaroo's.
- `extra: true` marks a skill that is practised but is not in the contest's own syllabus, so mock tests leave it out.
- To add a contest: add it under `contests`, tag existing skills that overlap, and add new skills for the rest. `build.py` rejects unknown prerequisite ids.

## Testing

There is no test suite yet. Changes have been checked with a headless browser and stand-ins for Claude and storage, which proves the flow but not the quality of real generated problems. Say which of the two a change was tested with.

## Working agreement

- One change per branch, with a pull request into `main`. Do not push to `main` directly.
- The look is the workbook: squared paper, navy ink, the yellow highlighter. Progress borrows a training log's content (best mock test, weekly goal, practice days, streak). Celebrations stay short, play once, and respect reduced motion. No points, XP or mascot.
- The student's navigation is Home, Practice, Mock test, Progress. Parent settings live behind the footer link.
- Keep user-facing copy plain and short. The reader is 10 or 11 years old. Use American spelling (practice, color).
- The page must work at phone width. It uses one light look in every viewer theme, by the owner's choice, with all colors taken from the tokens at the top of the stylesheet.
