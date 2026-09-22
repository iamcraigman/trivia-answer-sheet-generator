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
- **Import rounds and questions from one file:** build every round — name, format, points, and questions and answers — from a single spreadsheet, instead of configuring each round by hand.

## 📥 Importing rounds and questions from a file

Both importers read the same file shape: one row per question, from an uploaded CSV/TSV or pasted spreadsheet cells (which copy as tab-separated text). The first row names the columns:

| column | required | notes |
| --- | --- | --- |
| `round` | yes | The round's name, or (section 4 only) its position (`1`, `2`, ...) |
| `question` and/or `answer` | at least one, section 4 only | |
| `number` | no | Filled in automatically. Use `TB` or `Bonus` to mark a round's tiebreaker or bonus question |
| `notes` | no | Host-only notes, shown in the host script |
| `format` | no, section 3 only | Single Column, Two Columns (Music), True/False, Multiple Choice, or Picture Round |
| `points` | no, section 3 only | Points per question for that round |
| `choices` | no, section 3 only | Number of options for a Multiple Choice round (2-6) |

**Section 3 — build rounds from scratch.** Upload a file with a `format` column (and optionally `points`/`choices`) and it replaces your current rounds entirely: one round per distinct name, in the order it first appears, with however many rows it has as its question count. It also fills in section 4 below with the same file, so nothing needs uploading twice — a picture round's images still need adding by hand, since a spreadsheet can't carry them. Download an example file from the app to see the shape.

```csv
round,format,points,number,question,answer,notes
Geography,Single Column,1,1,What is the capital of France?,Paris,
Geography,Single Column,1,TB,How many countries are in Africa?,54,Closest guess wins
Name That Tune,Two Columns (Music),2,1,Play clip 1,Bohemian Rhapsody - Queen,
```

**Section 4 — add answers to rounds already configured.** Same shape, without the round-defining columns, matched against the rounds already set up (by name or position) rather than replacing them. The app warns about rows that match no round and about rounds whose question count doesn't match. **Download a blank template** in the app to get one row per configured question.

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
  - `questions.py`: parses the questions CSV, infers whole rounds from a file, and writes the templates.
  - `images.py`: shrinks and grayscales uploaded pictures for printing.
  - `pdf.py`: renders HTML to PDF and pages to preview images, and sets up the Windows DLL lookup. It is the only module that needs WeasyPrint.
  - `state.py`: maps a saved setup onto the app's widget keys.
- `tests/`: one test module per module above, plus `test_app.py` for the interface.

## 🔒 A note on setup files
A setup file is untrusted input. Loading one clamps every value to its valid range and accepts only inline (`data:image/...`) pictures, so a file can't make the PDF renderer fetch a local file or a web address.
