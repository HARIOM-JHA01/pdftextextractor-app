import os
import fitz
from PIL import Image
import io
from langchain_community.document_loaders import PyPDFLoader
import google.generativeai as genai
from docx import Document as DocxDocument

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
TEMP_IMAGE_DIR = os.path.join(OUTPUT_DIR, "temp_images")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_IMAGE_DIR, exist_ok=True)

def configure_gemini_api(api_key):
    genai.configure(api_key=api_key)

def extract_text_level1_pdf(pdf_path, progress_callback):
    progress_callback("Starting Level 1 PDF extraction (selectable text)...")
    progress_callback("Loading PDF document with Langchain...")
    loader = PyPDFLoader(pdf_path)
    
    try:
        documents = loader.load()
    except Exception as e:
        progress_callback(f"Error loading PDF: {e}")
        return f"[Error loading PDF for Level 1: {e}]"
        
    progress_callback(f"PDF loaded into {len(documents)} document sections.")
    
    extracted_text = ""
    for i, doc_chunk in enumerate(documents):
        extracted_text += doc_chunk.page_content + "\n\n"
        progress_callback(f"Extracted text from section {i+1}/{len(documents)}.")
    
    progress_callback("Level 1 PDF extraction complete.")
    return extracted_text

def _extract_text_from_image_with_gemini(image_bytes, model_name="gemini-1.5-flash-latest"):
    model = genai.GenerativeModel(model_name)
    image_part = {"mime_type": "image/png", "data": image_bytes}
    prompt = "Extract all text content from this image. Preserve formatting like paragraphs and line breaks where possible. If there is no text, return an empty string."
    
    try:
        response = model.generate_content([prompt, image_part])
        if response.parts:
            return response.text
        return "" 
    except Exception as e:
        print(f"Gemini API error during image text extraction: {e}")
        return f"[Error extracting text from image via API: {e}]"

def extract_text_level2_pdf(pdf_path, progress_callback, gemini_api_key):
    progress_callback("Starting Level 2 PDF extraction (image-based OCR)...")
    configure_gemini_api(gemini_api_key)
    
    pdf_document = None
    try:
        progress_callback("Opening PDF document using PyMuPDF...")
        pdf_document = fitz.open(pdf_path)
    except Exception as e:
        progress_callback(f"Error opening PDF with PyMuPDF: {e}")
        return f"[Error opening PDF for Level 2: {e}]"

    total_pages = len(pdf_document)
    progress_callback(f"PDF has {total_pages} pages.")
    
    all_pages_text_content = []

    for page_num in range(total_pages):
        current_page_info = f"Page {page_num + 1}/{total_pages}"
        progress_callback(f"Processing {current_page_info}: Starting...")
        try:
            page = pdf_document.load_page(page_num)
            
            progress_callback(f"{current_page_info}: Converting to high-resolution image (300 DPI)...")
            pix = page.get_pixmap(dpi=300) # Using 300 DPI
            img_bytes = pix.tobytes("png")
            
            progress_callback(f"{current_page_info}: Sending image to Gemini for text extraction...")
            page_text = _extract_text_from_image_with_gemini(img_bytes)
            
            if page_text.strip():
                 all_pages_text_content.append(page_text)
            else:
                all_pages_text_content.append(f"[No text found by AI on {current_page_info}]")
            progress_callback(f"{current_page_info}: Text received from Gemini.")

        except Exception as e:
            error_message = f"Error processing {current_page_info}: {e}"
            progress_callback(error_message)
            all_pages_text_content.append(f"[{error_message}]")
            
    if pdf_document:
        pdf_document.close()
        
    progress_callback("Combining text from all pages...")
    final_text = "\n\n--- Page Break ---\n\n".join(all_pages_text_content)
    progress_callback("Level 2 PDF extraction complete.")
    return final_text

def extract_text_from_docx(docx_path, progress_callback):
    progress_callback("Starting DOCX text extraction...")
    try:
        progress_callback(f"Opening DOCX file: {os.path.basename(docx_path)}...")
        document = DocxDocument(docx_path)
        progress_callback("DOCX file opened. Extracting paragraphs...")
        
        full_text = []
        for i, para in enumerate(document.paragraphs):
            full_text.append(para.text)
            if (i + 1) % 20 == 0: # Report progress every 20 paragraphs
                 progress_callback(f"Processed {i+1} paragraphs...")
        
        progress_callback(f"Total {len(document.paragraphs)} paragraphs processed.")
        progress_callback("DOCX extraction complete.")
        return "\n".join(full_text)
    except Exception as e:
        progress_callback(f"Error reading DOCX file: {e}")
        return f"[Error processing DOCX file: {e}]"

def get_pdf_first_page_preview(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        if len(doc) > 0:
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=96) # Lower DPI for preview
            img_bytes = pix.tobytes("png")
            doc.close()
            return img_bytes
        doc.close()
    except Exception as e:
        print(f"Error generating PDF preview: {e}")
    return None

def cleanup_temporary_files(uploaded_file_path=None):
    if uploaded_file_path and os.path.exists(uploaded_file_path):
        try:
            os.remove(uploaded_file_path)
        except Exception as e:
            print(f"Error removing uploaded file {uploaded_file_path}: {e}")

    # Cleanup temp images if any were saved, though current logic passes bytes
    for item_name in os.listdir(TEMP_IMAGE_DIR):
        item_path = os.path.join(TEMP_IMAGE_DIR, item_name)
        try:
            if os.path.isfile(item_path):
                os.remove(item_path)
        except Exception as e:
            print(f"Error removing temp image {item_path}: {e}")