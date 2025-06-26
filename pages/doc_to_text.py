import streamlit as st
import os
import time
from dotenv import load_dotenv
from core.extractor import (
    DocumentProcessor,
    ExtractorFactory,
    get_pdf_first_page_preview,
    cleanup_temporary_files,
    UPLOAD_DIR
)
from core.config import GeminiConfig, OpenAIConfig
from core.history_manager import HistoryManager

class DocumentToTextUI:
    def __init__(self):
        self.processor = DocumentProcessor()
        self.history_manager = HistoryManager()
        self.gemini_config = GeminiConfig()
        self.openai_config = OpenAIConfig()
    
    def save_uploaded_file_to_disk(self, uploaded_file_obj):
        file_path = os.path.join(UPLOAD_DIR, uploaded_file_obj.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file_obj.getbuffer())
        return file_path
    
    def display_file_preview(self, uploaded_file_obj, saved_path, preview_area):
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
    
    def display_api_key_status(self):
        st.sidebar.subheader("API Key Status")
        
        gemini_status = "✅ Available" if self.gemini_config.is_available() else "❌ Not Configured"
        openai_status = "✅ Available" if self.openai_config.is_available() else "❌ Not Configured"
        
        st.sidebar.markdown(f"**Gemini API**: {gemini_status}")
        st.sidebar.markdown(f"**OpenAI API**: {openai_status}")
        
        if not self.gemini_config.is_available() and not self.openai_config.is_available():
            st.sidebar.warning("No AI service API keys found. Add to .env file.")
    
    def show(self):
        st.title("📄 Convert PDF/Word to Text")
        
        self.display_api_key_status()
        
        with st.sidebar:
            st.subheader("Recent Documents")
            recent_files = self.history_manager.get_recent_files("pdf_to_text")
            if recent_files:
                st.write("Recently processed:")
                for file in recent_files:
                    st.write(f"- {file}")
            else:
                st.write("No recent documents")
        
        uploaded_file = st.file_uploader("Upload your PDF or DOCX file", type=["pdf", "docx"], key="doc_file_uploader")
        
        preview_area = st.container()
        current_file_path_in_session = None
        
        if uploaded_file:
            if "current_uploaded_filename" not in st.session_state or st.session_state.current_uploaded_filename != uploaded_file.name:
                st.session_state.current_uploaded_filename = uploaded_file.name
                st.session_state.extracted_text = None
                st.session_state.output_filename = None
                
            current_file_path_in_session = self.save_uploaded_file_to_disk(uploaded_file)
            self.display_file_preview(uploaded_file, current_file_path_in_session, preview_area)
        
        if current_file_path_in_session:
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            
            extraction_options = {
                "langchain": "Custom Algo (Langchain)"
            }
            
            if self.gemini_config.is_available():
                extraction_options.update(
                    {f"gemini_{model_id}": f"Gemini: {model_name}" 
                     for model_id, model_name in self.gemini_config.get_models().items()}
                )
            
            if self.openai_config.is_available():
                extraction_options.update(
                    {f"openai_{model_id}": f"OpenAI: {model_name}" 
                     for model_id, model_name in self.openai_config.get_models().items()}
                )
            
            extractor_type = st.selectbox(
                "Select Extraction Method:",
                options=list(extraction_options.keys()),
                format_func=lambda x: extraction_options[x],
                key="extraction_method_select"
            )
            
            submit_button = st.button("Extract Text from Document")
            
            status_messages_area = st.empty()
            results_display_area = st.empty()
            download_button_area = st.empty()
            
            if "extracted_text" not in st.session_state:
                st.session_state.extracted_text = None
            if "output_filename" not in st.session_state:
                st.session_state.output_filename = None
            
            if submit_button:
                st.session_state.extracted_text = None
                st.session_state.output_filename = None
                download_button_area.empty()
                results_display_area.empty()
                
                base_filename = os.path.splitext(uploaded_file.name)[0]
                st.session_state.output_filename = f"{base_filename}_extracted.txt"
                
                with st.status("Processing Document...", expanded=True) as status_indicator:
                    def progress_updater(message):
                        status_indicator.write(message)
                        time.sleep(0.05)
                    
                    progress_updater(f"File '{uploaded_file.name}' received. Type: {file_extension.upper()}")
                    
                    try:
                        if file_extension == ".pdf":
                            if extractor_type == "langchain":
                                strategy = ExtractorFactory.create_extractor("langchain")
                            elif extractor_type.startswith("gemini_"):
                                model_name = extractor_type.replace("gemini_", "")
                                strategy = ExtractorFactory.create_extractor("gemini", model_name)
                            elif extractor_type.startswith("openai_"):
                                model_name = extractor_type.replace("openai_", "")
                                strategy = ExtractorFactory.create_extractor("openai", model_name)
                            else:
                                strategy = ExtractorFactory.create_extractor("langchain")
                                
                            self.processor.set_strategy(strategy)
                            extracted_content = self.processor.process(current_file_path_in_session, progress_updater)
                            
                        elif file_extension == ".docx":
                            strategy = ExtractorFactory.create_extractor("docx")
                            self.processor.set_strategy(strategy)
                            extracted_content = self.processor.process(current_file_path_in_session, progress_updater)
                        
                        else:
                            extracted_content = "Unsupported file type for extraction."
                            progress_updater(extracted_content)
                        
                        st.session_state.extracted_text = extracted_content
                        
                        self.history_manager.add_entry(
                            "pdf_to_text", 
                            uploaded_file.name, 
                            {"extractor": extractor_type, "success": "[Error" not in extracted_content}
                        )
                        
                        if "[Error" in extracted_content:
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
                            st.session_state.current_uploaded_filename = None
            
            if st.session_state.extracted_text is not None:
                results_display_area.subheader("Extracted Text:")
                results_display_area.text_area("Content", st.session_state.extracted_text, height=400, key="text_area_results_display")
                
                if st.session_state.output_filename and not ("[Error" in st.session_state.extracted_text):
                    download_button_area.download_button(
                        label="Download Extracted Text (.txt)",
                        data=st.session_state.extracted_text.encode('utf-8', errors='replace'),
                        file_name=st.session_state.output_filename,
                        mime="text/plain"
                    )

def show():
    ui = DocumentToTextUI()
    ui.show()