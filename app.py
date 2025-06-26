import streamlit as st
import os
from dotenv import load_dotenv
from core.config import ConfigFactory
from core.history_manager import HistoryManager

load_dotenv()

class DocuTextApp:
    def __init__(self):
        self.history_manager = HistoryManager()
        self.setup_configs()
        self.setup_page()
    
    def setup_configs(self):
        self.gemini_config = ConfigFactory.get_config("gemini")
        self.openai_config = ConfigFactory.get_config("openai")
        self.deepgram_config = ConfigFactory.get_config("deepgram")
    
    def setup_page(self):
        st.set_page_config(page_title="DocuText Extractor", layout="wide")
    
    def show_home(self):
        st.title("🔠 DocuText Extractor")
        st.write("Your all-in-one document processing solution")
        
        self.show_api_status()
        
        col1, col2 = st.columns(2)
        
        with col1:
            with st.container():
                st.subheader("📄 Convert PDF/Word to Text")
                st.write("Extract text from PDF and Word documents with advanced OCR capabilities.")
                if st.button("Open", key="pdf_to_text"):
                    st.session_state.page = "pdf_to_text"
                    st.rerun()
            st.markdown("---")
            
            with st.container():
                st.subheader("🔊 Convert Audio to Text")
                st.write("Transcribe audio files to text with Deepgram or Gemini speech recognition.")
                if st.button("Open", key="audio_to_text"):
                    st.session_state.page = "audio_to_text"
                    st.rerun()
            st.markdown("---")
        
        with col2:
            with st.container():
                st.subheader("💬 Chat with PDF/Word")
                st.write("Ask questions about your documents and get instant answers.")
                if st.button("Open", key="chat_with_doc"):
                    st.session_state.page = "chat_with_doc"
                    st.rerun()
            st.markdown("---")
            
            with st.container():
                st.subheader("📝 Document Summarizer")
                st.write("Generate concise summaries of your documents automatically.")
                if st.button("Open", key="summarizer"):
                    st.session_state.page = "summarizer"
                    st.rerun()
            st.markdown("---")
        
        with st.expander("Recent Activity"):
            all_history = self.history_manager.get_history()
            
            if not any(all_history.values()):
                st.write("No recent activity")
            else:
                tabs = st.tabs(["Documents", "Audio", "Chat", "Summaries"])
                
                with tabs[0]:
                    doc_history = all_history.get("pdf_to_text", [])
                    if doc_history:
                        for entry in doc_history[:5]:
                            st.write(f"📄 {entry['file_name']} - {entry['timestamp'][:10]}")
                    else:
                        st.write("No document processing history")
                
                with tabs[1]:
                    audio_history = all_history.get("audio_to_text", [])
                    if audio_history:
                        for entry in audio_history[:5]:
                            st.write(f"🔊 {entry['file_name']} - {entry['timestamp'][:10]}")
                    else:
                        st.write("No audio transcription history")
                
                with tabs[2]:
                    chat_history = all_history.get("chat_with_doc", [])
                    if chat_history:
                        for entry in chat_history[:5]:
                            st.write(f"💬 {entry['file_name']} - {entry['timestamp'][:10]}")
                    else:
                        st.write("No document chat history")
                
                with tabs[3]:
                    summary_history = all_history.get("summarizer", [])
                    if summary_history:
                        for entry in summary_history[:5]:
                            st.write(f"📝 {entry['file_name']} - {entry['timestamp'][:10]}")
                    else:
                        st.write("No document summary history")
    
    def show_api_status(self):
        with st.sidebar:
            st.subheader("API Services Status")
            
            gemini_status = "✅ Available" if self.gemini_config and self.gemini_config.is_available() else "❌ Not Configured"
            openai_status = "✅ Available" if self.openai_config and self.openai_config.is_available() else "❌ Not Configured"
            deepgram_status = "✅ Available" if self.deepgram_config and self.deepgram_config.is_available() else "❌ Not Configured"
            
            st.markdown(f"**Gemini API**: {gemini_status}")
            st.markdown(f"**OpenAI API**: {openai_status}")
            st.markdown(f"**Deepgram API**: {deepgram_status}")
            
            if not (self.gemini_config and self.gemini_config.is_available()) and \
               not (self.openai_config and self.openai_config.is_available()) and \
               not (self.deepgram_config and self.deepgram_config.is_available()):
                st.warning("No API keys configured. Add to .env file for full functionality.")
            
            st.divider()
            if st.button("Clear History"):
                self.history_manager.clear_history()
                st.success("History cleared successfully!")
    
    def run(self):
        if "page" not in st.session_state:
            st.session_state.page = "home"
        
        if st.session_state.page == "home":
            self.show_home()
        
        elif st.session_state.page == "pdf_to_text":
            from pages import doc_to_text
            doc_to_text.show()
            
            if st.button("← Back to Home"):
                st.session_state.page = "home"
                st.rerun()
        
        elif st.session_state.page == "audio_to_text":
            from pages import audio_to_text
            audio_to_text.show()
            
            if st.button("← Back to Home"):
                st.session_state.page = "home"
                st.rerun()
        
        elif st.session_state.page == "chat_with_doc":
            from pages import chat_with_doc
            chat_with_doc.show()
            
            if st.button("← Back to Home"):
                st.session_state.page = "home"
                st.rerun()
        
        elif st.session_state.page == "summarizer":
            from pages import summarizer
            summarizer.show()
            
            if st.button("← Back to Home"):
                st.session_state.page = "home"
                st.rerun()
        
        st.markdown("---")
        st.markdown("DocuText Extractor v2.0")

if __name__ == "__main__":
    app = DocuTextApp()
    app.run()