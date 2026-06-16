import pytest
import pandas as pd
from src.processor import reconcile_inventories, calculate_similarity
from src.llm_helper import AnalysisAgent, run_reconciliation_workflow

def test_similarity_calculation():
    # Similar names should yield high similarity scores
    score_similar = calculate_similarity("prod-db-postgres", "prod-db-pg-01")
    score_dissimilar = calculate_similarity("prod-db-postgres", "dev-gitlab-runner")
    
    assert score_similar > 0.60
    assert score_dissimilar < 0.40

def test_inventory_reconciliation():
    # Create sample CMDB dataframe
    cmdb_data = [
        {"name": "server-01", "ip_address": "192.168.1.10", "environment": "Production", "cpu_cores": 4, "memory_gb": 16, "status": "Active"},
        {"name": "server-02", "ip_address": "192.168.1.20", "environment": "Production", "cpu_cores": 8, "memory_gb": 32, "status": "Active"},
        {"name": "server-03", "ip_address": "192.168.1.30", "environment": "Staging", "cpu_cores": 2, "memory_gb": 4, "status": "Active"},
        {"name": "server-04", "ip_address": "192.168.1.40", "environment": "Production", "cpu_cores": 2, "memory_gb": 4, "status": "Active"}
    ]
    cmdb_df = pd.DataFrame(cmdb_data)
    
    # Create sample Live discovery data
    live_data = [
        {"name": "server-01", "type": "Virtual Machine", "ip_address": "192.168.1.10", "environment": "Production", "cpu_cores": 4, "memory_gb": 16, "status": "running"},
        {"name": "server-02-new-name", "type": "Database", "ip_address": "192.168.1.20", "environment": "Production", "cpu_cores": 8, "memory_gb": 32, "status": "running"},
        {"name": "server-03", "type": "Load Balancer", "ip_address": "192.168.1.35", "environment": "Staging", "cpu_cores": 4, "memory_gb": 8, "status": "running"},
        {"name": "server-untracked", "type": "Virtual Machine", "ip_address": "192.168.1.99", "environment": "Development", "cpu_cores": 2, "memory_gb": 4, "status": "running"}
    ]
    live_df = pd.DataFrame(live_data)
    
    # Run reconciler
    results = reconcile_inventories(cmdb_df, live_df)
    summary = results["summary"]
    
    assert summary["total_cmdb"] == 4
    assert summary["total_live"] == 4
    assert summary["exact_matches"] == 2
    assert summary["naming_mismatches"] == 1
    assert summary["config_drifts"] == 1
    assert summary["missing"] == 1
    assert summary["untracked"] == 1

def test_agent_orchestration():
    reconciler_output = {
        "summary": {
            "total_cmdb": 2,
            "total_live": 2,
            "exact_matches": 1,
            "missing": 1,
            "untracked": 1,
            "naming_mismatches": 0,
            "config_drifts": 0
        },
        "missing": [{"name": "missing-host", "details": {"environment": "Production", "ip_address": "10.0.0.1"}}],
        "untracked": [{"name": "untracked-host", "details": {"environment": "Production", "ip_address": "10.0.0.2"}}],
        "naming_mismatches": [],
        "config_drifts": []
    }

    workflow_results = run_reconciliation_workflow(reconciler_output)
    
    assert "analysis" in workflow_results
    assert "reconciliation" in workflow_results
    assert "classification" in workflow_results
    assert "risk_assessment" in workflow_results
    assert "recommendation" in workflow_results
    assert "validation" in workflow_results
    
    assert len(workflow_results["execution_logs"]) > 0
