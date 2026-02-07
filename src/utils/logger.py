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
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_file = os.path.join(log_dir, f"kronos_{datetime.now().strftime('%Y-%m-%d')}.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 2. Console Handler (s bojama!)
        # Ostavljamo print za CLI output, logger za debug informacije
    
    def info(self, msg):
        print(f"{Fore.CYAN}ℹ️  {msg}{Style.RESET_ALL}")
        self.logger.info(msg)
        
    def success(self, msg):
        print(f"{Fore.GREEN}✅ {msg}{Style.RESET_ALL}")
        self.logger.info(pass_msg := f"SUCCESS: {msg}")

    def warning(self, msg):
        print(f"{Fore.YELLOW}⚠️  {msg}{Style.RESET_ALL}")
        self.logger.warning(msg)

    def error(self, msg):
        print(f"{Fore.RED}❌ {msg}{Style.RESET_ALL}")
        self.logger.error(msg)
        
    def debug(self, msg):
        # Debug ispisuje samo u file, ne u konzolu (da ne smeta korisniku)
        self.logger.debug(msg)

# Singleton instanca
logger = KronosLogger()
