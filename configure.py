import os
import sys

def configure():
    print("----------------------------------------------------------------")
    print("Kronos Configuration / Konfiguracija")
    print("----------------------------------------------------------------")
    print("1. English (en)")
    print("2. Hrvatski (hr)")
    
    choice = input("\nChoose your language / Odaberi jezik (1/2) [default: 1]: ").strip()
    
    lang = "en"
    if choice == "2" or choice.lower() == "hr":
        lang = "hr"
        print("\nOdabrano: Hrvatski")
    else:
        print("\nSelected: English")
        
    # .env handling
    env_file = ".env"
    lines = []
    
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            lines = f.readlines()
            
    # Check if KRONOS_LANG exists and update it, or append it
    found = False
    new_lines = []
    for line in lines:
        if line.startswith("KRONOS_LANG="):
            new_lines.append(f"KRONOS_LANG={lang}\n")
            found = True
        else:
            new_lines.append(line)
            
    if not found:
        # Ensure newline before appending if file not empty and no newline at end
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(f"KRONOS_LANG={lang}\n")
        
    with open(env_file, "w") as f:
        f.writelines(new_lines)
        
    print(f"\nConfiguration saved to {env_file}.")
    print(f"KRONOS_LANG={lang}")

if __name__ == "__main__":
    configure()
