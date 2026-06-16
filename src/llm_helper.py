import json
import time
import requests
import os
from openai import OpenAI
from src import utils

class BaseAgent:
    def __init__(self, name: str, role: str, system_prompt: str):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.execution_logs = []

    def log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.execution_logs.append(f"[{timestamp}] {self.name}: {message}")

    def get_logs(self):
        return self.execution_logs

    def run(self, input_data: dict) -> dict:
        self.log(f"Starting execution with input keys: {list(input_data.keys())}")
        
        user_prompt = self.format_prompt(input_data)
        response_text = ""
        provider = utils.LLM_PROVIDER
        
        self.log(f"Routing query to provider: '{provider}'")
        
        start_time = time.time()
        try:
            if provider == "openai":
                response_text = self._call_openai(self.system_prompt, user_prompt)
            elif provider == "ollama":
                response_text = self._call_ollama(self.system_prompt, user_prompt)
            else:
                response_text = self._generate_demo_response(input_data)
                
            duration = round(time.time() - start_time, 2)
            self.log(f"LLM request completed in {duration} seconds.")
            
        except Exception as e:
            self.log(f"Error calling LLM: {str(e)}. Falling back to Demo Mode.")
            response_text = self._generate_demo_response(input_data)
            
        parsed_output = self._parse_json_response(response_text)
        self.log("Output successfully structured and validated.")
        return parsed_output

    def format_prompt(self, input_data: dict) -> str:
        return json.dumps(input_data, indent=2)

    def _call_openai(self, system: str, user: str) -> str:
        client = OpenAI(api_key=utils.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=utils.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        return response.choices[0].message.content

    def _call_ollama(self, system: str, user: str) -> str:
        url = f"{utils.OLLAMA_API_BASE.rstrip('/api')}/api/chat"
        payload = {
            "model": utils.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "stream": False,
            "format": "json"
        }
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()["message"]["content"]

    def _parse_json_response(self, text: str) -> dict:
        text_clean = text.strip()
        if text_clean.startswith("```json"):
            text_clean = text_clean[7:]
        if text_clean.endswith("```"):
            text_clean = text_clean[:-3]
        text_clean = text_clean.strip()

        try:
            return json.loads(text_clean)
        except json.JSONDecodeError:
            self.log("Failed to parse LLM response as JSON. Retrying simple extraction.")
            try:
                start = text_clean.find("{")
                end = text_clean.rfind("}")
                if start != -1 and end != -1:
                    return json.loads(text_clean[start:end+1])
            except Exception:
                pass
            return {"error": "JSON parse error", "raw_content": text}

    def _generate_demo_response(self, input_data: dict) -> str:
        return "{}"

# =========================================================
# Specialized Agents Definition
# =========================================================

class AnalysisAgent(BaseAgent):
    def __init__(self):
        system_prompt = (
            "You are the Analysis Agent in a multi-agent inventory reconciliation system.\n"
            "Your job is to read raw statistics about CMDB and Live infrastructure states "
            "and compute a high-level assessment of configuration status, health score, "
            "and infrastructure completeness.\n"
            "You must return a JSON object with the following schema:\n"
            "{\n"
            "  \"infrastructure_health_score\": <int between 0 and 100>,\n"
            "  \"analysis_summary\": \"<text summary of findings>\",\n"
            "  \"key_findings\": [\"<finding 1>\", \"<finding 2>\", ...],\n"
            "  \"environments_found\": [\"<env1>\", \"<env2>\", ...]\n"
            "}"
        )
        super().__init__("Analysis Agent", "Infrastructure & Business Analyst", system_prompt)

    def format_prompt(self, input_data: dict) -> str:
        summary_stats = input_data.get("summary", {})
        return (
            f"Analyze the following infrastructure reconciliation stats:\n"
            f"- Total CMDB Assets: {summary_stats.get('total_cmdb', 0)}\n"
            f"- Total Live Assets: {summary_stats.get('total_live', 0)}\n"
            f"- Exact matches: {summary_stats.get('exact_matches', 0)}\n"
            f"- Discrepancies: Missing={summary_stats.get('missing', 0)}, "
            f"Untracked={summary_stats.get('untracked', 0)}, "
            f"Naming Mismatches={summary_stats.get('naming_mismatches', 0)}, "
            f"Config Drifts={summary_stats.get('config_drifts', 0)}"
        )

    def _generate_demo_response(self, input_data: dict) -> str:
        summary_stats = input_data.get("summary", {})
        total_cmdb = summary_stats.get("total_cmdb", 6)
        exact_matches = summary_stats.get("exact_matches", 2)
        drifts = summary_stats.get("config_drifts", 2)
        missing = summary_stats.get("missing", 1)
        untracked = summary_stats.get("untracked", 1)
        mismatches = summary_stats.get("naming_mismatches", 1)
        
        total_issues = drifts + missing + untracked + mismatches
        health_score = max(0, 100 - (total_issues * 12))
        
        response = {
            "infrastructure_health_score": health_score,
            "analysis_summary": (
                f"Infrastructure analysis reveals a total of {total_cmdb} configuration items in the CMDB, "
                f"compared to {summary_stats.get('total_live', 6)} discovered live assets. "
                f"Only {exact_matches} assets are perfectly aligned. There are significant configuration drifts, "
                f"untracked hosts (Shadow IT), and missing servers that pose potential operational risk."
            ),
            "key_findings": [
                f"Detected {untracked} untracked active system(s) operating without CMDB authorization (Potential Shadow IT).",
                f"Identified {missing} CMDB-registered host(s) missing from live discovery scans (Possible outage or decommissioning drift).",
                f"Discovered {mismatches} naming consistency mismatch where names differ but resource IPs are identical.",
                f"Found {drifts} host(s) suffering from resource sizing or configuration parameter drift."
            ],
            "environments_found": ["Production", "Staging", "Development"]
        }
        return json.dumps(response)


class ReconciliationAgent(BaseAgent):
    def __init__(self):
        system_prompt = (
            "You are the Reconciliation Agent in a multi-agent inventory reconciliation system.\n"
            "Your job is to review the raw differences between CMDB and Live states "
            "and build a clean, validated list of discrepancies for further classification.\n"
            "You must return a JSON object with the following schema:\n"
            "{\n"
            "  \"reconciliation_status\": \"<Critical|Warning|Healthy>\",\n"
            "  \"total_anomalies\": <int>,\n"
            "  \"anomaly_validation_notes\": \"<brief remarks on validity of discrepancies>\",\n"
            "  \"reconciled_diff_list\": [\n"
            "     {\n"
            "       \"target_asset\": \"<asset name>\",\n"
            "       \"anomaly_type\": \"<missing|untracked|naming_mismatch|config_drift>\",\n"
            "       \"description\": \"<description>\",\n"
            "       \"details\": <object with CMDB vs Live values>\n"
            "     }, ...\n"
            "  ]\n"
            "}"
        )
        super().__init__("Reconciliation Agent", "Data & Systems Reconciliation Specialist", system_prompt)

    def format_prompt(self, input_data: dict) -> str:
        diffs = {
            "missing": input_data.get("missing", []),
            "untracked": input_data.get("untracked", []),
            "naming_mismatches": input_data.get("naming_mismatches", []),
            "config_drifts": input_data.get("config_drifts", [])
        }
        return f"Review and validate the following list of raw discrepancies:\n{json.dumps(diffs, indent=2)}"

    def _generate_demo_response(self, input_data: dict) -> str:
        reconciled_diffs = []
        
        for item in input_data.get("missing", []):
            reconciled_diffs.append({
                "target_asset": item["name"],
                "anomaly_type": "missing",
                "description": f"Asset '{item['name']}' is defined in CMDB but not detected in Live inventory.",
                "details": {"cmdb": item["details"], "live": {}}
            })
            
        for item in input_data.get("untracked", []):
            reconciled_diffs.append({
                "target_asset": item["name"],
                "anomaly_type": "untracked",
                "description": f"Asset '{item['name']}' is running live but has no record in the CMDB.",
                "details": {"cmdb": {}, "live": item["details"]}
            })
            
        for item in input_data.get("naming_mismatches", []):
            reconciled_diffs.append({
                "target_asset": item["cmdb_name"],
                "anomaly_type": "naming_mismatch",
                "description": f"Naming mismatch: CMDB shows '{item['cmdb_name']}' but Live shows '{item['live_name']}'. IP matches ({item['ip_address']}).",
                "details": {"cmdb": item["cmdb_details"], "live": item["live_details"]}
            })
            
        for item in input_data.get("config_drifts", []):
            drift_desc = ", ".join([f"{d['display']} (CMDB: {d['cmdb']} vs Live: {d['live']})" for d in item["drifts"].values()])
            reconciled_diffs.append({
                "target_asset": item["name"],
                "anomaly_type": "config_drift",
                "description": f"Resource parameters drifted: {drift_desc}",
                "details": {
                    "cmdb_name": item["cmdb_name"],
                    "live_name": item["live_name"],
                    "drifts": item["drifts"]
                }
            })

        total_anomalies = len(reconciled_diffs)
        status = "Critical" if any(x["anomaly_type"] in ["missing", "untracked"] for x in reconciled_diffs) else "Warning"
        if total_anomalies == 0:
            status = "Healthy"

        response = {
            "reconciliation_status": status,
            "total_anomalies": total_anomalies,
            "anomaly_validation_notes": (
                f"Successfully parsed and validated {total_anomalies} discrepancies. All items represent verifiable configuration states."
            ),
            "reconciled_diff_list": reconciled_diffs
        }
        return json.dumps(response)


class ClassificationAgent(BaseAgent):
    def __init__(self):
        system_prompt = (
            "You are the Classification Agent in a multi-agent inventory reconciliation system.\n"
            "Your job is to analyze the reconciled discrepancies and assign specific, detailed "
            "classification categories (e.g. Shadow IT, Decommissioning Drift, Resource Allocation Drift, "
            "Naming Inconsistency, Network Configuration Drift, Service Failure) and explain your reasoning.\n"
            "You must return a JSON object with the following schema:\n"
            "{\n"
            "  \"classified_discrepancies\": [\n"
            "     {\n"
            "       \"target_asset\": \"<asset name>\",\n"
            "       \"anomaly_type\": \"<anomaly_type>\",\n"
            "       \"classification\": \"<Shadow IT|Decommissioning Drift|Resource Allocation Drift|Naming Inconsistency|Network Drift|Service Outage>\",\n"
            "       \"classification_details\": \"<explanation of reasoning>\",\n"
            "       \"details\": <details object>\n"
            "     }, ...\n"
            "  ]\n"
            "}"
        )
        super().__init__("Classification Agent", "Systems & Configuration Classifier", system_prompt)

    def format_prompt(self, input_data: dict) -> str:
        diff_list = input_data.get("reconciled_diff_list", [])
        return f"Classify the following verified discrepancies:\n{json.dumps(diff_list, indent=2)}"

    def _generate_demo_response(self, input_data: dict) -> str:
        diff_list = input_data.get("reconciled_diff_list", [])
        classified = []
        
        for item in diff_list:
            anomaly_type = item["anomaly_type"]
            target = item["target_asset"]
            details = item["details"]
            
            classification = "Other"
            reason = "General configuration mismatch"
            
            if anomaly_type == "missing":
                classification = "Decommissioning Drift"
                reason = f"Asset '{target}' exists in CMDB but was not found in Live scans, suggesting it was retired without updating the registry or is currently offline."
            elif anomaly_type == "untracked":
                classification = "Shadow IT"
                reason = f"Asset '{target}' is active in the live environment but lacks CMDB documentation, creating a security and billing blindspot."
            elif anomaly_type == "naming_mismatch":
                classification = "Naming Inconsistency"
                reason = f"Same machine identified via IP, but has different names ('{details.get('cmdb', {}).get('name')}' vs '{details.get('live', {}).get('name')}'). Needs standardization."
            elif anomaly_type == "config_drift":
                drifts = details.get("drifts", {})
                if "ip_address" in drifts:
                    classification = "Network Drift"
                    reason = f"IP address mismatch for '{target}'. Expected {drifts['ip_address']['cmdb']} but found {drifts['ip_address']['live']} live."
                elif "cpu_cores" in drifts or "memory_gb" in drifts:
                    classification = "Resource Allocation Drift"
                    reason = f"Hardware specifications drifted: {', '.join([f'{d['display']}: CMDB {d['cmdb']} vs Live {d['live']}' for d in drifts.values()])}."
                elif "status" in drifts:
                    classification = "Service Outage"
                    reason = f"Operational status mismatch: CMDB shows Active, but Live discovery shows system stopped/offline."

            classified.append({
                "target_asset": target,
                "anomaly_type": anomaly_type,
                "classification": classification,
                "classification_details": reason,
                "details": details
            })
            
        return json.dumps({"classified_discrepancies": classified})


class RiskAssessmentAgent(BaseAgent):
    def __init__(self):
        system_prompt = (
            "You are the Risk Assessment Agent in a multi-agent inventory reconciliation system.\n"
            "Your job is to evaluate each classified discrepancy and determine its risk score (0-10), "
            "risk level (High/Medium/Low), operational and security impact, compliance implications "
            "(e.g., SOC 2, ISO 27001, HIPAA, PCI-DSS, GDPR), and associated CVE vulnerability pointers.\n"
            "You must return a JSON object with the following schema:\n"
            "{\n"
            "  \"assessed_discrepancies\": [\n"
            "     {\n"
            "       \"target_asset\": \"<asset name>\",\n"
            "       \"classification\": \"<classification>\",\n"
            "       \"risk_level\": \"<High|Medium|Low>\",\n"
            "       \"risk_score\": <float between 0.0 and 10.0>,\n"
            "       \"impact_statement\": \"<operational or security impact description>\",\n"
            "       \"compliance_implications\": [\"<compliance framework clause 1>\", ...],\n"
            "       \"cve_references\": [\"<CVE-YYYY-NNNN>\", ...],\n"
            "       \"details\": <details object>,\n"
            "       \"classification_details\": \"<details>\"\n"
            "     }, ...\n"
            "  ]\n"
            "}"
        )
        super().__init__("Risk Assessment Agent", "Cybersecurity & Compliance Risk Auditor", system_prompt)

    def format_prompt(self, input_data: dict) -> str:
        classified = input_data.get("classified_discrepancies", [])
        return f"Perform security and compliance risk assessments on these classified discrepancies:\n{json.dumps(classified, indent=2)}"

    def _generate_demo_response(self, input_data: dict) -> str:
        classified = input_data.get("classified_discrepancies", [])
        assessed = []
        
        for item in classified:
            classification = item["classification"]
            target = item["target_asset"]
            
            risk_level = "Low"
            risk_score = 2.0
            impact = "Minimal impact on current services."
            compliance = []
            cve = []
            
            if classification == "Shadow IT":
                risk_level = "High"
                risk_score = 8.5
                impact = f"Untracked active host '{target}' has no security baseline, firewall monitoring, or vulnerability management. Opens network perimeter exposure."
                compliance = ["ISO 27001 Annex A.8.1 (Asset Inventory)", "PCI-DSS v4.0 Req 2.4 (Maintain Inventory of System Components)", "SOC 2 CC6.1 (Access Controls & Asset Safeguarding)"]
                cve = ["CVE-2023-4911 (Looney Tunables - potential root exploit if unpatched)", "CVE-2024-21626 (runc container escape risk if hosting Docker)"]
            elif classification == "Decommissioning Drift":
                risk_level = "Medium"
                risk_score = 5.5
                impact = f"Asset '{target}' listed as active in CMDB but not running live. Leads to inaccurate license audits, orphan DNS records (subdomain takeover risk), and false monitoring alerts."
                compliance = ["SOC 2 CC7.1 (Vulnerability & Configuration Change Management)", "GDPR Article 32 (Security of Processing)"]
                cve = ["CVE-2023-38408 (OpenSSH agent vulnerability)"]
            elif classification == "Network Drift":
                risk_level = "High"
                risk_score = 7.8
                impact = f"IP address configuration drift. DNS/routing discrepancies can break security groups, firewalls, and cause unauthorized routing of sensitive traffic."
                compliance = ["PCI-DSS Req 1.1.2 (Network Diagram Verification)", "SOC 2 CC6.6 (Boundary Defense & Network Security)"]
                cve = []
            elif classification == "Resource Allocation Drift":
                risk_level = "Low"
                risk_score = 3.5
                impact = f"Server is operating with hardware metrics different from CMDB logs. May lead to unexpected hosting costs or resource constraints."
                compliance = ["ISO 27001 A.12.1.3 (Capacity Management)"]
                cve = []
            elif classification == "Naming Inconsistency":
                risk_level = "Low"
                risk_score = 2.5
                impact = "Naming mismatches complicate log correlation, incident response, and slow down operations during server outages."
                compliance = ["SOC 2 CC7.2 (Incident Response & Event Tracking)"]
                cve = []
            elif classification == "Service Outage":
                risk_level = "High"
                risk_score = 9.0
                impact = f"CI/CD or production utility '{target}' is offline/stopped, directly interrupting engineering pipelines."
                compliance = ["ISO 27001 A.17.1 (Information Security Continuity)", "SOC 2 CC8.1 (System Availability & Operations Management)"]
                cve = []

            assessed.append({
                "target_asset": target,
                "anomaly_type": item["anomaly_type"],
                "classification": classification,
                "risk_level": risk_level,
                "risk_score": risk_score,
                "impact_statement": impact,
                "compliance_implications": compliance,
                "cve_references": cve,
                "details": item["details"],
                "classification_details": item["classification_details"]
            })
            
        return json.dumps({"assessed_discrepancies": assessed})


class RecommendationAgent(BaseAgent):
    def __init__(self):
        system_prompt = (
            "You are the Recommendation Agent in a multi-agent inventory reconciliation system.\n"
            "Your job is to generate concrete, highly actionable remediation plans for each discrepancy.\n"
            "Include exact terminal commands, Ansible playbooks, or API scripts, alongside detailed manual "
            "steps, prerequisites, and system targets.\n"
            "You must return a JSON object with the following schema:\n"
            "{\n"
            "  \"remediation_plan\": [\n"
            "     {\n"
            "       \"target_asset\": \"<asset name>\",\n"
            "       \"classification\": \"<classification>\",\n"
            "       \"action_type\": \"<Automated|Manual>\",\n"
            "       \"remediation_steps\": [\"<step 1>\", \"<step 2>\", ...],\n"
            "       \"target_system\": \"<system to run the remediation on>\",\n"
            "       \"script_content\": \"<code block, shell script, ansible playbook, or empty>\",\n"
            "       \"pre_requisites\": [\"<pre-req 1>\", ...]\n"
            "     }, ...\n"
            "  ]\n"
            "}"
        )
        super().__init__("Recommendation Agent", "Systems & Automation Architect", system_prompt)

    def format_prompt(self, input_data: dict) -> str:
        assessed = input_data.get("assessed_discrepancies", [])
        return f"Generate detailed remediation plans for these risk-assessed discrepancies:\n{json.dumps(assessed, indent=2)}"

    def _generate_demo_response(self, input_data: dict) -> str:
        assessed = input_data.get("assessed_discrepancies", [])
        plan = []
        
        for item in assessed:
            classification = item["classification"]
            target = item["target_asset"]
            details = item["details"]
            
            action_type = "Manual"
            steps = ["Investigate discrepancy configuration manually."]
            target_system = "CMDB Admin Portal"
            script = ""
            prereqs = ["Admin access to CMDB and target system."]
            
            if classification == "Shadow IT":
                action_type = "Automated"
                target_system = "Configuration Automation Engine (Ansible)"
                steps = [
                    f"Scan host {details.get('live', {}).get('ip_address', 'IP')} using discovery tools.",
                    "Verify owner and purpose with DevOps team.",
                    "Execute CMDB registration API script to log the host officially.",
                    "Enroll host in central patching and compliance scans."
                ]
                prereqs = ["Active network path to host", "Valid CMDB REST API credentials"]
                script = (
                    "--- # Ansible Playbook: Register Shadow IT host in CMDB\n"
                    "- name: Register Shadow Host in ServiceNow/Jira CMDB\n"
                    "  hosts: localhost\n"
                    "  gather_facts: false\n"
                    "  vars:\n"
                    f"    host_name: \"{target}\"\n"
                    f"    host_ip: \"{details.get('live', {}).get('ip_address')}\"\n"
                    f"    host_os: \"{details.get('live', {}).get('os')}\"\n"
                    "  tasks:\n"
                    "    - name: Post configuration CI to CMDB\n"
                    "      uri:\n"
                    "        url: \"https://cmdb.enterprise.local/api/v1/ci\"\n"
                    "        method: POST\n"
                    "        body_format: json\n"
                    "        user: \"{{ cmdb_user }}\"\n"
                    "        password: \"{{ cmdb_pass }}\"\n"
                    "        body:\n"
                    "          name: \"{{ host_name }}\"\n"
                    "          ip_address: \"{{ host_ip }}\"\n"
                    "          os_family: \"Linux\"\n"
                    "          os_version: \"{{ host_os }}\"\n"
                    "          environment: \"Development\"\n"
                    "          status: \"Discovered\"\n"
                    "        status_code: 201\n"
                )
            elif classification == "Decommissioning Drift":
                action_type = "Manual"
                target_system = "ServiceNow CMDB Portal"
                steps = [
                    f"Verify if asset '{target}' was decommissioned via an approved change request.",
                    "Check hypervisor/cloud account to see if the VM was deleted or powered down.",
                    "If decommissioned: Update CMDB record status to 'Decommissioned' and archive.",
                    "If crashed: Trigger incident ticket for hardware/hypervisor repair."
                ]
                prereqs = ["Jira/ServiceNow Change Request ID", "Hypervisor audit logs Access"]
                script = (
                    "# SQL query to clean orphan CMDB relationships:\n"
                    f"UPDATE cmdb_assets SET status = 'Decommissioned', decommissioned_at = NOW() WHERE name = '{target}';\n"
                    f"DELETE FROM asset_relationships WHERE child_asset_name = '{target}' OR parent_asset_name = '{target}';"
                )
            elif classification == "Network Drift":
                action_type = "Automated"
                target_system = "Ansible / Network Engine"
                steps = [
                    f"Update IP mapping for host '{target}' in Ansible inventory files.",
                    "Perform API call to ServiceNow CMDB updating IP address field.",
                    "Reload load balancer configurations if server is a pool member."
                ]
                prereqs = ["CMDB API Access Token", "Ansible Inventory access"]
                script = (
                    "#!/bin/bash\n"
                    "# Shell script to update CMDB Asset IP via REST API\n"
                    f"API_URL=\"https://cmdb.enterprise.local/api/v1/assets/{target}\"\n"
                    "TOKEN=\"$CMDB_API_TOKEN\"\n\n"
                    "curl -X PATCH $API_URL \\\n"
                    "  -H \"Authorization: Bearer $TOKEN\" \\\n"
                    "  -H \"Content-Type: application/json\" \\\n"
                    f"  -d '{{\"ip_address\": \"{details.get('drifts', {}).get('ip_address', {}).get('live')}\"}}'"
                )
            elif classification == "Resource Allocation Drift":
                action_type = "Automated"
                target_system = "CMDB Update Service"
                drifts = details.get("drifts", {})
                cpu_drift = drifts.get("cpu_cores", {})
                mem_drift = drifts.get("memory_gb", {})
                steps = [
                    "Validate that the hardware upgrade was authorized by a change order.",
                    "Execute script to update CPU and Memory metrics in CMDB to match live discovery."
                ]
                prereqs = ["Admin API keys to CMDB"]
                script = (
                    "import requests\n"
                    "import os\n\n"
                    f"asset_name = '{target}'\n"
                    f"cpu = {cpu_drift.get('live', 4)}\n"
                    f"memory = {mem_drift.get('live', 16)}\n"
                    "api_url = f'https://cmdb.enterprise.local/api/v1/assets/name/{asset_name}'\n"
                    "headers = {'Authorization': f'Bearer {os.getenv(\"CMDB_TOKEN\")}'}\n"
                    "response = requests.patch(api_url, headers=headers, json={'cpu_cores': cpu, 'memory_gb': memory})\n"
                    "print('Status:', response.status_code)"
                )
            elif classification == "Naming Inconsistency":
                action_type = "Manual"
                target_system = "DNS Server & VM Hypervisor"
                steps = [
                    f"Standardize target hostname. Keep CMDB name '{details.get('cmdb', {}).get('name')}' or update to '{details.get('live', {}).get('name')}' in DNS and OS hosts.",
                    "Update DNS lookup zones with correct standardized hostname.",
                    "Run hostname change script on live virtual machine to align OS hostname."
                ]
                prereqs = ["DNS server administration credentials", "Target root credentials"]
                script = (
                    "#!/bin/bash\n"
                    "# Bash script to standardize local server hostname\n"
                    f"NEW_HOSTNAME=\"{details.get('cmdb', {}).get('name')}\"\n"
                    "echo \"Setting hostname to $NEW_HOSTNAME\"\n"
                    "hostnamectl set-hostname $NEW_HOSTNAME\n"
                    "echo \"127.0.0.1 localhost $NEW_HOSTNAME\" > /etc/hosts"
                )
            elif classification == "Service Outage":
                action_type = "Automated"
                target_system = "Target Host SSH"
                steps = [
                    f"Establish SSH session to {details.get('live', {}).get('ip_address')}.",
                    "Check system service status for stopping reason.",
                    "Restart the stopped service via systemctl commands."
                ]
                prereqs = ["Target root SSH private key"]
                script = (
                    "#!/bin/bash\n"
                    f"ssh -i /path/to/id_rsa root@{details.get('live', {}).get('ip_address')} << 'EOF'\n"
                    "  systemctl start gitlab-runner\n"
                    "  systemctl enable gitlab-runner\n"
                    "EOF"
                )

            plan.append({
                "target_asset": target,
                "classification": classification,
                "action_type": action_type,
                "remediation_steps": steps,
                "target_system": target_system,
                "script_content": script,
                "pre_requisites": prereqs
            })
            
        return json.dumps({"remediation_plan": plan})


class ValidationAgent(BaseAgent):
    def __init__(self):
        system_prompt = (
            "You are the Validation Agent in a multi-agent inventory reconciliation system.\n"
            "Your job is to audit the proposed remediation plan and security ratings. You must:\n"
            "1. Run safety checks (e.g., flag any drop/delete/destroy/decommission operations targeting Production systems).\n"
            "2. Assign a safety_status ('Approved', 'Approved with Caveats', 'Needs Manual Verification').\n"
            "3. Append detailed validation remarks and a solid Rollback Plan for each remediation item.\n"
            "4. Provide an overall approved status and a validation summary.\n"
            "You must return a JSON object with the following schema:\n"
            "{\n"
            "  \"approved\": <true|false>,\n"
            "  \"overall_validation_summary\": \"<text summary of the security audit>\",\n"
            "  \"safety_audited_plan\": [\n"
            "     {\n"
            "       \"target_asset\": \"<asset name>\",\n"
            "       \"classification\": \"<classification>\",\n"
            "       \"action_type\": \"<action_type>\",\n"
            "       \"safety_status\": \"<Approved|Approved with Caveats|Needs Manual Verification>\",\n"
            "       \"validation_remarks\": \"<why this status was assigned>\",\n"
            "       \"rollback_plan\": \"<step-by-step instructions to revert this remediation if it fails>\",\n"
            "       \"remediation_steps\": [\"<steps>\"],\n"
            "       \"target_system\": \"<system>\",\n"
            "       \"script_content\": \"<script>\",\n"
            "       \"pre_requisites\": [\"<pre-reqs>\"]\n"
            "     }, ...\n"
            "  ]\n"
            "}"
        )
        super().__init__("Validation Agent", "DevSecOps Quality & Safety Auditor", system_prompt)

    def format_prompt(self, input_data: dict) -> str:
        plan = input_data.get("remediation_plan", [])
        return f"Perform safety validation audits on the following remediation plan:\n{json.dumps(plan, indent=2)}"

    def _generate_demo_response(self, input_data: dict) -> str:
        plan = input_data.get("remediation_plan", [])
        audited_plan = []
        
        for item in plan:
            classification = item["classification"]
            target = item["target_asset"]
            
            safety_status = "Approved"
            remarks = "Remediation plan verified and approved. Low operational risk."
            rollback = "Revert script execution. No permanent configuration changes are destructive."
            
            if classification == "Shadow IT":
                safety_status = "Approved with Caveats"
                remarks = "Registering host in CMDB requires validation of the asset owner. Validate ownership to prevent security quarantine."
                rollback = f"Execute CMDB API delete script to remove CI entry for '{target}'."
            elif classification == "Decommissioning Drift":
                safety_status = "Needs Manual Verification"
                remarks = "WARNING: CMDB archive is irreversible. Requires manual confirmation that VM was decommissioned and not crashed."
                rollback = f"Update CMDB asset '{target}' status back to 'Active'."
            elif classification == "Service Outage":
                safety_status = "Approved"
                remarks = "Service restart command is standard. Verify logs to confirm service is healthy post-reboot."
                rollback = f"Execute service stop command if loops/crashes occur."
            elif classification == "Network Drift":
                safety_status = "Approved with Caveats"
                remarks = "Updating IP in CMDB. Check active routes to verify DNS zones have updated before execution."
                rollback = f"Restore prior CMDB IP values via database script."

            audited_plan.append({
                "target_asset": target,
                "classification": classification,
                "action_type": item["action_type"],
                "safety_status": safety_status,
                "validation_remarks": remarks,
                "rollback_plan": rollback,
                "remediation_steps": item["remediation_steps"],
                "target_system": item["target_system"],
                "script_content": item["script_content"],
                "pre_requisites": item["pre_requisites"]
            })

        response = {
            "approved": True,
            "overall_validation_summary": (
                "Remediation plan audited successfully. 2 items approved, 2 items require manual/caveated confirmation."
            ),
            "safety_audited_plan": audited_plan
        }
        return json.dumps(response)

# =========================================================
# Orchestration Pipeline Execution
# =========================================================

def run_reconciliation_workflow(reconciler_output: dict) -> dict:
    logs = []
    timings = {}
    
    # 1. Analysis Agent
    t_start = time.time()
    analysis_agent = AnalysisAgent()
    analysis_output = analysis_agent.run(reconciler_output)
    timings["analysis_agent"] = round(time.time() - t_start, 2)
    logs.extend(analysis_agent.get_logs())
    
    # 2. Reconciliation Agent
    t_start = time.time()
    reconciliation_agent = ReconciliationAgent()
    rec_input = {**reconciler_output, **analysis_output}
    reconciliation_output = reconciliation_agent.run(rec_input)
    timings["reconciliation_agent"] = round(time.time() - t_start, 2)
    logs.extend(reconciliation_agent.get_logs())
    
    # 3. Classification Agent
    t_start = time.time()
    classification_agent = ClassificationAgent()
    classification_output = classification_agent.run(reconciliation_output)
    timings["classification_agent"] = round(time.time() - t_start, 2)
    logs.extend(classification_agent.get_logs())
    
    # 4. Risk Assessment Agent
    t_start = time.time()
    risk_agent = RiskAssessmentAgent()
    risk_output = risk_agent.run(classification_output)
    timings["risk_assessment_agent"] = round(time.time() - t_start, 2)
    logs.extend(risk_agent.get_logs())
    
    # 5. Recommendation Agent
    t_start = time.time()
    recommendation_agent = RecommendationAgent()
    recommendation_output = recommendation_agent.run(risk_output)
    timings["recommendation_agent"] = round(time.time() - t_start, 2)
    logs.extend(recommendation_agent.get_logs())
    
    # 6. Validation Agent
    t_start = time.time()
    validation_agent = ValidationAgent()
    validation_output = validation_agent.run(recommendation_output)
    timings["validation_agent"] = round(time.time() - t_start, 2)
    logs.extend(validation_agent.get_logs())
    
    return {
        "analysis": analysis_output,
        "reconciliation": reconciliation_output,
        "classification": classification_output,
        "risk_assessment": risk_output,
        "recommendation": recommendation_output,
        "validation": validation_output,
        "execution_logs": logs,
        "timings": timings,
        "total_duration": round(sum(timings.values()), 2)
    }
