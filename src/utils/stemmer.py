"""
CroStem: Hrvatski Stemmer
Port of the CroStem Rust/PHP algorithm to Python.
"""

class CroStemmer:
    """
    CroStem stemmer za hrvatski jezik.
    Podržava agresivni i konzervativni mod.
    """
    
    # Sufiksi za agresivni mod (više skraćuje)
    SUFFIXES_AGGRESSIVE = [
        "ovijega", "ovijemu", "ovijeg", "ovijem", "ovijim", "ovijih", "ovijoj", 
        "ijega", "ijemu", "ijem", "ijih", "ijim", "ijog", "ijoj",
        "nijeg", "nijem", "nijih", "nijim", "nija", "nije", "niji", "niju", 
        "asmo", "aste", "ahu", "ismo", "iste", "jesmo", "jeste", "jesu", 
        "ajući", "ujući", "ivši", "avši", "jevši", "nuti", "iti", "ati", "eti", "uti", 
        "ela", "ala", "alo", "ilo", "ili", 
        "njak", "nost", "anje", "enje", "stvo", "ica", "ika", "ice", "ike",
        "jemu", "jega", "ama", "ima", "om", "em", "ev", "og", "eg", "im", "ih", 
        "oj", "oh", "iš", "ov", "ši", "ga", "mu", "en", "ski", "jeh", "eš", "aš", 
        "am", "osmo", "este", "oše", 
        "a", "e", "i", "o", "u", "la", "lo", "li", "te", "mo", "je",
    ]
    
    # Sufiksi za konzervativni mod (manje skraćuje)
    SUFFIXES_CONSERVATIVE = [
        "ovijega", "ovijemu", "ovijeg", "ovijem", "ovijim", "ovijih", "ovijoj", 
        "ijega", "ijemu", "ijem", "ijih", "ijim", "ijog", "ijoj",
        "nijeg", "nijem", "nijih", "nijim", "nija", "nije", "niji", "niju", 
        "asmo", "aste", "ahu", "ismo", "iste", "jesmo", "jeste", "jesu", 
        "ajući", "ujući", "ivši", "avši", "nuti", "iti", "ati", "eti", "uti", 
        "ela", "ala", "alo", "ilo", "ili", 
        "njak", "nost", "anje", "enje", "stvo", "ica", "ika", "ice", "ike",
        "jemu", "jega", "ama", "ima", "om", "em", "og", "im", "ih", "oj", "oh", 
        "iš", "ov", "ši", "ga", "mu",
        "a", "e", "i", "o", "u", "la", "lo", "li", "te", "mo",
    ]
    
    # Prefiksi
    PREFIXES = ["naj", "pre", "iz", "na", "po", "do", "uz"]
    
    # Izuzetci
    EXCEPTIONS = {
        "ljudi": "ljud", "osoba": "osoba", "psa": "pas", "psi": "pas",
        "oca": "otac", "očevi": "otac", "oči": "oko", "uši": "uho",
        "djeca": "dijete", "vrapca": "vrabac", "vrapci": "vrabac",
    }
    
    # Glasovna pravila (voice rules)
    VOICE_RULES = {
        "učenic": "učenik", "majc": "majk", "ruc": "ruk", "ruz": "ruk", "noz": "nog", 
        "knjiz": "knjig", "dječac": "dječak", "dus": "duh", "jezic": "jezik", 
        "supruz": "suprug", "rekoš": "rek", "snjeg": "snijeg", "pjesnic": "pjesnik", 
        "momc": "momak", "pekl": "pek", "gledal": "gled", "djetet": "djet", 
        "pjes": "pjesm", "peć": "pek", "striž": "strig", "vuč": "vuk", 
        "kaž": "kaz", "maš": "mah", "pij": "pi", "draž": "drag", "brž": "brz", 
        "slađ": "slad", "vraz": "vrag", "siromas": "siromah", "skač": "skak", 
        "svrs": "svrha", "vuc": "vuk", "oblac": "oblak", "viš": "vis", 
        "bolj": "dobar", "jač": "jak", "već": "velik", "duž": "dug", 
        "bjelj": "bijel", "gorč": "gork", "reć": "rek", "ora": "orl", 
        "dijet": "djet", "tež": "teg", "sunc": "sunc", "vremen": "vremen", 
        "djevojč": "djevojčic", "oras": "orah", "src": "src", "dra": "drag", 
        "pečen": "pek", "rađen": "rad", "viđ": "vid", "momk": "momak", 
        "vrapc": "vrab", "vidj": "vid", "ptič": "ptič", "snj": "snijeg", 
        "hrvatsk": "hrvat", "mislima": "misao", "šalic": "šalic", 
        "stručnj": "struč", "jest": "jed", "pit": "pi", "čut": "ču", 
        "znat": "zna", "htj": "htje", "moć": "mog", "reč": "rek", 
        "teč": "tek", "vrš": "vrh", "dobar": "dobr", "kratak": "kratk", 
        "uzak": "uzk", "nizak": "nizk", "težak": "težk", "topao": "topl", 
        "hladan": "hladn", "tjedn": "tjedan", "dvorc": "dvorac", 
        "trenuc": "trenutak", "bitak": "bitka", "bajak": "bajka", 
        "dasak": "daska", "djevojak": "djevojka", "momak": "momak", 
        "top": "topl", "vidjev": "vid", "ljep": "lijep", "crv": "crven", 
        "peč": "pek", "piš": "pis", "duš": "duh", "čovječ": "čovjek", 
        "čovjec": "čovjek",
    }
    
    # Lemma pravila (za konzervativni mod)
    LEMMA_RULES = {
        "majk": "majka", "ruk": "ruka", "nog": "noga", "knjig": "knjiga", 
        "vrijem": "vrijeme", "djet": "dijete", "pjesm": "pjesma", "kuć": "kuća", 
        "škol": "škola", "polj": "polje", "mor": "more", "sunc": "sunce", 
        "dobr": "dobar", "sret": "sretan", "pamet": "pametan", "tužn": "tužan", 
        "tuž": "tužan", "duž": "dug", "već": "velik", "manj": "malen", 
        "bolj": "dobar", "lošij": "loš", "pis": "pisati", "vidj": "vidjeti", 
        "vid": "vidjeti", "htje": "htjeti", "mog": "moći", "rek": "reći", 
        "pek": "peći",
    }

    def stem(self, word: str, mode: str = "aggressive") -> str:
        """
        Stemira jednu riječ.
        
        Args:
            word: Riječ za stemiranje
            mode: 'aggressive' ili 'conservative'
            
        Returns:
            Stemirani korijen
        """
        # 1. Lowercase i čišćenje
        word = word.lower().strip()
        word = ''.join(c for c in word if c.isalpha())
        
        if not word:
            return word
            
        # 2. Izuzetci
        if word in self.EXCEPTIONS:
            return self.EXCEPTIONS[word]
            
        # 3. Suffix stripping (longest match first)
        suffixes = self.SUFFIXES_AGGRESSIVE if mode == "aggressive" else self.SUFFIXES_CONSERVATIVE
        current = word
        
        while True:
            found = False
            for suffix in suffixes:
                if current.endswith(suffix):
                    potential_root = current[:-len(suffix)]
                    if self._is_suffix_strippable(suffix, potential_root, mode):
                        current = potential_root
                        found = True
                        break
            if not found:
                break
                
        # 4. Prefix stripping
        for prefix in self.PREFIXES:
            if current.startswith(prefix):
                potential_root = current[len(prefix):]
                if len(potential_root) >= 3:
                    current = potential_root
                    break
                    
        # 5. Voice rules
        if current in self.VOICE_RULES:
            current = self.VOICE_RULES[current]
            
        # 6. Lemma rules (conservative only)
        if mode == "conservative" and current in self.LEMMA_RULES:
            current = self.LEMMA_RULES[current]
            
        return current
        
    def _is_suffix_strippable(self, suffix: str, root: str, mode: str) -> bool:
        """Provjerava može li se sufiks ukloniti."""
        root_len = len(root)
        
        if mode == "aggressive":
            if suffix in ["em", "ov", "ev"]:
                return root_len >= 3
            if suffix in ["en", "ica", "ice", "ika", "ike"]:
                return root_len >= 4
            if len(suffix) == 1:
                return root_len >= 3
            return root_len >= 2
        else:
            # Conservative: minimum root is 3 chars
            return root_len >= 3
            
    def stem_text(self, text: str, mode: str = "aggressive") -> str:
        """
        Stemira cijeli tekst (više riječi).
        
        Args:
            text: Tekst za stemiranje
            mode: 'aggressive' ili 'conservative'
            
        Returns:
            Stemirani tekst
        """
        words = text.split()
        stemmed = [self.stem(word, mode) for word in words]
        return ' '.join(stemmed)


# Singleton instanca
stemmer = CroStemmer()


def stem(word: str, mode: str = "aggressive") -> str:
    """Convenience funkcija za stemiranje jedne riječi."""
    return stemmer.stem(word, mode)


def stem_text(text: str, mode: str = "aggressive") -> str:
    """Convenience funkcija za stemiranje teksta."""
    return stemmer.stem_text(text, mode)


# Test
if __name__ == "__main__":
    test_words = ["kuća", "kući", "kućom", "kućama", "knjiga", "knjigama", "čovjek", "ljudi"]
    print("CroStem Test:")
    print("-" * 40)
    for word in test_words:
        print(f"  {word:15} → {stem(word)}")
