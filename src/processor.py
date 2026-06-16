import pandas as pd
from difflib import SequenceMatcher
import re

def clean_name(name):
    if not isinstance(name, str):
        return ""
    return re.sub(r'[^a-zA-Z0-9]', '', name.lower())

def calculate_similarity(name1, name2):
    c1 = clean_name(name1)
    c2 = clean_name(name2)
    return SequenceMatcher(None, c1, c2).ratio()

def reconcile_inventories(cmdb_df: pd.DataFrame, live_df: pd.DataFrame):
    """
    Compares CMDB inventory against Live discovery inventory.
    Returns a dictionary of:
    - matched: Assets matching perfectly
    - missing: Assets in CMDB but not in Live
    - untracked: Assets in Live but not in CMDB
    - naming_mismatches: Assets that represent the same device but have naming differences
    - config_drift: Assets in both but with configuration discrepancies (IP, Hardware, OS, Status)
    """
    cmdb_df = cmdb_df.fillna("")
    live_df = live_df.fillna("")

    for df in [cmdb_df, live_df]:
        if "name" in df.columns:
            df["name"] = df["name"].astype(str).str.strip()
        if "ip_address" in df.columns:
            df["ip_address"] = df["ip_address"].astype(str).str.strip()

    cmdb_by_name = {row["name"]: row for _, row in cmdb_df.iterrows()}
    live_by_name = {row["name"]: row for _, row in live_df.iterrows()}

    cmdb_names = set(cmdb_by_name.keys())
    live_names = set(live_by_name.keys())

    # 1. Exact Name Matches
    exact_matches = cmdb_names & live_names
    
    # 2. Check for Naming Mismatches
    unresolved_cmdb = cmdb_names - exact_matches
    unresolved_live = live_names - exact_matches

    naming_mismatches = []
    resolved_cmdb_mismatch = set()
    resolved_live_mismatch = set()

    # Match by same IP address first
    for cmdb_name in list(unresolved_cmdb):
        cmdb_row = cmdb_by_name[cmdb_name]
        cmdb_ip = cmdb_row.get("ip_address", "")
        if not cmdb_ip:
            continue
            
        for live_name in list(unresolved_live):
            live_row = live_by_name[live_name]
            live_ip = live_row.get("ip_address", "")
            
            if cmdb_ip == live_ip and cmdb_ip != "":
                similarity = calculate_similarity(cmdb_name, live_name)
                naming_mismatches.append({
                    "cmdb_name": cmdb_name,
                    "live_name": live_name,
                    "ip_address": cmdb_ip,
                    "reason": "Matching IP Address",
                    "similarity": round(similarity * 100, 2),
                    "cmdb_details": cmdb_row.to_dict(),
                    "live_details": live_row.to_dict()
                })
                resolved_cmdb_mismatch.add(cmdb_name)
                resolved_live_mismatch.add(live_name)
                break

    unresolved_cmdb -= resolved_cmdb_mismatch
    unresolved_live -= resolved_live_mismatch

    # Match by high string similarity (similarity >= 0.75)
    for cmdb_name in list(unresolved_cmdb):
        cmdb_row = cmdb_by_name[cmdb_name]
        best_match = None
        best_score = 0.0

        for live_name in list(unresolved_live):
            score = calculate_similarity(cmdb_name, live_name)
            if score > best_score:
                best_score = score
                best_match = live_name

        if best_score >= 0.75 and best_match:
            live_row = live_by_name[best_match]
            naming_mismatches.append({
                "cmdb_name": cmdb_name,
                "live_name": best_match,
                "ip_address": live_row.get("ip_address", cmdb_row.get("ip_address", "")),
                "reason": f"High Name Similarity ({round(best_score * 100, 1)}%)",
                "similarity": round(best_score * 100, 2),
                "cmdb_details": cmdb_row.to_dict(),
                "live_details": live_row.to_dict()
            })
            resolved_cmdb_mismatch.add(cmdb_name)
            resolved_live_mismatch.add(best_match)
            unresolved_live.remove(best_match)

    unresolved_cmdb -= resolved_cmdb_mismatch
    
    # 3. Missing Assets
    missing = []
    for cmdb_name in unresolved_cmdb:
        missing.append({
            "name": cmdb_name,
            "details": cmdb_by_name[cmdb_name].to_dict()
        })

    # 4. Untracked Assets
    untracked = []
    for live_name in unresolved_live:
        untracked.append({
            "name": live_name,
            "details": live_by_name[live_name].to_dict()
        })

    # 5. Configuration Drift
    config_drifts = []

    def check_drift(cmdb_item, live_item, actual_name):
        drifts = {}
        fields_to_compare = {
            "ip_address": "IP Address",
            "os": "Operating System",
            "cpu_cores": "CPU Cores",
            "memory_gb": "Memory (GB)",
            "status": "Operational Status"
        }
        
        for field, display in fields_to_compare.items():
            cmdb_val = cmdb_item.get(field, "")
            live_val = live_item.get(field, "")
            
            if field == "status":
                c_status = str(cmdb_val).lower()
                l_status = str(live_val).lower()
                if (c_status == "active" and l_status in ["running", "active", "online"]):
                    continue
                if (c_status in ["stopped", "inactive"] and l_status in ["stopped", "inactive"]):
                    continue

            if str(cmdb_val).strip().lower() != str(live_val).strip().lower():
                drifts[field] = {
                    "field": field,
                    "display": display,
                    "cmdb": cmdb_val,
                    "live": live_val
                }
                
        if drifts:
            config_drifts.append({
                "name": actual_name,
                "cmdb_name": cmdb_item["name"],
                "live_name": live_item["name"],
                "environment": cmdb_item.get("environment", live_item.get("environment", "")),
                "owner": cmdb_item.get("owner", live_item.get("owner", "")),
                "drifts": drifts
            })

    # Compare exact matches
    for name in exact_matches:
        check_drift(cmdb_by_name[name], live_by_name[name], name)

    # Compare naming mismatches
    for item in naming_mismatches:
        check_drift(item["cmdb_details"], item["live_details"], item["cmdb_name"])

    return {
        "summary": {
            "total_cmdb": len(cmdb_df),
            "total_live": len(live_df),
            "exact_matches": len(exact_matches),
            "missing": len(missing),
            "untracked": len(untracked),
            "naming_mismatches": len(naming_mismatches),
            "config_drifts": len(config_drifts)
        },
        "missing": missing,
        "untracked": untracked,
        "naming_mismatches": naming_mismatches,
        "config_drifts": config_drifts
    }
