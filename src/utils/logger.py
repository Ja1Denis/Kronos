import logging
import os
from colorama import init, Fore, Style
from datetime import datetime

# Inicijalizacija colorame
init(autoreset=True)

class KronosLogger:
    def __init__(self, name="Kronos", log_dir="logs"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Formatiranje
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # 1. File Handler (za trajnu pohranu)
        # Ako je log_dir relativan, razriješi ga relativno na korijen projekta
        # da se izbjegne pisanje u system32 kad se MCP pokrene iz IDE-a
        if not os.path.isabs(log_dir):
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_dir = os.path.join(project_root, log_dir)

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_file = os.path.join(log_dir, f"kronos_{datetime.now().strftime('%Y-%m-%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 2. Console Handler (s bojama!)
        # Ostavljamo print za CLI output, logger za debug informacije
    
    def info(self, msg):
        try:
            print(f"{Fore.CYAN}ℹ️  {msg}{Style.RESET_ALL}")
        except UnicodeEncodeError:
            try:
                # Pokušaj ispisati barem s hrvatskim znakovima ako konzola podržava cp1252
                print(f"{Fore.CYAN}[INFO] {msg}{Style.RESET_ALL}")
            except UnicodeEncodeError:
                safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
                print(f"{Fore.CYAN}[INFO] {safe_msg}{Style.RESET_ALL}")
        self.logger.info(msg)
        
    def success(self, msg):
        try:
            print(f"{Fore.GREEN}✅ {msg}{Style.RESET_ALL}")
        except UnicodeEncodeError:
            try:
                print(f"{Fore.GREEN}[SUCCESS] {msg}{Style.RESET_ALL}")
            except UnicodeEncodeError:
                safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
                print(f"{Fore.GREEN}[SUCCESS] {safe_msg}{Style.RESET_ALL}")
        self.logger.info(pass_msg := f"SUCCESS: {msg}")

    def warning(self, msg):
        try:
            print(f"{Fore.YELLOW}⚠️  {msg}{Style.RESET_ALL}")
        except UnicodeEncodeError:
            try:
                print(f"{Fore.YELLOW}[WARNING] {msg}{Style.RESET_ALL}")
            except UnicodeEncodeError:
                safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
                print(f"{Fore.YELLOW}[WARNING] {safe_msg}{Style.RESET_ALL}")
        self.logger.warning(msg)

    def error(self, msg):
        try:
            print(f"{Fore.RED}❌ {msg}{Style.RESET_ALL}")
        except UnicodeEncodeError:
            try:
                print(f"{Fore.RED}[ERROR] {msg}{Style.RESET_ALL}")
            except UnicodeEncodeError:
                safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
                print(f"{Fore.RED}[ERROR] {safe_msg}{Style.RESET_ALL}")
        self.logger.error(msg)
        
    def debug(self, msg):
        self.logger.debug(msg)

# Singleton instanca
logger = KronosLogger()
