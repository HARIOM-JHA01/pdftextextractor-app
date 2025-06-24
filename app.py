import streamlit as st
import os
import time
from dotenv import load_dotenv
from core.extractor import (
    extract_text_level1_pdf,
    extract_text_level2_pdf,
    extract_text_from_docx,
    get_pdf_first_page_preview,
    cleanup_temporary_files,
    UPLOAD_DIR,
    OUTPUT_DIR
)

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

def save_uploaded_file_to_disk(uploaded_file_obj):
    file_path = os.path.join(UPLOAD_DIR, uploaded_file_obj.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file_obj.getbuffer())
    return file_path

def display_file_preview(uploaded_file_obj, saved_path):
    file_extension = os.path.splitext(uploaded_file_obj.name)[1].lower()
    preview_area.empty() 
    with preview_area.expander("File Preview", expanded=True):
        if file_extension == ".pdf":
            st.write(f"Preview of '{uploaded_file_obj.name}' (First Page):")
            preview_image_bytes = get_pdf_first_page_preview(saved_path)
            if preview_image_bytes:
                st.image(preview_image_bytes)
            else:
                st.warning("Could not generate PDF preview.")
        elif file_extension == ".docx":
            st.info(f"'{uploaded_file_obj.name}' (DOCX file) is ready for processing. Preview not available for DOCX.")
        else:
            st.info(f"Uploaded file: '{uploaded_file_obj.name}'. Preview not supported for this file type.")


st.set_page_config(page_title="Document Text Extractor", layout="wide")
st.title("📄 Document Text Extractor")

if "GEMINI_API_KEY_LOADED" not in st.session_state:
    st.session_state.GEMINI_API_KEY_LOADED = bool(GEMINI_API_KEY)

if not st.session_state.GEMINI_API_KEY_LOADED:
    st.warning("GEMINI_API_KEY not found in .env. Level 2 PDF (Image-based) extraction will not be available.")

uploaded_file = st.file_uploader("Upload your PDF or DOCX file", type=["pdf", "docx"], key="file_uploader")

preview_area = st.container()
current_file_path_in_session = None

if uploaded_file:
    if "current_uploaded_filename" not in st.session_state or st.session_state.current_uploaded_filename != uploaded_file.name:
        st.session_state.current_uploaded_filename = uploaded_file.name
        st.session_state.extracted_text = None # Clear previous results for new file
        st.session_state.output_filename = None
        
    current_file_path_in_session = save_uploaded_file_to_disk(uploaded_file)
    display_file_preview(uploaded_file, current_file_path_in_session)


extraction_level_options = ["Level 1 (Direct Text/Selectable PDF)", "Level 2 (Image-based PDF OCR - Slow, uses AI)"]
extraction_method = st.radio(
    "Select Extraction Method:",
    options=extraction_level_options,
    key="extraction_method_radio"
)

submit_button = st.button("Extract Text from Document")

status_messages_area = st.empty()
results_display_area = st.empty()
download_button_area = st.empty()

if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = None
if "output_filename" not in st.session_state:
    st.session_state.output_filename = None

if submit_button and uploaded_file and current_file_path_in_session:
    st.session_state.extracted_text = None
    st.session_state.output_filename = None
    download_button_area.empty()
    results_display_area.empty()
    
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()
    base_filename = os.path.splitext(uploaded_file.name)[0]
    st.session_state.output_filename = f"{base_filename}_extracted.txt"
    
    with st.status("Processing Document...", expanded=True) as status_indicator:
        def progress_updater(message):
            status_indicator.write(message)
            time.sleep(0.05) 

        progress_updater(f"File '{uploaded_file.name}' received. Type: {file_extension.upper()}")
        
        extracted_content = ""
        try:
            if file_extension == ".pdf":
                if extraction_method == extraction_level_options[0]: # Level 1 PDF
                    extracted_content = extract_text_level1_pdf(current_file_path_in_session, progress_updater)
                elif extraction_method == extraction_level_options[1]: # Level 2 PDF
                    if not st.session_state.GEMINI_API_KEY_LOADED:
                        error_msg = "Gemini API Key is required for Level 2 PDF extraction but is not configured."
                        st.error(error_msg)
                        status_indicator.update(label="Configuration Error!", state="error", expanded=True)
                        extracted_content = f"[ERROR: {error_msg}]"
                    else:
                        extracted_content = extract_text_level2_pdf(current_file_path_in_session, progress_updater, GEMINI_API_KEY)
            
            elif file_extension == ".docx":
                if extraction_method == extraction_level_options[1]: # Level 2 selected for DOCX
                    progress_updater("Note: Level 2 (Image-based OCR) is intended for PDFs. For DOCX, standard text extraction will be performed.")
                extracted_content = extract_text_from_docx(current_file_path_in_session, progress_updater)
            
            else:
                extracted_content = "Unsupported file type for extraction."
                progress_updater(extracted_content)

            st.session_state.extracted_text = extracted_content
            if "[Error" in extracted_content or "[ERROR:" in extracted_content :
                 status_indicator.update(label="Extraction Failed or Partially Failed!", state="error", expanded=True)
            else:
                status_indicator.update(label="Extraction Complete!", state="complete", expanded=False)

        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            status_indicator.update(label="Critical Extraction Error!", state="error", expanded=True)
            st.session_state.extracted_text = f"Critical error during extraction: {str(e)}"
        finally:
            if current_file_path_in_session:
                 cleanup_temporary_files(current_file_path_in_session)
                 st.session_state.current_uploaded_filename = None # Mark as processed


if st.session_state.extracted_text is not None:
    results_display_area.subheader("Extracted Text:")
    results_display_area.text_area("Content", st.session_state.extracted_text, height=400, key="text_area_results_display")
    
    if st.session_state.output_filename and not ("[Error" in st.session_state.extracted_text or "[ERROR:" in st.session_state.extracted_text):
        download_button_area.download_button(
            label="Download Extracted Text (.txt)",
            data=st.session_state.extracted_text.encode('utf-8', errors='replace'),
            file_name=st.session_state.output_filename,
            mime="text/plain"
        )

st.markdown("---")
st.markdown("Document Text Extractor v1")