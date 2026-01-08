
import os
import PyPDF2
import openai
from tqdm import tqdm
import re

def read_api_key():
    try:
        with open('key.txt', 'r') as f:
            return f.read().strip()
    except Exception as e:
        raise ValueError(f"Error reading API key from 'apikey.txt': {e}")

api_key = read_api_key()
openai.api_key = api_key

def get_openai_response(prompt, model="gpt-4-turbo", temperature=0.1):
    try:
        response = openai.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature
        )
        content = response.choices[0].message.content
        # Replace double backslashes with single backslashes
        content = content.replace('\\\\', '\\')
        return content
    except Exception as e:
        print(f"Error: {e}. Skipping this response.")
        return None

def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, "rb") as file:
        reader = PyPDF2.PdfReader(file)
        for page in reader.pages:
            text += page.extract_text()
    if not text.strip():
        raise ValueError(f"No text extracted from {pdf_path}.")
    return text

def clean_latex_summary(summary):
    # Remove unwanted LaTeX document-level commands
    summary = re.sub(r"\\documentclass.*?\n", "", summary, flags=re.DOTALL)
    summary = re.sub(r"\\usepackage.*?\n", "", summary, flags=re.DOTALL)
    summary = re.sub(r"\\geometry.*?\n", "", summary)
    summary = re.sub(r"\\title.*?\n", "", summary)
    summary = re.sub(r"\\author.*?\n", "", summary)
    summary = re.sub(r"\\date.*?\n", "", summary)
    summary = re.sub(r"\\maketitle", "", summary)
    summary = re.sub(r"\\begin\{document\}", "", summary)
    summary = re.sub(r"\\end\{document\}", "", summary)
    summary = re.sub(r"```latex", "", summary)  # Remove markdown-like fences
    summary = re.sub(r"```", "", summary)       # Remove any code fences

    # Replace section headers with subsubsection headers for summaries
    summary = summary.replace("\\section*{", "\\subsubsection*{")

    # Replace curly quotes with straight quotes
    summary = summary.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')

    # Replace em-dashes and en-dashes with LaTeX equivalents
    summary = summary.replace("—", "---").replace("–", "--")

    # Escape problematic LaTeX characters (excluding backslashes)
    # Only escape if not already escaped
    summary = re.sub(r'(?<!\\)([%$&#_^~])', r'\\\1', summary)

    # Remove optional arguments in itemize and enumerate environments
    summary = re.sub(r'\\begin{itemize}\[.*?\]', r'\\begin{itemize}', summary)
    summary = re.sub(r'\\begin{enumerate}\[.*?\]', r'\\begin{enumerate}', summary)

    # Remove any extra spaces or empty lines
    summary = re.sub(r'\n\s*\n', '\n\n', summary)

    return summary.strip()

def validate_latex(latex_content):
    # Quick validation for unmatched braces
    open_braces = latex_content.count("{")
    close_braces = latex_content.count("}")
    if open_braces != close_braces:
        raise ValueError(f"Unmatched braces in LaTeX content. Open: {open_braces}, Close: {close_braces}")

def summarize_text_with_gpt(text, chapter_name):
    prompt = f"""
    You are a technical summarizer creating a detailed LaTeX report for a chapter, for a stats/ml expert.
    Based on the content of the chapter titled '{chapter_name}', generate a 1-page summary formatted in LaTeX:

    If the chapter is introductory/overview:
    1. Provide a motivating example in 1 rich paragraph. If the example is in the chapter use that. 
    2. Include a comprehensive laundry list of solutions or methods in concise bullet points. Add sub-bullets if needed.
    3. Do not add any conclusion. 

    If the chapter is a deep dive into a problem:
    1. State the problem the chapter is trying to resolve.
    2. Provide a motivating example with rich context (1 paragraph). If the example is in the chapter use that. 
    3. Present the solutions as detailed bullets (each bullet should be 2–3 lines). Add sub-bullets if needed.
    4. Do NOT add any generic conclusion. 

    Do NOT use textbf. Keep headers short. Do not refer to the chapter "Chapter X say...", or "Chapter Y delves...")
    Ensure the summary fits within a single page and uses only valid LaTeX commands. Do not include any markdown code fences or markdown formatting. Only output valid LaTeX code. Replace all headers with \\subsubsection* except for chapter titles. Do not use any optional arguments in LaTeX environments.

    Chapter Text:
    {text}
    """
    raw_summary = get_openai_response(prompt)
    if raw_summary:
        return clean_latex_summary(raw_summary)
    else:
        raise ValueError(f"Failed to generate summary for chapter '{chapter_name}'.")

def create_latex_summary(summaries):
    latex_content = r"""\documentclass{article}
\usepackage[a4paper,margin=1in]{geometry}
\usepackage{hyperref}
\usepackage{amsmath}
\usepackage{enumitem}  % Include enumitem package
\begin{document}
"""
    for chapter_name, summary in summaries.items():
        latex_content += f"\\section*{{{chapter_name.replace('_', ' ').title()}}}\n"
        latex_content += summary + "\n\n"

    latex_content += r"\end{document}"
    validate_latex(latex_content)
    return latex_content

def main():
    output_folder = "output"
    latex_file = "summary.tex"

    if not os.path.exists(output_folder):
        raise FileNotFoundError(f"The output folder '{output_folder}' does not exist.")
    pdf_files = sorted(f for f in os.listdir(output_folder) if f.endswith(".pdf"))

    summaries = {}
    with tqdm(pdf_files, desc="Processing PDFs", unit="file") as progress_bar:
        for file_name in progress_bar:
            chapter_name = os.path.splitext(file_name)[0]
            pdf_path = os.path.join(output_folder, file_name)
            progress_bar.set_postfix({"Processing": chapter_name})
            try:
                text = extract_text_from_pdf(pdf_path)
                summary = summarize_text_with_gpt(text, chapter_name)
                summaries[chapter_name] = summary
            except Exception as e:
                print(f"[Error] Skipping {chapter_name}: {e}")
                continue

    latex_content = create_latex_summary(summaries)
    with open(latex_file, "w") as file:
        file.write(latex_content)

    print(f"\nSummary saved to {latex_file}")

if __name__ == "__main__":
    main()