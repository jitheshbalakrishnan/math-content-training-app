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
