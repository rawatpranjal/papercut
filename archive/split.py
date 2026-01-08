import PyPDF2
import os
import shutil

def split_pdf(input_path: str, start_page: int, end_page: int, output_path: str):
    """
    Splits a PDF file into a new PDF containing pages from start_page to end_page.

    Parameters:
        input_path (str): Path to the input PDF file.
        start_page (int): Starting page number (1-indexed).
        end_page (int): Ending page number (1-indexed).
        output_path (str): Path to save the output PDF file.
    """
    # Open the PDF file
    with open(input_path, 'rb') as pdf_file:
        reader = PyPDF2.PdfReader(pdf_file)

        # Create a PDF writer object
        writer = PyPDF2.PdfWriter()

        # Add the selected pages to the writer
        for page_num in range(start_page - 1, end_page):  # 0-indexed
            writer.add_page(reader.pages[page_num])

        # Write the new PDF to the output file
        with open(output_path, 'wb') as output_pdf:
            writer.write(output_pdf)

        print(f"Chapter saved: {output_path}")

def main():
    # Input and output folder paths
    input_folder = "input"
    output_folder = "output"

    # Ensure the output folder exists and is emptied
    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)  # Remove all contents of the output folder
    os.makedirs(output_folder, exist_ok=True)

    # Automatically find the first PDF file in the input folder
    input_files = [f for f in os.listdir(input_folder) if f.endswith(".pdf")]
    if not input_files:
        raise FileNotFoundError(f"No PDF files found in the '{input_folder}' folder.")
    input_file = os.path.join(input_folder, input_files[0])  # Select the first PDF file

    # Path to chapters.txt
    chapters_file = "chapters.txt"

    # Check if the chapters file exists
    if not os.path.exists(chapters_file):
        raise FileNotFoundError(f"The file '{chapters_file}' does not exist.")

    # Read the chapters.txt file
    with open(chapters_file, "r") as f:
        chapters = f.readlines()

    # Process each chapter
    for index, line in enumerate(chapters, start=1):
        # Extract chapter details
        parts = line.strip().split()
        if len(parts) < 3:
            print(f"Skipping invalid line: {line}")
            continue

        chapter_name = parts[0]
        try:
            start_page = int(parts[1])
            end_page = int(parts[2])
        except ValueError:
            print(f"Invalid page numbers in line: {line}")
            continue

        # Format the output file name as "01_name.pdf", "02_name.pdf", etc.
        output_file = os.path.join(output_folder, f"{index:02d}_{chapter_name}.pdf")

        # Split the PDF for this chapter
        split_pdf(input_file, start_page, end_page, output_file)

if __name__ == "__main__":
    main()
