import os
import time
from typing import Callable, Optional, Dict, Any
from abc import ABC, abstractmethod
from deepgram import (
    DeepgramClient,
    PrerecordedOptions,
    FileSource
)
import google.generativeai as genai
from core.config import DeepgramConfig, GeminiConfig

AUDIO_UPLOAD_DIR = "audio_uploads"
os.makedirs(AUDIO_UPLOAD_DIR, exist_ok=True)

class AudioTranscriber(ABC):
    @abstractmethod
    def transcribe(self, audio_path: str, progress_callback: Callable[[str], None]) -> str:
        pass

class DeepgramTranscriber(AudioTranscriber):
    def __init__(self, model: str = "nova-2"):
        self.model = model
        self.config = DeepgramConfig()
    
    def transcribe(self, audio_path: str, progress_callback: Callable[[str], None]) -> str:
        if not self.config.is_available():
            return "[Error: Deepgram API key not configured]"
        
        progress_callback(f"Initializing Deepgram transcription with model: {self.model}...")
        
        try:
            deepgram = DeepgramClient(self.config.api_key)
            
            progress_callback("Reading audio file...")
            with open(audio_path, "rb") as audio:
                audio_data = audio.read()
            
            progress_callback("Sending audio to Deepgram for processing...")
            
            payload = {
                "buffer": audio_data
            }
            
            options = {
                "model": self.model,
                "smart_format": True,
                "diarize": True,
                "punctuate": True
            }
            
            response = deepgram.listen.prerecorded.v("1").transcribe_file(payload, options)
            
            progress_callback("Processing response...")
            
            if response and isinstance(response, dict):
                if "results" in response and "channels" in response["results"]:
                    channels = response["results"]["channels"]
                    if channels and isinstance(channels, list) and len(channels) > 0:
                        if "alternatives" in channels[0] and len(channels[0]["alternatives"]) > 0:
                            transcript = channels[0]["alternatives"][0].get("transcript", "")
                            if transcript:
                                progress_callback("Transcription complete!")
                                return transcript
            
            if response and hasattr(response, "results"):
                try:
                    transcript = response.results.channels[0].alternatives[0].transcript
                    progress_callback("Transcription complete!")
                    return transcript
                except (AttributeError, IndexError, TypeError):
                    pass
            
            try:
                if hasattr(response, "to_json"):
                    import json
                    json_data = json.loads(response.to_json())
                    if "results" in json_data and "channels" in json_data["results"]:
                        channels = json_data["results"]["channels"]
                        if channels and len(channels) > 0:
                            if "alternatives" in channels[0] and len(channels[0]["alternatives"]) > 0:
                                transcript = channels[0]["alternatives"][0].get("transcript", "")
                                if transcript:
                                    progress_callback("Transcription complete!")
                                    return transcript
            except Exception as json_error:
                progress_callback(f"Error extracting transcript from JSON: {str(json_error)}")
            
            progress_callback("No transcription results found in response.")
            return "[Error: No transcription results in response]"
                
        except Exception as e:
            error_message = f"Error during transcription: {str(e)}"
            progress_callback(error_message)
            return f"[Error: {error_message}]"

class GeminiTranscriber(AudioTranscriber):
    def __init__(self, model: str = "gemini-1.5-flash-latest"):
        self.model = model
        self.config = GeminiConfig()
    
    def transcribe(self, audio_path: str, progress_callback: Callable[[str], None]) -> str:
        if not self.config.is_available():
            return "[Error: Gemini API key not configured]"
        
        self.config.configure()
        progress_callback(f"Initializing Gemini transcription with model: {self.model}...")
        
        try:
            model = genai.GenerativeModel(self.model)
            
            progress_callback("Reading audio file...")
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            
            progress_callback("Processing audio with Gemini AI...")
            
            content = [
                "Transcribe this audio accurately. Include speaker labels if multiple speakers are detected.",
                {"mime_type": "audio/mp3", "data": audio_data}
            ]
            
            response = model.generate_content(content)
            transcription = response.text
            
            progress_callback("Transcription complete!")
            return transcription
        
        except Exception as e:
            error_message = f"Error transcribing audio: {str(e)}"
            progress_callback(error_message)
            return f"[Error: {error_message}]"

class TranscriberFactory:
    @staticmethod
    def create_transcriber(transcriber_type: str, model: str = None) -> AudioTranscriber:
        if transcriber_type == "deepgram":
            if not model:
                model = "nova-2"
            return DeepgramTranscriber(model)
        elif transcriber_type == "gemini":
            if not model:
                model = "gemini-1.5-flash-latest"
            return GeminiTranscriber(model)
        else:
            raise ValueError(f"Unknown transcriber type: {transcriber_type}")

class AudioProcessor:
    def __init__(self):
        self.transcriber = None
    
    def set_transcriber(self, transcriber: AudioTranscriber) -> None:
        self.transcriber = transcriber
    
    def process(self, audio_path: str, progress_callback: Callable[[str], None]) -> str:
        if self.transcriber is None:
            return "[Error: No transcription service selected]"
        
        return self.transcriber.transcribe(audio_path, progress_callback)

def save_uploaded_audio_file(uploaded_file) -> str:
    file_path = os.path.join(AUDIO_UPLOAD_DIR, uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path

def cleanup_audio_file(file_path: str) -> None:
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception as e:
            print(f"Error removing audio file {file_path}: {e}")