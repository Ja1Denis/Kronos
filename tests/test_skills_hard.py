import os
import time
import pytest
import threading
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from src.server import app
from src.modules.librarian import Librarian
from src.modules.skill_manager import SkillManager
from src.modules.approval import ApprovalManager
from src.modules.oracle import Oracle

os.environ["KRONOS_SKILL_THRESHOLD"] = "0.5"
client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_skills_db():
    """Čisti tablice prije svakog testa, osiguravajući da su kreirane."""
    sm = SkillManager()
    am = ApprovalManager()
    
    lib = Librarian()
    conn = lib._get_sqlite_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM registered_skills")
    cursor.execute("DELETE FROM approvals")
    cursor.execute("DELETE FROM vec_metadata WHERE json_extract(metadata_json, '$.type') = 'skill'")
    conn.commit()
    conn.close()
    yield

def test_approval_timeout():
    """Testira da čekanje na odobrenje ispravno istječe i automatski odbija zahtjev."""
    am = ApprovalManager()
    
    # Kreiraj zahtjev
    req_id = am.create_request("Timeout Skill", "test query timeout")
    
    # Blokiraj s kratkim timeoutom (1 sekunda) i brzim poll intervalom
    start_time = time.time()
    approved = am.wait_for_approval(req_id, timeout_sec=1, poll_interval_sec=0.1)
    duration = time.time() - start_time
    
    # Provjere
    assert approved is False
    assert duration >= 1.0
    
    # Zahtjev bi morao biti automatski postavljen na REJECTED nakon timeouta
    req = am.get_request(req_id)
    assert req["status"] == "REJECTED"
    assert req["resolved_at"] is not None

def test_approval_explicit_rejection():
    """Testira da se čekanje prekida čim se zahtjev eksplicitno odbije iz drugog threada."""
    am = ApprovalManager()
    req_id = am.create_request("Rejected Skill", "test query rejection")
    
    def reject_later():
        time.sleep(0.5)
        mgr = ApprovalManager()
        mgr.resolve_request(req_id, "REJECTED")
        
    t = threading.Thread(target=reject_later)
    t.start()
    
    start_time = time.time()
    # Postavljamo dug timeout (10s), ali bi trebalo završiti za ~0.5s
    approved = am.wait_for_approval(req_id, timeout_sec=10, poll_interval_sec=0.1)
    duration = time.time() - start_time
    
    assert approved is False
    assert 0.4 <= duration < 2.0  # Završilo je odmah po odbijanju, puno prije 10s
    
    req = am.get_request(req_id)
    assert req["status"] == "REJECTED"

def test_concurrent_approvals():
    """Testira konkurentnost nad SQLite bazom pod opterećenjem više paralelnih odobrenja."""
    am = ApprovalManager()
    num_requests = 10
    req_ids = []
    
    # 1. Kreiraj više zahtjeva paralelno
    def create_req(i):
        mgr = ApprovalManager()
        return mgr.create_request(f"Concurrent Skill {i}", f"query {i}")
        
    with ThreadPoolExecutor(max_workers=5) as executor:
        req_ids = list(executor.map(create_req, range(num_requests)))
        
    assert len(req_ids) == num_requests
    for req_id in req_ids:
        assert req_id is not None
        
    # 2. Provjeri da su svi PENDING
    pending = am.get_pending_requests()
    assert len(pending) == num_requests
    
    # 3. Pokreni thread koji će ih sve odobriti s kratkim razmacima
    def resolve_all():
        mgr = ApprovalManager()
        for rid in req_ids:
            time.sleep(0.1)
            mgr.resolve_request(rid, "APPROVED")
            
    t = threading.Thread(target=resolve_all)
    t.start()
    
    # 4. Čekaj odobrenje za svaki zahtjev paralelno
    def wait_req(rid):
        mgr = ApprovalManager()
        return mgr.wait_for_approval(rid, timeout_sec=5, poll_interval_sec=0.1)
        
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(wait_req, req_ids))
        
    # Svi zahtjevi bi trebali biti uspješno odobreni bez zaključavanja baze
    assert all(results)
    
    for rid in req_ids:
        req = am.get_request(rid)
        assert req["status"] == "APPROVED"

