import os
from abc import ABC, abstractmethod
import google.generativeai as genai
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

class AIServiceConfig(ABC):
    @abstractmethod
    def configure(self) -> None:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass

class GeminiConfig(AIServiceConfig):
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.models = {
            "gemini-1.5-flash-latest": "Gemini 1.5 Flash (Fast)",
            "gemini-1.5-pro-latest": "Gemini 1.5 Pro (Powerful)"
        }
    
    def configure(self) -> None:
        if self.is_available():
            genai.configure(api_key=self.api_key)
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def get_models(self) -> Dict[str, str]:
        return self.models

class OpenAIConfig(AIServiceConfig):
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.models = {
            "gpt-4o": "GPT-4o"
        }
    
    def configure(self) -> None:
        if self.is_available():
            os.environ["OPENAI_API_KEY"] = self.api_key
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def get_models(self) -> Dict[str, str]:
        return self.models

class DeepgramConfig(AIServiceConfig):
    def __init__(self):
        self.api_key = os.getenv("DEEPGRAM_API_KEY")
        self.models = {
            "nova-2": "Nova-2 (Latest)",
            "enhanced": "Enhanced"
        }
    
    def configure(self) -> None:
        pass
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def get_models(self) -> Dict[str, str]:
        return self.models

class ConfigFactory:
    @staticmethod
    def get_config(service_name: str) -> Optional[AIServiceConfig]:
        if service_name == "gemini":
            return GeminiConfig()
        elif service_name == "openai":
            return OpenAIConfig()
        elif service_name == "deepgram":
            return DeepgramConfig()
        return None