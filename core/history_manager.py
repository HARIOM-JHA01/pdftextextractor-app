import os
import json
import datetime
from typing import Dict, List, Any, Optional

class HistoryManager:
    def __init__(self, history_file: str = "user_history.json"):
        self.history_file = history_file
        self.history_data = self._load_history()
    
    def _load_history(self) -> Dict[str, List[Dict[str, Any]]]:
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._initialize_history()
        else:
            return self._initialize_history()
    
    def _initialize_history(self) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "pdf_to_text": [],
            "audio_to_text": [],
            "chat_with_doc": [],
            "summarizer": []
        }
    
    def _save_history(self) -> None:
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.history_data, f, indent=2)
        except IOError:
            pass
    
    def add_entry(self, 
                 feature: str, 
                 file_name: str, 
                 details: Optional[Dict[str, Any]] = None) -> None:
        if feature not in self.history_data:
            self.history_data[feature] = []
        
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "file_name": file_name,
            "details": details or {}
        }
        
        self.history_data[feature].append(entry)
        self._save_history()
    
    def get_history(self, feature: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        if feature:
            return {feature: self.history_data.get(feature, [])}
        return self.history_data
    
    def get_recent_files(self, feature: str, limit: int = 5) -> List[str]:
        if feature not in self.history_data:
            return []
        
        entries = self.history_data[feature]
        files = []
        seen = set()
        
        for entry in reversed(entries):
            file_name = entry["file_name"]
            if file_name not in seen and len(files) < limit:
                files.append(file_name)
                seen.add(file_name)
        
        return files
    
    def clear_history(self, feature: Optional[str] = None) -> None:
        if feature:
            if feature in self.history_data:
                self.history_data[feature] = []
        else:
            self.history_data = self._initialize_history()
        
        self._save_history()