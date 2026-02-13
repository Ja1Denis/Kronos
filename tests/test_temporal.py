"""
Testovi za Temporal Truth značajke (Faza 3).
"""
import pytest
from src.modules.extractor import Extractor
from src.modules.librarian import Librarian
import tempfile
import os


class TestExtractorDecisions:
    """Testovi za ekstrakciju odluka s temporalnim podacima."""
    
    def setup_method(self):
        self.extractor = Extractor()
    
    def test_extract_decision_with_inline_dates(self):
        """Test ekstrakcije odluke s inline datumima [YYYY-MM-DD -> YYYY-MM-DD]."""
        text = "* **Odluka:** Koristimo SQLite. [2024-01-01 -> 2024-12-31]"
        result = self.extractor.extract(text)
        
        assert len(result['decisions']) == 1
        decision = result['decisions'][0]
        assert "Koristimo SQLite" in decision['content']
        assert decision['valid_from'] == "2024-01-01"
        assert decision['valid_to'] == "2024-12-31"
    
    def test_extract_decision_with_metadata_lines(self):
        """Test ekstrakcije odluke s metapodacima u idućim linijama."""
        text = """
* **Odluka:** Prelazimo na PostgreSQL.
  Valid From: 2025-01-01
  Superseded By: sqlite-odluka
"""
        result = self.extractor.extract(text)
        
        assert len(result['decisions']) >= 1
        decision = result['decisions'][0]
        assert "PostgreSQL" in decision['content']
        assert decision['valid_from'] == "2025-01-01"
        assert decision['superseded_by'] == "sqlite-odluka"
    
    def test_extract_simple_decision(self):
        """Test ekstrakcije jednostavne odluke bez datuma."""
        text = "Odluka: Koristimo Python 3.11."
        result = self.extractor.extract(text)
        
        assert len(result['decisions']) == 1
        decision = result['decisions'][0]
        assert "Python 3.11" in decision['content']
        assert decision['valid_from'] is None
        assert decision['valid_to'] is None


class TestLibrarianActiveDecisions:
    """Testovi za dohvaćanje aktivnih odluka."""
    
    def setup_method(self):
        # Koristi privremeni direktorij za testiranje
        self.temp_dir = tempfile.mkdtemp()
        self.librarian = Librarian(data_path=self.temp_dir)
    
    def teardown_method(self):
        # Očisti privremeni direktorij
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_active_decisions_empty(self):
        """Test dohvaćanja odluka iz prazne baze."""
        decisions = self.librarian.get_active_decisions()
        assert decisions == []
    
    def test_store_and_retrieve_decision(self):
        """Test spremanja i dohvaćanja odluke s temporalnim podacima."""
        data = {
            'decisions': [
                {
                    'content': 'Test odluka',
                    'valid_from': '2024-01-01',
                    'valid_to': '2024-12-31',
                    'superseded_by': None
                }
            ],
            'problems': [],
            'solutions': [],
            'tasks': [],
            'code_snippets': []
        }
        
        self.librarian.store_extracted_data('/test/path.md', data, project='test')
        
        # Dohvati odluke za datum unutar raspona
        decisions = self.librarian.get_active_decisions(date='2024-06-15')
        assert len(decisions) == 1
        assert decisions[0]['content'] == 'Test odluka'
        
        # Dohvati odluke za datum izvan raspona
        decisions_outside = self.librarian.get_active_decisions(date='2025-06-15')
        assert len(decisions_outside) == 0


class TestDebounceHandler:
    """Osnovni testovi za debounce handler."""
    
    def test_import_batch_handler(self):
        """Test da se BatchJobEventHandler može importirati."""
        from src.modules.watcher import BatchJobEventHandler
        assert BatchJobEventHandler is not None
    
    def test_batch_interval_default(self):
        """Test defaultne vrijednosti debounce intervala."""
        from src.modules.watcher import BatchJobEventHandler
        handler = BatchJobEventHandler()
        
        assert handler.debounce_interval == 5.0
        assert handler.pending_files == set()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
