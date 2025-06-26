import streamlit as st
import os
import time
from dotenv import load_dotenv
from core.extractor import (
    get_pdf_first_page_preview,
    UPLOAD_DIR
)
from core.summarizer import (
    SummarizerService,
    SummarizerFactory
)
from core.config import GeminiConfig, OpenAIConfig
from core.history_manager import HistoryManager

class SummarizerUI:
    def __init__(self):
        self.summarizer_service = SummarizerService()
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
            st.sidebar.error("No AI service API keys found. Add to .env file.")
    
    def show(self):
        st.title("📝 Document Summarizer")
        
        self.display_api_key_status()
        
        with st.sidebar:
            st.subheader("Recent Documents")
            recent_files = self.history_manager.get_recent_files("summarizer")
            if recent_files:
                st.write("Recently processed:")
                for file in recent_files:
                    st.write(f"- {file}")
            else:
                st.write("No recent documents")
        
        summarizer_options = {}
        
        if self.gemini_config.is_available():
            summarizer_options.update(
                {f"gemini_{model_id}": f"Gemini: {model_name}" 
                for model_id, model_name in self.gemini_config.get_models().items()}
            )
        
        if self.openai_config.is_available():
            summarizer_options.update(
                {f"openai_{model_id}": f"OpenAI: {model_name}" 
                for model_id, model_name in self.openai_config.get_models().items()}
            )
        
        if not summarizer_options:
            st.error("No summarization services available. Please add API keys to your .env file.")
            st.info("Required keys: GEMINI_API_KEY or OPENAI_API_KEY")
            return
        
        summarizer_type = st.selectbox(
            "Select Summarization Service:",
            options=list(summarizer_options.keys()),
            format_func=lambda x: summarizer_options[x],
            key="summarizer_service_select"
        )
        
        st.write("Upload a document to generate an AI-powered summary. Choose from different summary styles to meet your needs.")
        
        uploaded_file = st.file_uploader("Upload your PDF or DOCX file", type=["pdf", "docx"], key="summary_file_uploader")
        
        preview_area = st.container()
        current_file_path = None
        
        if "summary_result" not in st.session_state:
            st.session_state.summary_result = None
        
        if uploaded_file:
            if "current_summary_filename" not in st.session_state or st.session_state.current_summary_filename != uploaded_file.name:
                st.session_state.current_summary_filename = uploaded_file.name
                st.session_state.summary_result = None
                
            current_file_path = self.save_uploaded_file_to_disk(uploaded_file)
            self.display_file_preview(uploaded_file, current_file_path, preview_area)
        
        summary_types = {
            "concise": "Concise (3-5 sentences)",
            "detailed": "Detailed (Comprehensive)",
            "executive": "Executive Summary",
            "bullet": "Bullet Points"
        }
        
        summary_type = st.radio(
            "Select Summary Type:",
            options=list(summary_types.keys()),
            format_func=lambda x: summary_types[x],
            key="summary_type_radio"
        )
        
        summarize_button = st.button("Generate Summary")
        
        status_area = st.empty()
        result_area = st.empty()
        download_area = st.empty()
        
        if summarize_button and uploaded_file and current_file_path:
            st.session_state.summary_result = None
            download_area.empty()
            result_area.empty()
            
            base_filename = os.path.splitext(uploaded_file.name)[0]
            summary_type_label = summary_types[summary_type].split(" ")[0].lower()
            output_filename = f"{base_filename}_{summary_type_label}_summary.txt"
            
            with st.status("Generating Summary...", expanded=True) as status:
                def progress_callback(message):
                    status.write(message)
                    time.sleep(0.05)
                
                progress_callback(f"Processing document: {uploaded_file.name}")
                
                try:
                    if summarizer_type.startswith("gemini_"):
                        model_name = summarizer_type.replace("gemini_", "")
                        summarizer = SummarizerFactory.create_summarizer("gemini", model_name)
                    elif summarizer_type.startswith("openai_"):
                        model_name = summarizer_type.replace("openai_", "")
                        summarizer = SummarizerFactory.create_summarizer("openai", model_name)
                    else:
                        summarizer = SummarizerFactory.create_summarizer("gemini")
                    
                    self.summarizer_service.set_summarizer(summarizer)
                    summary = self.summarizer_service.summarize_document(
                        current_file_path,
                        summary_type,
                        progress_callback
                    )
                    
                    st.session_state.summary_result = summary
                    st.session_state.summary_output_filename = output_filename
                    
                    self.history_manager.add_entry(
                        "summarizer", 
                        uploaded_file.name, 
                        {"summarizer": summarizer_type, "summary_type": summary_type, "success": "Error:" not in summary}
                    )
                    
                    if "Error:" in summary:
                        status.update(label="Summarization Failed!", state="error", expanded=True)
                    else:
                        status.update(label="Summary Generated!", state="complete", expanded=False)
                
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")
                    status.update(label="Summarization Error!", state="error", expanded=True)
                    st.session_state.summary_result = f"Critical error during summarization: {str(e)}"
        
        if st.session_state.summary_result is not None:
            result_area.subheader("Summary Result:")
            result_area.markdown(st.session_state.summary_result)
            
            if "summary_output_filename" in st.session_state and not "Error:" in st.session_state.summary_result:
                download_area.download_button(
                    label="Download Summary (.txt)",
                    data=st.session_state.summary_result.encode('utf-8', errors='replace'),
                    file_name=st.session_state.summary_output_filename,
                    mime="text/plain"
                )

def show():
    ui = SummarizerUI()
    ui.show()