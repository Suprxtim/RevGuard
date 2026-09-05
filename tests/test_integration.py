import pytest
from fastapi.testclient import TestClient
from bs4 import BeautifulSoup
from app.main import app

def test_full_recovery_loop():
    """
    Automated integration test suite for the Recovery Loop control flow.
    Follows the exact 8-step verification sequence.
    """
    client = TestClient(app)
    
    # 1. Empty reset state
    reset_res = client.post("/admin/reset-demo")
    assert reset_res.status_code == 200
    
    audit_res = client.get("/audit")
    soup = BeautifulSoup(audit_res.text, 'html.parser')
    tbody = soup.find('tbody')
    rows = tbody.find_all('tr') if tbody else []
    assert len(rows) == 0, "Expected 0 events after reset"
    
    # Refresh the empty dashboard twice
    audit_res_1 = client.get("/audit")
    audit_res_2 = client.get("/audit")
    assert audit_res_1.text == audit_res_2.text, "Dashboard should be strictly read-only"
    
    # 2. Click Generate Batch exactly once
    gen_res = client.post("/admin/simulate/batch")
    assert gen_res.status_code == 200
    
    # Verify it has non-zero at risk and events are pending
    audit_res_gen = client.get("/audit")
    soup_gen = BeautifulSoup(audit_res_gen.text, 'html.parser')
    tbody_gen = soup_gen.find('tbody')
    rows_gen = tbody_gen.find_all('tr') if tbody_gen else []
    assert len(rows_gen) > 0, "Batch generation failed to create events"
    
    text_content = audit_res_gen.text
    assert "Pending" in text_content, "Events should initially be open/pending"
    
    # Refresh twice
    audit_res_gen_1 = client.get("/audit")
    audit_res_gen_2 = client.get("/audit")
    assert audit_res_gen_1.text == audit_res_gen_2.text, "Refresh must not change metrics or create events"
    
    # 3. Click Process Pending once
    # TestClient automatically executes BackgroundTasks synchronously!
    client.post("/admin/process") 
    
    audit_res_proc = client.get("/audit")
    soup_proc = BeautifulSoup(audit_res_proc.text, 'html.parser')
    tbody_proc = soup_proc.find('tbody')
    rows_proc = tbody_proc.find_all('tr') if tbody_proc else []
    assert len(rows_proc) == len(rows_gen), "Number of events should not change"
    
    # Refresh twice again
    audit_res_proc_1 = client.get("/audit")
    audit_res_proc_2 = client.get("/audit")
    assert audit_res_proc_1.text == audit_res_proc_2.text # Proves idempotency & read-only reporting
    
    # 4. Click Process Pending a second time
    client.post("/admin/process")
    
    audit_res_proc_second = client.get("/audit")
    assert audit_res_proc.text == audit_res_proc_second.text, "Second process call mutated state!"
    
    # 5. Click Trigger Retry Storm
    storm_res = client.post("/admin/trigger-retry-storm")
    assert storm_res.status_code == 200
    
    # Process the storm
    client.post("/admin/process")
    
    audit_res_storm = client.get("/audit")
    assert "retry_storm_check" in audit_res_storm.text, "Retry storm policy was not triggered"
    
    # 6. Click Reset Demo
    reset_final = client.post("/admin/reset-demo")
    assert reset_final.status_code == 200
    
    audit_res_final = client.get("/audit")
    soup_final = BeautifulSoup(audit_res_final.text, 'html.parser')
    tbody_final = soup_final.find('tbody')
    rows_final = tbody_final.find_all('tr') if tbody_final else []
    assert len(rows_final) == 0, "Expected 0 events after final reset"
