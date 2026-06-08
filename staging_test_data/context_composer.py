class ContextComposer:
    def __init__(self):
        self.category_tokens = {}
        self.pointer_mode = "v0.3.0"
        
    def compose(self, query):
        print(f"Composing for {query}")
        return "Context"
    