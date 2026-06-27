import os
# Point WeasyPrint to the MSYS2 library directory
os.environ['WEASYPRINT_DLL_DIRECTORIES'] = r"C:\msys64\mingw64\bin"

import streamlit as st
from weasyprint import HTML

st.set_page_config(page_title="Trivia Sheet Generator", layout="centered")
st.title("🎯 Trivia Answer Sheet Generator")
st.write("Configure your rounds below to export a perfectly aligned 2x2 grid PDF or HTML markup.")

# 1. Global Event Setup
num_rounds = st.number_input("How many rounds total?", min_value=1, max_value=10, value=5)

rounds_data = []

# 2. Dynamic Input Generation
for i in range(int(num_rounds)):
    st.markdown(f"### 📋 Round {i+1}")
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        name = st.text_input(f"Round {i+1} Name", value=f"Round {i+1}", key=f"name_{i}")
    with col2:
        q_count = st.number_input(f"Questions (1-10)", min_value=1, max_value=10, value=10, key=f"q_{i}")
    with col3:
        template_type = st.selectbox(
            "Answer Columns", 
            options=["Single Column", "Two Columns (Music)"], 
            key=f"type_{i}"
        )
    
    is_music = (template_type == "Two Columns (Music)")
    rounds_data.append((name, is_music, q_count))

# 3. Structural Core HTML Assembly Function
def generate_trivia_html(rounds_info):
    html_start = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    *, *::before, *::after { box-sizing: border-box; }
    @page { size: letter landscape; margin: 4mm; background-color: #ffffff; }
    body { margin: 0; padding: 0; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #000000; background-color: #ffffff; }
    .master-grid { width: 100%; max-width: 100%; height: 100vh; border-collapse: collapse; page-break-after: always; table-layout: fixed; }
    .master-grid:last-child { page-break-after: avoid; }
    .grid-cell { width: 50%; height: 50%; vertical-align: top; background-color: #ffffff; border: 2px dashed #718096; padding: 12px 14px; overflow: hidden; position: relative; }
    .grid-cell::before, .grid-cell::after { content: ""; position: absolute; width: 10px; height: 10px; border-color: #4a5568; }
    .grid-cell::before { top: 2px; left: 2px; border-top: 1.5px solid #4a5568; border-left: 1.5px solid #4a5568; }
    .grid-cell::after { bottom: 2px; right: 2px; border-bottom: 1.5px solid #4a5568; border-right: 1.5px solid #4a5568; }
    .sheet-wrapper { width: 100%; height: 100%; }
    .header { background-color: #2d3748; color: #ffffff; padding: 5px; border-radius: 4px; border-bottom: 2px solid #000000; text-align: center; margin-bottom: 6px; }
    .header h1 { margin: 0; font-size: 11pt; text-transform: uppercase; letter-spacing: 1px; }
    .team-info-box { width: 100%; font-size: 8.5pt; display: table; margin-bottom: 6px; }
    .team-info-cell { display: table-cell; vertical-align: middle; }
    .team-info-cell.label { font-weight: bold; color: #000000; width: 14%; }
    .team-info-cell.line { border-bottom: 1px dashed #2d3748; width: 62%; }
    .team-info-cell.score-label { font-weight: bold; color: #000000; text-align: right; padding-right: 5px; width: 15%; }
    .team-info-cell.score-box { border: 2px solid #000000; border-radius: 3px; height: 18px; width: 9%; background-color: white; }
    .answer-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
    .answer-table th { background-color: #1a202c; color: white; padding: 3px 5px; font-size: 8pt; text-transform: uppercase; text-align: left; }
    .answer-table th.num-col { width: 12%; text-align: center; }
    .answer-table th.music-col { width: 44%; }
    .answer-row { page-break-inside: avoid; }
    .answer-row td { padding: 3px 5px; font-size: 8.5pt; border-bottom: 1px solid #cbd5e0; line-height: 1.2; height: 18px; }
    .answer-row td.q-num { font-weight: bold; color: #000000; text-align: center; background-color: #e2e8f0; border-right: 1px solid #cbd5e0; border-left: 1px solid #cbd5e0; }
    .answer-row td.q-ans, .answer-row td.q-music { border-right: 1px solid #cbd5e0; background-color: #ffffff; }
</style>
</head>
<body>
"""
    body_content = ""
    for name, is_music, q_count in rounds_info:
        table_head = """
        <thead><tr><th class="num-col">#</th><th class="music-col">Song Name</th><th>Artist</th></tr></thead>
        """ if is_music else """
        <thead><tr><th class="num-col">#</th><th>Your Answer</th></tr></thead>
        """
        
        rows = ""
        for i in range(1, 11):
            num_content = f"{i}" if i <= q_count else "&nbsp;"
            if is_music:
                rows += f'<tr class="answer-row"><td class="q-num">{num_content}</td><td class="q-music">&nbsp;</td><td class="q-ans">&nbsp;</td></tr>'
            else:
                rows += f'<tr class="answer-row"><td class="q-num">{num_content}</td><td class="q-ans">&nbsp;</td></tr>'
        
        quad_html = f"""
        <div class="sheet-wrapper">
            <div class="header"><h1>{name}</h1></div>
            <div class="team-info-box">
                <div class="team-info-cell label">Team:</div>
                <div class="team-info-cell line"></div>
                <div class="team-info-cell score-label">Score:</div>
                <div class="team-info-cell score-box"></div>
            </div>
            <table class="answer-table">{table_head}<tbody>{rows}</tbody></table>
        </div>
        """
        
        body_content += f"""
        <table class="master-grid">
            <tr><td class="grid-cell">{quad_html}</td><td class="grid-cell">{quad_html}</td></tr>
            <tr><td class="grid-cell">{quad_html}</td><td class="grid-cell">{quad_html}</td></tr>
        </table>
        """
    return html_start + body_content + "</body></html>"

# 4. Action Bars
st.markdown("---")
if st.button("🚀 Compile Trivia Sheets", type="primary"):
    final_html = generate_trivia_html(rounds_data)
    
    # Generate PDF using WeasyPrint
    pdf_bytes = HTML(string=final_html).write_pdf()
    
    st.success("Compilation successful!")
    
    # Downloads
    st.download_button(
        label="📥 Download Print-Ready PDF",
        data=pdf_bytes,
        file_name="trivia_night_pack.pdf",
        mime="application/pdf"
    )
    
    st.download_button(
        label="🌐 Export Raw HTML Code",
        data=final_html,
        file_name="trivia_night_template.html",
        mime="text/html"
    )
    
    with st.expander("👁️ Preview Raw Generated HTML"):
        st.code(final_html, language="html")