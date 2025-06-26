import os
from typing import Callable, List, Dict, Any, Optional
from abc import ABC, abstractmethod
import google.generativeai as genai
from openai import OpenAI
from core.config import GeminiConfig, OpenAIConfig
from core.chat_engine import DocumentLoader

class DocumentSummarizer(ABC):
    @abstractmethod
    def summarize(self, document_chunks: List[Any], summary_type: str, progress_callback: Optional[Callable[[str], None]] = None) -> str:
        pass

class GeminiSummarizer(DocumentSummarizer):
    def __init__(self, model_name: str = "gemini-1.5-pro-latest"):
        self.model_name = model_name
        self.config = GeminiConfig()
    
    def summarize(self, document_chunks: List[Any], summary_type: str, progress_callback: Optional[Callable[[str], None]] = None) -> str:
        if progress_callback:
            progress_callback(f"Preparing to summarize with Gemini {self.model_name}...")
        
        if not self.config.is_available():
            return "[Error: Gemini API key not configured]"
        
        self.config.configure()
        model = genai.GenerativeModel(self.model_name)
        
        document_text = ""
        for chunk in document_chunks:
            document_text += chunk.page_content + "\n\n"
        
        if progress_callback:
            progress_callback("Generating summary...")
        
        summary_instruction = self._get_summary_instruction(summary_type)
        
        prompt = f"""
        You are a professional document summarizer.
        
        DOCUMENT CONTENT:
        {document_text[:50000]}
        
        TASK: {summary_instruction}
        
        Make sure the summary is accurate, well-structured, and captures the essence of the document.
        """
        
        try:
            response = model.generate_content(prompt)
            if progress_callback:
                progress_callback("Summary generated successfully!")
            return response.text
        except Exception as e:
            error_message = f"Error generating summary: {str(e)}"
            if progress_callback:
                progress_callback(error_message)
            return f"Error: {error_message}"
    
    def _get_summary_instruction(self, summary_type: str) -> str:
        if summary_type == "concise":
            return "Create a very concise summary of the document in 3-5 sentences."
        elif summary_type == "detailed":
            return "Create a detailed summary of the document covering the main points and key details."
        elif summary_type == "executive":
            return "Create an executive summary of the document with key findings, conclusions, and recommendations."
        elif summary_type == "bullet":
            return "Create a bullet-point summary of the document's main points."
        else:
            return "Create a comprehensive summary of the document."

class OpenAISummarizer(DocumentSummarizer):
    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name
        self.config = OpenAIConfig()
    
    def summarize(self, document_chunks: List[Any], summary_type: str, progress_callback: Optional[Callable[[str], None]] = None) -> str:
        if progress_callback:
            progress_callback(f"Preparing to summarize with OpenAI {self.model_name}...")
        
        if not self.config.is_available():
            return "[Error: OpenAI API key not configured]"
        
        self.config.configure()
        client = OpenAI(api_key=self.config.api_key)
        
        document_text = ""
        for chunk in document_chunks:
            document_text += chunk.page_content + "\n\n"
        
        if progress_callback:
            progress_callback("Generating summary...")
        
        summary_instruction = self._get_summary_instruction(summary_type)
        
        system_prompt = f"""
        You are a professional document summarizer.
        
        TASK: {summary_instruction}
        
        Make sure the summary is accurate, well-structured, and captures the essence of the document.
        """
        
        try:
            response = client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Here is the document to summarize:\n\n{document_text[:50000]}"}
                ]
            )
            
            if progress_callback:
                progress_callback("Summary generated successfully!")
            return response.choices[0].message.content
        except Exception as e:
            error_message = f"Error generating summary: {str(e)}"
            if progress_callback:
                progress_callback(error_message)
            return f"Error: {error_message}"
    
    def _get_summary_instruction(self, summary_type: str) -> str:
        if summary_type == "concise":
            return "Create a very concise summary of the document in 3-5 sentences."
        elif summary_type == "detailed":
            return "Create a detailed summary of the document covering the main points and key details."
        elif summary_type == "executive":
            return "Create an executive summary of the document with key findings, conclusions, and recommendations."
        elif summary_type == "bullet":
            return "Create a bullet-point summary of the document's main points."
        else:
            return "Create a comprehensive summary of the document."

class SummarizerFactory:
    @staticmethod
    def create_summarizer(engine_type: str, model_name: Optional[str] = None) -> DocumentSummarizer:
        if engine_type == "gemini":
            if not model_name:
                model_name = "gemini-1.5-pro-latest"
            return GeminiSummarizer(model_name)
        elif engine_type == "openai":
            if not model_name:
                model_name = "gpt-4o"
            return OpenAISummarizer(model_name)
        else:
            raise ValueError(f"Unknown summarizer type: {engine_type}")

class SummarizerService:
    def __init__(self):
        self.document_loader = DocumentLoader()
        self.summarizer = None
    
    def set_summarizer(self, summarizer: DocumentSummarizer) -> None:
        self.summarizer = summarizer
    
    def load_document(self, file_path: str, progress_callback: Optional[Callable[[str], None]] = None):
        return self.document_loader.load_document(file_path, progress_callback)
    
    def summarize_document(self, file_path: str, summary_type: str, progress_callback: Optional[Callable[[str], None]] = None) -> str:
        if progress_callback:
            progress_callback("Loading document for summarization...")
        
        document_chunks, error = self.document_loader.load_document(file_path, progress_callback)
        
        if error:
            if progress_callback:
                progress_callback(f"Error loading document: {error}")
            return f"Error: {error}"
        
        if progress_callback:
            progress_callback("Document loaded successfully. Preparing for summarization...")
        
        if self.summarizer is None:
            return "[Error: No summarizer selected]"
        
        return self.summarizer.summarize(document_chunks, summary_type, progress_callback)