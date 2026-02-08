import os

class Contextualizer:
    def __init__(self):
        pass
        
    def expand_context(self, chunk_content: str, source_path: str, context_window: int = 500) -> str:
        """
        Prouširuje chunk s okolnim tekstom iz izvorne datoteke.
        """
        if not source_path or not os.path.exists(source_path):
            return chunk_content 
            
        try:
            with open(source_path, 'r', encoding='utf-8') as f:
                full_text = f.read()
            
            # Pokušaj naći točan match
            start_idx = full_text.find(chunk_content)
            
            # Ako ne nađemo, probajmo naći prvih 50 znakova (možda je kraj odrezan)
            if start_idx == -1 and len(chunk_content) > 50:
                start_idx = full_text.find(chunk_content[:50])
                
            if start_idx == -1:
                return chunk_content # Nema matcha, vrati original
                
            end_idx = start_idx + len(chunk_content)
            
            # Proširi prozor
            new_start = max(0, start_idx - context_window)
            new_end = min(len(full_text), end_idx + context_window)
            
            # Pokušaj poravnati na početak/kraj linije radi ljepšeg prikaza
            # Traži newline unazad od new_start
            if new_start > 0:
                prev_newline = full_text.rfind('\n', 0, new_start)
                if prev_newline != -1:
                    new_start = prev_newline + 1
            
            # Traži newline unaprijed od new_end
            if new_end < len(full_text):
                next_newline = full_text.find('\n', new_end)
                if next_newline != -1:
                    new_end = next_newline
            
            extended = full_text[new_start:new_end]
            return extended
            
        except Exception as e:
            # print(f"Warning: Contextualizer error: {e}") 
            return chunk_content
            
if __name__ == "__main__":
    # Test
    ctx = Contextualizer()
    print("Testiram Contextualizer...")
    # Kreiraj dummy file
    test_file = "test_context.txt"
    content = "Linija 1\nLinija 2\nLinija 3\nOvo je target chunk koji tražimo.\nLinija 5\nLinija 6\nLinija 7"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    target = "Ovo je target chunk koji tražimo."
    res = ctx.expand_context(target, test_file, context_window=20)
    
    print(f"Original: '{target}'")
    print("-" * 20)
    print(f"Expanded:\n{res}")
    print("-" * 20)
    
    if os.path.exists(test_file):
        os.remove(test_file)
