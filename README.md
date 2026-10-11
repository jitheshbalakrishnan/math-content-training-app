# math-content-training-app
App to train my kid for Math Competition

## Files

- `src/index.html`: the page shell, with slots for the styles and scripts
- `src/css/`: the styles, in three files
- `src/js/`: the scripts, one file per area of the app
- `skill_map.json`: the skills, topics and difficulty anchors for each contest
- `math-contest-trainer.html`: the built page that gets published. Generated, never edited by hand.
- `build.py`: assembles the built page from everything above

| Script | What it holds |
|---|---|
| `01-setup.js` | The skill map, constants and small helpers |
| `02-state.js` | Learner state, loading and saving |
| `03-leveling.js` | Level changes and choosing the next skill |
| `04-figures.js` | Figure checking and drawing |
| `05-problems.js` | Prompts, draft checks, and writing problems |
| `06-practice-flow.js` | Placement, answering, retries, moving on |
| `07-tutor.js` | The tutor chat |
| `08-view-practice.js` | The practice screen |
| `09-view-progress.js` | The progress screen |
| `10-scratchpad.js` | The scratchpad |
| `11-mock-tests.js` | Timed mock tests |
| `12-parents.js` | The Parents tab |
| `13-main.js` | Screen switching and startup |

The scripts are pasted together in file-name order and share one scope, so a file can use anything defined in an earlier file. There are no imports.

## Build

Edit files under `src/` or `skill_map.json`, then rebuild:

```bash
python3 build.py          # write math-contest-trainer.html
python3 build.py --check  # fail if the built page is out of date
```

## Figures

Visual skills list the figure types they may use in `skill_map.json` (`"figures": ["grid", "shape"]`).
The generator returns the figure as data, and the app draws it. Types: `grid`, `shape`, `bars`, `table`, `clock`.
The answer check and the tutor read the same data as text, so the picture on screen is the one that was checked.
