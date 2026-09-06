import fitz
import asyncio
import sys
import time

def create_300_page_pdf(filename: str):
    doc = fitz.open()
    for i in range(300):
        page = doc.new_page(width=612, height=792)
        page.insert_text(
            (50, 50),
            f"Chapter {(i // 10) + 1}: Sample Chapter Title for Page {i+1}\n\n"
            f"This is section paragraph 1 for page {i+1}. PDF Chatter processes text pages with high accuracy.\n"
            f"Here is some more content to simulate realistic page text payload for testing large PDFs.",
            fontsize=12
        )
    doc.save(filename)
    doc.close()
    print(f"Created {filename} with 300 pages.")

if __name__ == "__main__":
    create_300_page_pdf("test_300_pages.pdf")
