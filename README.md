# math-content-training-app
App to train my kid for Math Competition

## Files

- `app.src.html`: the app source (HTML, CSS and JavaScript in one file)
- `skill_map.json`: the skills, topics and difficulty anchors for each contest
- `math-contest-trainer.html`: the built page that gets published
- `build.py`: builds the page from the two files above

## Build

Edit `app.src.html` or `skill_map.json`, then rebuild:

```bash
python3 build.py          # write math-contest-trainer.html
python3 build.py --check  # fail if the built page is out of date
```

## Figures

Visual skills list the figure types they may use in `skill_map.json` (`"figures": ["grid", "shape"]`).
The generator returns the figure as data, and the app draws it. Types: `grid`, `shape`, `bars`, `table`, `clock`.
The answer check and the tutor read the same data as text, so the picture on screen is the one that was checked.
