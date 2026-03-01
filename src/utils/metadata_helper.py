import hashlib
import os
import re
from datetime import datetime
from colorama import Fore, Style
from typing import Any, Optional

# SECURITY: Određujemo dozvljeni root bazirano na lokaciji skripte (ai-test-project),
# a ne na trenutnom radnom direktoriju (CWD), što je robusnije.
_curr_file = os.path.abspath(__file__) # .../kronos/src/utils/metadata_helper.py
_src_utils = os.path.dirname(_curr_file)
_src = os.path.dirname(_src_utils)
_kronos = os.path.dirname(_src)

# Popravak za Railway/Docker (ako je u Dockeru, dopusti cijeli /app root, inače koristi lokalni root)
if os.path.exists("/app") and _kronos.startswith("/app"):
    ALLOWED_ROOT = "/app"
else:
    ALLOWED_ROOT = os.path.dirname(_kronos) # ai-test-project root

# Podrška za dodatne dozvoljene root putanje putem env varijable
# Primjer: KRONOS_ALLOWED_ROOTS=E:\M;E:\Projects
_extra_roots = os.getenv("KRONOS_ALLOWED_ROOTS", "")
ALLOWED_ROOTS = [ALLOWED_ROOT] + [r.strip() for r in _extra_roots.split(";") if r.strip()]

def is_safe_path(file_path: str, allowed_root: str = ALLOWED_ROOT) -> bool:
    """
    SECURITY: Prevents path traversal attacks.
    Provjerava je li putanja unutar dozvoljenog korijenskog direktorija.
    Podržava provjeru protiv svih ALLOWED_ROOTS.
    """
    if not file_path or not isinstance(file_path, str):
        return False
        
    # Check for null bytes and control characters
    if "\x00" in file_path or "\n" in file_path or "\r" in file_path:
        return False
        
    try:
        # Normalize and resolve
        normalized_path = os.path.normpath(file_path)
        
        # Provjeri sve dozvoljene root putanje
        roots_to_check = ALLOWED_ROOTS if allowed_root == ALLOWED_ROOT else [allowed_root]
        
        if os.path.isabs(normalized_path):
            path_ok = any(
                normalized_path.lower().startswith(os.path.abspath(root).lower())
                for root in roots_to_check
            )
            if not path_ok:
                return False
        else:
            abs_path = os.path.abspath(normalized_path)
            path_ok = any(
                abs_path.lower().startswith(os.path.abspath(root).lower())
                for root in roots_to_check
            )
            if not path_ok:
                return False
                
        # Dodatna provjera za '..' nakon normalizacije
        if ".." in normalized_path.split(os.sep):
            return False
            
        return True
    except Exception:
        return False

def enforce_metadata_types(metadata: Any) -> Optional[dict]:
    """
    KRITIČNO: Prevents NoneType crashes i osigurava ispravne tipove podataka.
    """
    # Check 1: metadata is dict
    if not isinstance(metadata, dict):
        print(f"{Fore.RED}❌ Invalid metadata type: {type(metadata)}{Style.RESET_ALL}")
        return None
        
    # Check 2: 'source' exists AND is string
    if 'source' not in metadata or not isinstance(metadata['source'], str):
        print(f"{Fore.RED}❌ Missing or invalid 'source' field{Style.RESET_ALL}")
        return None
        
    # Check 3: 'source' is not empty
    if len(metadata['source'].strip()) == 0:
        print(f"{Fore.RED}❌ Empty 'source' field{Style.RESET_ALL}")
        return None
        
    # Check 4: start_line and end_line are integers
    if 'start_line' in metadata:
        if not isinstance(metadata['start_line'], int):
            print(f"{Fore.RED}❌ start_line not int: {type(metadata['start_line'])}{Style.RESET_ALL}")
            return None
        if metadata['start_line'] < 0:
            print(f"{Fore.RED}❌ start_line negative: {metadata['start_line']}{Style.RESET_ALL}")
            return None
            
    # Check 5: end_line >= start_line
    if 'start_line' in metadata and 'end_line' in metadata:
        if not isinstance(metadata['end_line'], int):
            print(f"{Fore.RED}❌ end_line not int: {type(metadata['end_line'])}{Style.RESET_ALL}")
            return None
        if metadata['end_line'] < metadata['start_line']:
            print(f"{Fore.RED}❌ end_line < start_line: {metadata['end_line']} < {metadata['start_line']}{Style.RESET_ALL}")
            return None
            
    # Check 6: Path safety
    if not is_safe_path(metadata['source']):
        print(f"{Fore.RED}❌ SECURITY: Unsafe path detected: {metadata['source']}{Style.RESET_ALL}")
        return None

    return metadata

def validate_metadata(metadata: dict) -> bool:
    """
    Provjerava obavezna polja u metapodacima koristeći strogu provjeru tipova.
    """
    return enforce_metadata_types(metadata) is not None

def validate_line_range(start: int, end: int, file_path: str = None, check_file: bool = True) -> tuple[bool, str]:
    """
    VAŽNO: Prevents IndexError crashes i DoS napade velikim rasponima.
    """
    if not isinstance(start, int) or not isinstance(end, int):
        return False, "Line indices must be integers"
        
    if start < 1: # Redni broj linije počinje od 1 u našem sustavu
        return False, f"Invalid start_line {start} (must be >= 1)"
        
    if end < start:
        return False, f"Invalid range: end_line {end} must be greater than or equal to start_line {start}"
        
    # DoS Prevention: Ograniči maksimalni raspon na 10,000 linija
    if end - start > 10000:
        return False, f"Range too large ({end - start} lines). Max allowed is 10000."
        
    # Provjera stvarne duljine fajla (opcionalno)
    if check_file and file_path and os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Efikasan način brojanja linija
                line_count = sum(1 for _ in f)
            if end > line_count:
                return False, f"end_line {end} exceeds file length {line_count}"
        except Exception as e:
            return False, f"Error checking file length: {str(e)}"
            
    return True, ""

def enrich_metadata(doc: str, metadata: dict) -> dict:
    """
    Dodaje indexed_at i content_hash.
    """
    new_meta = metadata.copy()
    new_meta["indexed_at"] = datetime.now().isoformat()
    if "content_hash" not in new_meta:
        new_meta["content_hash"] = hashlib.sha256(doc.encode()).hexdigest()
    return new_meta
