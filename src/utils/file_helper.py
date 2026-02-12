import os
import time
import logging
import hashlib
from typing import Dict, Any, Tuple, Optional
from src.utils.metadata_helper import is_safe_path, validate_line_range

# OS-specific locking
try:
    import msvcrt
    HAS_MSVCRT = True
except ImportError:
    HAS_MSVCRT = False
    try:
        import fcntl
        HAS_FCNTL = True
    except ImportError:
        HAS_FCNTL = False

logger = logging.getLogger(__name__)

def detect_encoding(file_path: str) -> str:
    """
    Detect file encoding from BOM or common Windows patterns.
    """
    try:
        with open(file_path, 'rb') as f:
            raw = f.read(4)
        
        # Check BOM signatures
        if raw.startswith(b'\xff\xfe\x00\x00'):
            return 'utf-32-le'
        elif raw.startswith(b'\x00\x00\xfe\xff'):
            return 'utf-32-be'
        elif raw.startswith(b'\xff\xfe'):
            return 'utf-16-le'
        elif raw.startswith(b'\xfe\xff'):
            return 'utf-16-be'
        elif raw.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        
        # No BOM, try UTF-8 first, fallback to cp1250 (Central European) or windows-1252
        return 'utf-8'
    except Exception:
        return 'utf-8'

def read_file_safe(file_path: str, start_line: int, end_line: int, timeout: int = 5) -> Dict[str, Any]:
    """
    KRITIČNO: Sigurno čitanje datoteke s lockingom, timeout-om i validacijom.
    """
    # STEP 1: Validate path
    if not is_safe_path(file_path):
        return {"error": "invalid_path", "message": f"Path validation failed for: {file_path}"}
    
    # STEP 2: Validate line range (Logička provjera bez otvaranja fajla)
    is_valid, error_msg = validate_line_range(start_line, end_line, check_file=False)
    if not is_valid:
        return {"error": "invalid_range", "message": error_msg}
    
    # STEP 3: Try to acquire lock with timeout
    start_time = time.time()
    lock_acquired = False
    f = None
    
    try:
        encoding = detect_encoding(file_path)
        # Use errors='replace' to prevent crashes on invalid characters
        f = open(file_path, 'r', encoding=encoding, errors='replace')
        
        # Try to lock with timeout
        while time.time() - start_time < timeout:
            try:
                if HAS_MSVCRT:
                    # Windows: LK_NBLCK (non-blocking lock)
                    # We lock only 1 byte as a semaphore
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    lock_acquired = True
                    break
                elif HAS_FCNTL:
                    # Linux/Mac: LOCK_SH (shared) | LOCK_NB (non-blocking)
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                    lock_acquired = True
                    break
                else:
                    # No locking available, proceed but log warning
                    logger.warning("No file locking mechanism available on this OS.")
                    lock_acquired = True
                    break
            except (IOError, OSError):
                time.sleep(0.1)  # Wait 100ms and retry
        
        if not lock_acquired:
            if f: f.close()
            return {"error": "lock_timeout", "message": f"Could not acquire lock after {timeout}s"}
        
        # STEP 4: Read file
        lines = f.readlines()
        
        # STEP 5: Bounds check (defense in depth)
        total_lines = len(lines)
        # Prilagodba indexima (ako start_line počinje od 1)
        # Naša implementacija koristi 1-based indexing za start_line/end_line
        idx_start = start_line - 1
        idx_end = end_line # end_line je inclusive u smislu "do te linije"
        
        if idx_end > total_lines:
            if HAS_MSVCRT:
                try:
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                except Exception: pass
            f.close()
            return {"error": "range_exceeds_file", "message": f"File has {total_lines} lines, requested {end_line}"}
            
        content = ''.join(lines[idx_start:idx_end])
        
        # Otključavanje (Windows zahtijeva LK_UNLCK prije zatvaranja na istoj poziciji)
        if HAS_MSVCRT:
            try:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            except Exception: pass
            
        f.close()
        return {
            "content": content, 
            "lines_read": idx_end - idx_start,
            "status": "success"
        }
    
    except FileNotFoundError:
        return {"error": "file_not_found", "message": f"File does not exist: {file_path}"}
    except PermissionError:
        return {"error": "permission_denied", "message": f"No permission to read: {file_path}"}
    except UnicodeDecodeError as e:
        return {"error": "encoding_error", "message": f"Cannot decode file: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error reading file {file_path}: {e}", exc_info=True)
        return {"error": "unknown_error", "message": str(e)}
    finally:
        if f and not f.closed:
            f.close()

def verify_content_hash(content: str, expected_hash: str) -> Tuple[bool, str]:
    """
    Provjerava hash sadržaja (samo prve linije radi stabilnosti).
    """
    if not content or not expected_hash:
        return True, ""
        
    lines = content.strip().split('\n')
    if not lines:
        return False, "Empty content"
        
    first_line = lines[0].strip()
    current_hash = hashlib.sha256(first_line.encode()).hexdigest()
    
    if current_hash != expected_hash:
        return False, "stale_pointer"
        
    return True, ""
