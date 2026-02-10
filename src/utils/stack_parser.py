import re
import os
from typing import List, Dict, Any

class StackTraceParser:
    """
    Parsira stack traceove (Python, JS, etc.) i izvlači relevantne lokacije datoteka.
    Cilj je pretvoriti trace u 'Virtualne Kursore' za Context Budgeter.
    """
    
    # Regex uzorci za različite jezike (proširivo)
    PATTERNS = [
        # Python: File "C:\path\to\file.py", line 123, in function_name
        r'File "(?P<path>[^"]+)", line (?P<line>\d+)',
        
        # Generic/JS: at functionName (C:/path/to/file.js:123:45)
        r'at .* \((?P<path>[^:]+):(?P<line>\d+)(?::\d+)?\)',
        
        # Simple Path:Line: /path/to/file.py:123
        r'(?P<path>[\w\-. /\\:]+\.(?:py|js|ts|html|css|php)):(?P<line>\d+)'
    ]

    @staticmethod
    def parse(trace_text: str) -> List[Dict[str, Any]]:
        """
        Parsira tekst i vraća listu pronađenih lokacija.
        Format: [{'path': '/abs/path', 'line': 123, 'snippet': '...'}]
        """
        locations = []
        seen = set()
        
        lines = trace_text.split('\n')
        
        for i, text_line in enumerate(lines):
            text_line = text_line.strip()
            if not text_line: continue
            
            for pattern in StackTraceParser.PATTERNS:
                match = re.search(pattern, text_line)
                if match:
                    path = match.group('path')
                    line = int(match.group('line'))
                    
                    # Normalizacija putanje (apsolutna)
                    # Ovdje pretpostavljamo da ako putanja nije apsolutna, 
                    # vjerojatno je relativna u odnosu na root (kojeg ne znamo uvijek ovdje, 
                    # ali parser će vratiti ono što nađe).
                    # U 'real-world' scenariju, server.py će ovo mapirati na stvarni projekt.
                    
                    # Dedup ključ
                    key = f"{path}:{line}"
                    if key not in seen:
                        # Pokušaj naći context (snippet) iz linije ispod (često u Python traceu)
                        snippet = ""
                        if i + 1 < len(lines):
                            next_line = lines[i+1].strip()
                            if not next_line.startswith("File"): # Basic check da nije novi frame
                                snippet = next_line

                        locations.append({
                            "file": path, 
                            "line": line,
                            "original_text": text_line,
                            "snippet": snippet
                        })
                        seen.add(key)
                    break # Match found, stop trying other patterns for this line
        
        return locations

# Test block
if __name__ == "__main__":
    example_trace = """
    Traceback (most recent call last):
      File "e:\G\GeminiCLI\ai-test-project\kronos\src\server.py", line 55, in query_memory
        results = oracle.ask(request.text, limit=request.limit, silent=True)
      File "e:\G\GeminiCLI\ai-test-project\kronos\src\modules\oracle.py", line 130, in ask
        return self._retrieve_candidates(q, project, limit, hyde, silent=True)
    """
    parsed = StackTraceParser.parse(example_trace)
    for p in parsed:
        print(p)
