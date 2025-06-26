import os
from typing import Callable, List, Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
import google.generativeai as genai
from openai import OpenAI
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from core.config import GeminiConfig, OpenAIConfig

class DocumentLoader:
    def load_document(self, file_path: str, progress_callback: Optional[Callable[[str], None]] = None) -> Tuple[Optional[List[Any]], Optional[str]]:
        if progress_callback:
            progress_callback("Loading document...")
        
        file_extension = os.path.splitext(file_path)[1].lower()
        
        try:
            if file_extension == '.pdf':
                if progress_callback:
                    progress_callback("Processing PDF document...")
                loader = PyPDFLoader(file_path)
                documents = loader.load()
            elif file_extension == '.docx':
                if progress_callback:
                    progress_callback("Processing DOCX document...")
                loader = Docx2txtLoader(file_path)
                documents = loader.load()
            else:
                return None, "Unsupported file type"
            
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=5000,
                chunk_overlap=500
            )
            
            if progress_callback:
                progress_callback("Splitting document into chunks...")
            
            chunks = text_splitter.split_documents(documents)
            
            if progress_callback:
                progress_callback(f"Document processed into {len(chunks)} chunks.")
            
            return chunks, None
        
        except Exception as e:
            error_message = f"Error loading document: {str(e)}"
            if progress_callback:
                progress_callback(error_message)
            return None, error_message

class ChatEngine(ABC):
    @abstractmethod
    def generate_response(self, query: str, document_chunks: List[Any], history: List[Dict[str, str]], progress_callback: Optional[Callable[[str], None]] = None) -> str:
        pass

class GeminiChatEngine(ChatEngine):
    def __init__(self, model_name: str = "gemini-1.5-pro-latest"):
        self.model_name = model_name
        self.config = GeminiConfig()
    
    def _get_document_context(self, chunks: List[Any], query: str, max_chunks: int = 5) -> str:
        document_text = ""
        for i, chunk in enumerate(chunks[:max_chunks]):
            document_text += chunk.page_content + "\n\n"
        
        return document_text
    
    def generate_response(self, query: str, document_chunks: List[Any], history: List[Dict[str, str]], progress_callback: Optional[Callable[[str], None]] = None) -> str:
        if not document_chunks:
            return "Please upload a document first."
        
        if progress_callback:
            progress_callback("Processing your query...")
        
        if not self.config.is_available():
            return "[Error: Gemini API key not configured]"
        
        self.config.configure()
        model = genai.GenerativeModel(self.model_name)
        
        context = self._get_document_context(document_chunks, query)
        
        if progress_callback:
            progress_callback("Generating response...")
        
        prompt = f"""
        You are a helpful AI assistant that answers questions based on the provided document.
        
        DOCUMENT CONTENT:
        {context}
        
        USER QUESTION: {query}
        
        Based only on the document content above, provide a helpful, accurate response. 
        If the document doesn't contain relevant information to answer the question, 
        say "I don't have enough information in the document to answer this question."
        """
        
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_message = f"Error generating response: {str(e)}"
            if progress_callback:
                progress_callback(error_message)
            return f"Error: {error_message}"

class OpenAIChatEngine(ChatEngine):
    def __init__(self, model_name: str = "gpt-4o"):
        self.model_name = model_name
        self.config = OpenAIConfig()
    
    def _get_document_context(self, chunks: List[Any], query: str, max_chunks: int = 5) -> str:
        document_text = ""
        for i, chunk in enumerate(chunks[:max_chunks]):
            document_text += chunk.page_content + "\n\n"
        
        return document_text
    
    def generate_response(self, query: str, document_chunks: List[Any], history: List[Dict[str, str]], progress_callback: Optional[Callable[[str], None]] = None) -> str:
        if not document_chunks:
            return "Please upload a document first."
        
        if progress_callback:
            progress_callback("Processing your query...")
        
        if not self.config.is_available():
            return "[Error: OpenAI API key not configured]"
        
        self.config.configure()
        client = OpenAI(api_key=self.config.api_key)
        
        context = self._get_document_context(document_chunks, query)
        
        if progress_callback:
            progress_callback("Generating response...")
        
        system_prompt = f"""
        You are a helpful AI assistant that answers questions based on the provided document.
        
        DOCUMENT CONTENT:
        {context}
        
        Based only on the document content above, provide a helpful, accurate response. 
        If the document doesn't contain relevant information to answer the question, 
        say "I don't have enough information in the document to answer this question."
        """
        
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]
            
            # Add conversation history
            for i in range(0, len(history), 2):
                if i+1 < len(history):
                    messages.append({"role": "user", "content": history[i]["content"]})
                    messages.append({"role": "assistant", "content": history[i+1]["content"]})
            
            response = client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )
            
            return response.choices[0].message.content
        except Exception as e:
            error_message = f"Error generating response: {str(e)}"
            if progress_callback:
                progress_callback(error_message)
            return f"Error: {error_message}"

class ChatEngineFactory:
    @staticmethod
    def create_chat_engine(engine_type: str, model_name: Optional[str] = None) -> ChatEngine:
        if engine_type == "gemini":
            if not model_name:
                model_name = "gemini-1.5-pro-latest"
            return GeminiChatEngine(model_name)
        elif engine_type == "openai":
            if not model_name:
                model_name = "gpt-4o"
            return OpenAIChatEngine(model_name)
        else:
            raise ValueError(f"Unknown chat engine type: {engine_type}")

class DocumentChat:
    def __init__(self):
        self.document_loader = DocumentLoader()
        self.chat_engine = None
    
    def set_chat_engine(self, chat_engine: ChatEngine) -> None:
        self.chat_engine = chat_engine
    
    def load_document(self, file_path: str, progress_callback: Optional[Callable[[str], None]] = None) -> Tuple[Optional[List[Any]], Optional[str]]:
        return self.document_loader.load_document(file_path, progress_callback)
    
    def chat(self, query: str, document_chunks: List[Any], history: List[Dict[str, str]], progress_callback: Optional[Callable[[str], None]] = None) -> str:
        if self.chat_engine is None:
            return "[Error: No chat engine selected]"
        
        return self.chat_engine.generate_response(query, document_chunks, history, progress_callback)