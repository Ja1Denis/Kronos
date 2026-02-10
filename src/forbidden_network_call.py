
import requests # OVO JE ZABRANJENO PREMA ODLUCI!

def dohvati_podatke():
    # Pokušavamo koristiti requests
    r = requests.get("https://api.github.com")
    return r.json()
