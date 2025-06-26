import streamlit as st
import os
import time
from dotenv import load_dotenv
from core.audio_processor import (
    AudioProcessor,
    TranscriberFactory,
    save_uploaded_audio_file,
    cleanup_audio_file
)
from core.config import DeepgramConfig, GeminiConfig
from core.history_manager import HistoryManager

class AudioToTextUI:
    def __init__(self):
        self.processor = AudioProcessor()
        self.history_manager = HistoryManager()
        self.deepgram_config = DeepgramConfig()
        self.gemini_config = GeminiConfig()
    
    def display_api_key_status(self):
        st.sidebar.subheader("API Key Status")
        
        deepgram_status = "✅ Available" if self.deepgram_config.is_available() else "❌ Not Configured"
        gemini_status = "✅ Available" if self.gemini_config.is_available() else "❌ Not Configured"
        
        st.sidebar.markdown(f"**Deepgram API**: {deepgram_status}")
        st.sidebar.markdown(f"**Gemini API**: {gemini_status}")
        
        if not self.deepgram_config.is_available() and not self.gemini_config.is_available():
            st.sidebar.error("No transcription API keys found. Add to .env file.")
    
    def show(self):
        st.title("🔊 Convert Audio to Text")
        
        self.display_api_key_status()
        
        with st.sidebar:
            st.subheader("Recent Audio Files")
            recent_files = self.history_manager.get_recent_files("audio_to_text")
            if recent_files:
                st.write("Recently processed:")
                for file in recent_files:
                    st.write(f"- {file}")
            else:
                st.write("No recent audio files")
        
        st.write("Upload an audio file to convert it to text. Supported formats: MP3, WAV, M4A.")
        
        transcription_options = {}
        
        if self.deepgram_config.is_available():
            transcription_options.update(
                {f"deepgram_{model_id}": f"Deepgram: {model_name}" 
                for model_id, model_name in self.deepgram_config.get_models().items()}
            )
        
        if self.gemini_config.is_available():
            transcription_options.update(
                {f"gemini_{model_id}": f"Gemini: {model_name}" 
                for model_id, model_name in self.gemini_config.get_models().items()}
            )
        
        if not transcription_options:
            st.error("No transcription services available. Please add API keys to your .env file.")
            st.info("Required keys: DEEPGRAM_API_KEY or GEMINI_API_KEY")
            return
        
        transcriber_type = st.selectbox(
            "Select Transcription Service:",
            options=list(transcription_options.keys()),
            format_func=lambda x: transcription_options[x],
            key="transcription_service_select"
        )
        
        uploaded_audio = st.file_uploader("Upload your audio file", type=["mp3", "wav", "m4a"], key="audio_file_uploader")
        
        current_audio_path = None
        
        if uploaded_audio:
            if "current_audio_filename" not in st.session_state or st.session_state.current_audio_filename != uploaded_audio.name:
                st.session_state.current_audio_filename = uploaded_audio.name
                st.session_state.transcription_result = None
                st.session_state.audio_output_filename = None
            
            st.audio(uploaded_audio)
            current_audio_path = save_uploaded_audio_file(uploaded_audio)
        
        transcribe_button = st.button("Transcribe Audio")
        
        status_area = st.empty()
        result_area = st.empty()
        download_area = st.empty()
        
        if "transcription_result" not in st.session_state:
            st.session_state.transcription_result = None
        if "audio_output_filename" not in st.session_state:
            st.session_state.audio_output_filename = None
        
        if transcribe_button and uploaded_audio and current_audio_path:
            st.session_state.transcription_result = None
            st.session_state.audio_output_filename = None
            download_area.empty()
            result_area.empty()
            
            base_filename = os.path.splitext(uploaded_audio.name)[0]
            st.session_state.audio_output_filename = f"{base_filename}_transcript.txt"
            
            with st.status("Transcribing Audio...", expanded=True) as status:
                def progress_callback(message):
                    status.write(message)
                    time.sleep(0.05)
                
                progress_callback(f"Audio file '{uploaded_audio.name}' received.")
                
                try:
                    if transcriber_type.startswith("deepgram_"):
                        model = transcriber_type.replace("deepgram_", "")
                        transcriber = TranscriberFactory.create_transcriber("deepgram", model)
                    elif transcriber_type.startswith("gemini_"):
                        model = transcriber_type.replace("gemini_", "")
                        transcriber = TranscriberFactory.create_transcriber("gemini", model)
                    else:
                        transcriber = TranscriberFactory.create_transcriber("deepgram")
                    
                    self.processor.set_transcriber(transcriber)
                    transcription = self.processor.process(current_audio_path, progress_callback)
                    
                    st.session_state.transcription_result = transcription
                    
                    self.history_manager.add_entry(
                        "audio_to_text", 
                        uploaded_audio.name, 
                        {"transcriber": transcriber_type, "success": "[Error" not in transcription}
                    )
                    
                    if "[Error" in transcription:
                        status.update(label="Transcription Failed!", state="error", expanded=True)
                    else:
                        status.update(label="Transcription Complete!", state="complete", expanded=False)
                
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")
                    status.update(label="Transcription Error!", state="error", expanded=True)
                    st.session_state.transcription_result = f"Critical error during transcription: {str(e)}"
                finally:
                    if current_audio_path:
                        cleanup_audio_file(current_audio_path)
                        st.session_state.current_audio_filename = None
        
        if st.session_state.transcription_result is not None:
            result_area.subheader("Transcription Result:")
            result_area.text_area("Content", st.session_state.transcription_result, height=300, key="transcription_text_area")
            
            if st.session_state.audio_output_filename and not "[Error" in st.session_state.transcription_result:
                download_area.download_button(
                    label="Download Transcription (.txt)",
                    data=st.session_state.transcription_result.encode('utf-8', errors='replace'),
                    file_name=st.session_state.audio_output_filename,
                    mime="text/plain"
                )

def show():
    ui = AudioToTextUI()
    ui.show()