def test_oracle_ask_with_skill_approval_hard():
    """Testira integraciju Oracle.ask s uspješnim odobrenjem skilla."""
    oracle = Oracle()
    sm = SkillManager(oracle.librarian)
    
    # Registriraj skill s visokim thresholdom ili specifičnim imenom
    sm.register_skill(
        name="SQL Generator Skill",
        description="Generates complex SQLite queries for debugging metadata.",
        path="skills/sql_gen.md"
    )
    
    # Ako nema Gemini API ključa, moramo mockati matching jer embedding_function neće raditi
    if not oracle.embedding_function:
        pytest.skip("Gemini API key is not configured, skipping Oracle integration test.")
        
    # Pokreni Oracle.ask u zasebnom threadu jer će blokirati dok se ne odobri
    query = "generate complex sqlite queries for metadata"
    result_box = []
    
    def run_ask():
        res = oracle.ask(query, silent=True)
        result_box.append(res)
        
    t = threading.Thread(target=run_ask)
    t.start()
    
    # Daj mu trenutak da kreira zahtjev
    time.sleep(1.0)
    
    # Pronađi pending zahtjev i odobri ga
    am = ApprovalManager(oracle.librarian)
    pending = am.get_pending_requests()
    assert len(pending) == 1
    req_id = pending[0]["id"]
    
    am.resolve_request(req_id, "APPROVED")
    
    t.join(timeout=5.0)
    
    assert len(result_box) == 1
    res = result_box[0]
    assert res["status"] == "approved_skill"
    assert res["skill"]["name"] == "SQL Generator Skill"
    assert res["approval_id"] == req_id

def test_oracle_ask_with_skill_rejection_hard():
    """Testira integraciju Oracle.ask s odbijanjem skilla."""
    oracle = Oracle()
    sm = SkillManager(oracle.librarian)
    
    sm.register_skill(
        name="Shell Script Runner",
        description="Executes arbitrary powershell commands.",
        path="skills/shell.md"
    )
    
    if not oracle.embedding_function:
        pytest.skip("Gemini API key is not configured, skipping Oracle integration test.")
        
    query = "execute arbitrary powershell commands"
    result_box = []
    
    def run_ask():
        res = oracle.ask(query, silent=True)
        result_box.append(res)
        
    t = threading.Thread(target=run_ask)
    t.start()
    
    time.sleep(1.0)
    
    am = ApprovalManager(oracle.librarian)
    pending = am.get_pending_requests()
    assert len(pending) == 1
    req_id = pending[0]["id"]
    
    # Odbij zahtjev
    am.resolve_request(req_id, "REJECTED")
    
    t.join(timeout=5.0)
    
    assert len(result_box) == 1
    res = result_box[0]
    assert res["status"] == "rejected_skill"
    assert res["approval_id"] == req_id

def test_invalid_and_edge_cases():
    """Testira nevaljane i rubne slučajeve za sustav odobrenja."""
    am = ApprovalManager()
    
    # 1. Čekanje na nepostojeći ID zahtjeva
    approved = am.wait_for_approval("non-existent-id", timeout_sec=1, poll_interval_sec=0.1)
    assert approved is False
    
    # 2. Rješavanje nepostojećeg zahtjeva
    success = am.resolve_request("non-existent-id", "APPROVED")
    assert success is False
    
    # 3. Rješavanje s nevaljanim statusom
    req_id = am.create_request("Valid Skill", "query")
    success = am.resolve_request(req_id, "INVALID_STATUS")
    assert success is False
    
    # Provjeri da je i dalje PENDING
    req = am.get_request(req_id)
    assert req["status"] == "PENDING"
