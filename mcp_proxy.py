import sys
import subprocess
import os

# Putanja do mcp_server.py
script_path = os.path.join(os.path.dirname(__file__), "src", "mcp_server.py")
venv_python = os.path.join(os.path.dirname(__file__), "venv", "Scripts", "python.exe")

# Log datoteka
log_file = os.path.join(os.path.dirname(__file__), "mcp_proxy_debug.log")

with open(log_file, "a") as log:
    log.write("\n--- NEW SESSION ---\n")

def main():
    # Pokreni pravi mcp_server.py kao podproces
    process = subprocess.Popen(
        [venv_python, script_path],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=0,
        universal_newlines=True
    )

    # Čitač iz stdin (od IDE-a) -> u podproces
    def pipe_stdin():
        while True:
            line = sys.stdin.readline()
            if not line: break
            with open(log_file, "a") as log:
                log.write(f"IDE -> SERVER: {line}")
            process.stdin.write(line)
            process.stdin.flush()

    import threading
    threading.Thread(target=pipe_stdin, daemon=True).start()

    # Čitač iz stdout (od podprocesa) -> IDE
    while True:
        line = process.stdout.readline()
        if not line: break
        with open(log_file, "a") as log:
            log.write(f"SERVER -> IDE: {line}")
        
        # Filtar: Ako linija ne počinje sa { (JSON-RPC), nemoj je slati IDE-u!
        if line.strip().startswith("{") or line.strip().startswith("["):
            sys.stdout.write(line)
            sys.stdout.flush()
        else:
            # Sve ostalo preusmjeri na stderr da IDE vidi kao logove
            sys.stderr.write(line)
            sys.stderr.flush()

if __name__ == "__main__":
    main()
