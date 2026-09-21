# 🎯 Trivia Night Kit

A Streamlit web app that turns a trivia night setup into print-ready PDFs: team answer sheets, a master scoresheet for the host, and, if you add your questions, an answer key and a host script. Everything is built in neutral grays so it prints crisply on a basic laser printer.

## 🛠️ Features

**Team answer sheets**
- **Layouts:** 4 per page (2×2 with shared cut lines), 2 per page, or 1 per page, on Letter or A4.
- **Answer formats per round:** single column, two columns (song and artist), true/false, multiple choice (2-6 choices), or a picture round with your own images in numbered frames.
- **Scoring details:** points per question (with each sheet's maximum score shown), plus an optional tiebreaker line (closest guess wins) or wager line.
- **Branding:** event name, date, venue and an optional logo in every sheet header.
- **Team labels:** leave the team line blank, pre-print table numbers, or pre-print your team names.
- **Team packets:** with teams listed, the PDF is ordered so that cutting each group of pages gives one stack per team, rounds in order, ready to hand out. "By round" ordering is also available.
- **Ink saver:** outlined headers instead of solid dark bars.
- **Up to 30 questions per round** on the 1-per-page layout (10 on 4-per-page, 25 on 2-per-page).

**Host materials**
- **Master scoresheet:** one row per team, a column per round (with the maximum), plus tiebreak, total and rank.
- **Answer key:** every answer on as few pages as possible.
- **Host script:** every question, answer and note, one round per page.

**Workflow**
- **Live preview:** see the actual rendered page for any round as you change settings.
- **Save and load:** download your whole setup (rounds, questions, team names, logo, pictures) as a `.json` file and load it next week.

## 📥 Adding your questions (optional)

Upload a CSV, or paste rows from a spreadsheet (pasted spreadsheet cells are tab-separated, which works). The first row names the columns:

| column | required | notes |
| --- | --- | --- |
| `round` | yes | The round's name or its position (`1`, `2`, ...) |
| `question` and/or `answer` | at least one | |
| `number` | no | Filled in automatically. Use `TB` or `Bonus` to mark a round's tiebreaker or bonus question |
| `notes` | no | Host-only notes, shown in the host script |

```csv
round,number,question,answer,notes
Geography,1,What is the capital of France?,Paris,
Geography,TB,How many countries are in Africa?,54,Closest guess wins
Name That Tune,1,Play clip 1,Bohemian Rhapsody - Queen,
```

The app warns about rows that match no round and about rounds whose question count doesn't match. **Download a blank template** in the app to get one row per configured question.

## 🖨️ Printing tips
- With **team packets** ordering, every *rounds*-many pages of the PDF form one group of teams (4 teams for the 4-per-page layout). Cut each group along the dashed lines through the whole stack and you get one stack per team.
- Print at **100% / actual size** (not "fit to page") so the cut lines and margins stay put.
- The last group is filled out with unlabelled spare sheets when your team count doesn't divide evenly.

## 🚀 How to Run Locally

### 1. Install System Dependencies
WeasyPrint requires certain underlying system libraries to render PDFs.
- **macOS:** `brew install pango libffi`
- **Linux:** Follow the [WeasyPrint Installation Guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html).
- **Windows:** Install [MSYS2](https://www.msys2.org/) and then, from an MSYS2 shell, run `pacman -S mingw-w64-x86_64-pango`. The app looks for the libraries in `C:\msys64\mingw64\bin`. If MSYS2 lives elsewhere, set the `WEASYPRINT_DLL_DIRECTORIES` environment variable to its `mingw64\bin` folder before starting the app.

### 2. Install Python Packages & Run
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 🧪 Running the Tests
```bash
pip install -r requirements-dev.txt
pytest
```
The PDF and app tests are skipped automatically if WeasyPrint's system libraries aren't available. The full suite takes about a minute, mostly from rendering worst-case packs in every layout.

## 📁 Project Layout
- `app.py`: the Streamlit interface (start it with `streamlit run app.py`).
- `trivia_kit/`: everything else, as an importable package.
  - `models.py`: the event and round data model, with JSON save/load and validation.
  - `sheets.py`: builds the team-sheet HTML (no Streamlit or WeasyPrint dependency).
  - `host.py`: builds the scoresheet, answer key and host script HTML.
  - `questions.py`: parses the questions CSV and writes the template.
  - `images.py`: shrinks and grayscales uploaded pictures for printing.
  - `pdf.py`: renders HTML to PDF and pages to preview images, and sets up the Windows DLL lookup. It is the only module that needs WeasyPrint.
  - `state.py`: maps a saved setup onto the app's widget keys.
- `tests/`: one test module per module above, plus `test_app.py` for the interface.

## 🔒 A note on setup files
A setup file is untrusted input. Loading one clamps every value to its valid range and accepts only inline (`data:image/...`) pictures, so a file can't make the PDF renderer fetch a local file or a web address.
