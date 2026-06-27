# 🎯 Trivia Answer Sheet Generator

An interactive, Python-powered Streamlit web app that automatically generates print-ready trivia answer sheets. It formats sheets into a gray-scale optimized 2x2 grid layout on Letter landscape paper with a single shared cutting line down the center.

## 🛠️ Features
- **Custom Round Inputs:** Dynamically configure round names and question counts (1-10).
- **Multiple Answer Formats:** Toggle between a standard single-column field or a dual-column layout tailored for Music rounds (Song Name & Artist).
- **Uniform Grid Sizing:** Forces all sheets to maintain an identical 10-row bounding block height for uniform, balanced packets.
- **Grayscale Optimization:** Built entirely with high-contrast charcoals, whites, and blacks to ensure it prints crisply on basic office laser printers.

## 🚀 How to Run Locally

### 1. Install System Dependencies
WeasyPrint requires certain underlying system library baselines to render PDFs. 
- **macOS:** `brew install pango libffi`
- **Windows / Linux:** Follow the [WeasyPrint Installation Guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html).

### 2. Install Python Packages & Run
```bash
pip install -r requirements.txt
streamlit run app.py