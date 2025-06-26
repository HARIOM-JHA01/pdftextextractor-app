import streamlit as st
import os
import time
from dotenv import load_dotenv
from core.extractor import (
    get_pdf_first_page_preview,
    UPLOAD_DIR
)
from core.chat_engine import (
    DocumentChat,
    ChatEngineFactory
)
from core.config import GeminiConfig, OpenAIConfig
from core.history_manager import HistoryManager

class ChatWithDocUI:
    def __init__(self):
        self.document_chat = DocumentChat()
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
        st.title("💬 Chat with PDF/Word")
        
        self.display_api_key_status()
        
        with st.sidebar:
            st.subheader("Recent Documents")
            recent_files = self.history_manager.get_recent_files("chat_with_doc")
            if recent_files:
                st.write("Recently processed:")
                for file in recent_files:
                    st.write(f"- {file}")
            else:
                st.write("No recent documents")
        
        chat_options = {}
        
        if self.gemini_config.is_available():
            chat_options.update(
                {f"gemini_{model_id}": f"Gemini: {model_name}" 
                for model_id, model_name in self.gemini_config.get_models().items()}
            )
        
        if self.openai_config.is_available():
            chat_options.update(
                {f"openai_{model_id}": f"OpenAI: {model_name}" 
                for model_id, model_name in self.openai_config.get_models().items()}
            )
        if not chat_options:
            st.error("No chat services available. Please add API keys to your .env file.")
            st.info("Required keys: GEMINI_API_KEY or OPENAI_API_KEY")
            return
        
        chat_engine_type = st.selectbox(
            "Select Chat Engine:",
            options=list(chat_options.keys()),
            format_func=lambda x: chat_options[x],
            key="chat_engine_select"
        )
        
        st.write("Upload a document and ask questions about its content. The AI will analyze the document and answer your questions.")
        
        uploaded_file = st.file_uploader("Upload your PDF or DOCX file", type=["pdf", "docx"], key="chat_file_uploader")
        
        preview_area = st.container()
        current_file_path = None
        
        if "chat_document_chunks" not in st.session_state:
            st.session_state.chat_document_chunks = None
        
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        
        if uploaded_file:
            if "current_chat_filename" not in st.session_state or st.session_state.current_chat_filename != uploaded_file.name:
                st.session_state.current_chat_filename = uploaded_file.name
                st.session_state.chat_document_chunks = None
                st.session_state.chat_history = []
                
                current_file_path = self.save_uploaded_file_to_disk(uploaded_file)
                self.display_file_preview(uploaded_file, current_file_path, preview_area)
                
                with st.status("Processing document...", expanded=True) as status:
                    def progress_callback(message):
                        status.write(message)
                        time.sleep(0.05)
                    
                    progress_callback(f"Uploaded: {uploaded_file.name}")
                    
                    if chat_engine_type.startswith("gemini_"):
                        model_name = chat_engine_type.replace("gemini_", "")
                        chat_engine = ChatEngineFactory.create_chat_engine("gemini", model_name)
                    elif chat_engine_type.startswith("openai_"):
                        model_name = chat_engine_type.replace("openai_", "")
                        chat_engine = ChatEngineFactory.create_chat_engine("openai", model_name)
                    else:
                        chat_engine = ChatEngineFactory.create_chat_engine("gemini")
                    
                    self.document_chat.set_chat_engine(chat_engine)
                    document_chunks, error = self.document_chat.load_document(current_file_path, progress_callback)
                    
                    if error:
                        status.update(label="Document Processing Failed!", state="error")
                        st.error(f"Error: {error}")
                    else:
                        st.session_state.chat_document_chunks = document_chunks
                        
                        self.history_manager.add_entry(
                            "chat_with_doc", 
                            uploaded_file.name, 
                            {"chat_engine": chat_engine_type}
                        )
                        
                        status.update(label="Document Ready for Chat!", state="complete")
            else:
                current_file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
                self.display_file_preview(uploaded_file, current_file_path, preview_area)
        
        st.subheader("Ask a question about your document")
        
        for message in st.session_state.chat_history:
            role = message["role"]
            content = message["content"]
            
            with st.chat_message(role):
                st.write(content)
        
        if query := st.chat_input("Type your question here..."):
            if not st.session_state.chat_document_chunks:
                st.error("Please upload a document first.")
            else:
                st.session_state.chat_history.append({"role": "user", "content": query})
                
                with st.chat_message("user"):
                    st.write(query)
                
                with st.chat_message("assistant"):
                    response_container = st.empty()
                    response_container.write("Thinking...")
                    
                    with st.status("Processing query...", expanded=True) as status:
                        def progress_callback(message):
                            status.write(message)
                            time.sleep(0.05)
                        
                        if chat_engine_type.startswith("gemini_"):
                            model_name = chat_engine_type.replace("gemini_", "")
                            chat_engine = ChatEngineFactory.create_chat_engine("gemini", model_name)
                        elif chat_engine_type.startswith("openai_"):
                            model_name = chat_engine_type.replace("openai_", "")
                            chat_engine = ChatEngineFactory.create_chat_engine("openai", model_name)
                        else:
                            chat_engine = ChatEngineFactory.create_chat_engine("gemini")
                        
                        self.document_chat.set_chat_engine(chat_engine)
                        
                        response = self.document_chat.chat(
                            query, 
                            st.session_state.chat_document_chunks, 
                            st.session_state.chat_history,
                            progress_callback
                        )
                        
                        response_container.write(response)
                        status.update(label="Response Generated!", state="complete")
                
                st.session_state.chat_history.append({"role": "assistant", "content": response})
        
        if st.button("Clear Chat History"):
            st.session_state.chat_history = []
            st.experimental_rerun()

def show():
    ui = ChatWithDocUI()
    ui.show()