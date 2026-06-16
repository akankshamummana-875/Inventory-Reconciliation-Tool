import streamlit as st
import pandas as pd
import json
import os
import time
import plotly.express as px

from src.processor import reconcile_inventories
from src.llm_helper import run_reconciliation_workflow
from src.utils import inject_premium_style, generate_pdf_report, LLM_PROVIDER, OPENAI_API_KEY, OLLAMA_API_BASE, OLLAMA_MODEL

# ---------------------------------------------------------
# Page Configurations
# ---------------------------------------------------------
st.set_page_config(
    page_title="InfraGuard | AI Inventory Reconciliation",
    page_icon="🤖",
    layout="wide"
)

# Inject custom premium dark CSS styling
inject_premium_style()

# Initialize session state variables
if "workflow_results" not in st.session_state:
    st.session_state["workflow_results"] = None
if "reconciler_output" not in st.session_state:
    st.session_state["reconciler_output"] = None
if "uploaded_cmdb" not in st.session_state:
    st.session_state["uploaded_cmdb"] = None
if "uploaded_live" not in st.session_state:
    st.session_state["uploaded_live"] = None

# =========================================================
# Sidebar Controls & Settings
# =========================================================
with st.sidebar:
    st.markdown('<div style="text-align: center; padding: 10px 0;"><h2 style="margin: 0; color: #38BDF8 !important;">🤖 INFRAGUARD</h2><span style="color: #94A3B8; font-size: 0.8rem; font-weight: 500;">AI Reconciliation Agent Loop</span></div>', unsafe_allow_html=True)
    st.markdown("---")
    
    # Provider selection
    st.markdown("### 🔌 LLM Provider")
    provider_options = ["Recruiter Demo Mode (Mock LLM)", "OpenAI API", "Ollama (Local)"]
    selected_provider = st.selectbox("Active Provider:", provider_options)
    
    if selected_provider == "OpenAI API":
        LLM_PROVIDER = "openai"
        key = st.text_input("Enter OpenAI API Key:", type="password", value=OPENAI_API_KEY)
        if key:
            os.environ["OPENAI_API_KEY"] = key
    elif selected_provider == "Ollama (Local)":
        LLM_PROVIDER = "ollama"
        OLLAMA_API_BASE = st.text_input("Ollama Endpoint Base:", value=OLLAMA_API_BASE)
    else:
        LLM_PROVIDER = "demo"
        
    st.markdown("---")
    
    # Quick Reset Button
    if st.session_state["workflow_results"] is not None:
        if st.button("🔄 Reset & Start New Audit", use_container_width=True):
            st.session_state["workflow_results"] = None
            st.session_state["reconciler_output"] = None
            st.session_state["uploaded_cmdb"] = None
            st.session_state["uploaded_live"] = None
            st.rerun()
            
    st.markdown('<div style="font-size: 0.7rem; color: #64748B; text-align: center; margin-top: 15px;">InfraGuard Prototype v2.0.0<br/>AI Prototype Challenge submission</div>', unsafe_allow_html=True)

# =========================================================
# Ingestion Screen
# =========================================================
st.markdown('# 🤖 InfraGuard Reconciliation System')

if st.session_state["workflow_results"] is None:
    st.markdown("### 📥 Input Data Panel")
    st.markdown("Upload your CMDB inventory (CSV) and discovered live state (JSON) to launch the 6-agent audit loop.")
    
    col1, col2 = st.columns(2)
    with col1:
        cmdb_file = st.file_uploader("📁 CMDB Target State (CSV)", type=["csv"], key="cmdb_main")
        if cmdb_file:
            st.session_state["uploaded_cmdb"] = pd.read_csv(cmdb_file)
            st.success("CMDB CSV loaded successfully!")
    with col2:
        live_file = st.file_uploader("📁 Live Discovered State (JSON)", type=["json"], key="live_main")
        if live_file:
            try:
                live_data = json.load(live_file)
                st.session_state["uploaded_live"] = pd.DataFrame(live_data)
                st.success("Live discovered state loaded successfully!")
            except Exception as e:
                st.error(f"Error parsing JSON: {str(e)}")
                
    st.markdown("<br/>", unsafe_allow_html=True)
    
    run_col1, run_col2 = st.columns([1, 3])
    with run_col1:
        if st.button("🚀 Run AI Reconciliation", use_container_width=True):
            if st.session_state["uploaded_cmdb"] is None or st.session_state["uploaded_live"] is None:
                st.error("Please upload both CMDB CSV and Live JSON files first.")
            else:
                with st.spinner("Processing Agentic workflow..."):
                    reconciler_output = reconcile_inventories(
                        st.session_state["uploaded_cmdb"],
                        st.session_state["uploaded_live"]
                    )
                    st.session_state["reconciler_output"] = reconciler_output
                    workflow_results = run_reconciliation_workflow(reconciler_output)
                    st.session_state["workflow_results"] = workflow_results
                    st.success("Analysis complete!")
                    st.rerun()
                    
    with run_col2:
        if st.button("💡 Load Default Demo Datasets (Recommended for quick testing)", use_container_width=False):
            try:
                cmdb_demo = pd.read_csv("data/sample_input.csv")
                with open("data/sample_input.json", "r") as f:
                    live_demo_data = json.load(f)
                live_demo = pd.DataFrame(live_demo_data)
                
                st.session_state["uploaded_cmdb"] = cmdb_demo
                st.session_state["uploaded_live"] = live_demo
                
                reconciler_output = reconcile_inventories(cmdb_demo, live_demo)
                st.session_state["reconciler_output"] = reconciler_output
                workflow_results = run_reconciliation_workflow(reconciler_output)
                st.session_state["workflow_results"] = workflow_results
                
                st.success("Demo datasets loaded successfully!")
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"Failed to load demo datasets: {str(e)}.")

# =========================================================
# Result Screen (One Clean Screen with 4 Dashboard Tabs)
# =========================================================
else:
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Executive Summary",
        "🔍 Drift Inventory",
        "🧠 Agent Thought Console",
        "📥 Report Exporter"
    ])
    
    # Ingest data outputs
    reconciler_output = st.session_state["reconciler_output"]
    workflow_results = st.session_state["workflow_results"]
    summary = reconciler_output.get("summary", {})
    analysis = workflow_results.get("analysis", {})
    risk_data = workflow_results.get("risk_assessment", {})
    discrepancies = risk_data.get("assessed_discrepancies", [])
    validation_data = workflow_results.get("validation", {})
    safety_plan = validation_data.get("safety_audited_plan", [])
    
    health_score = analysis.get("infrastructure_health_score", 100)
    
    # ---------------------------------------------------------
    # TAB 1: EXECUTIVE SUMMARY
    # ---------------------------------------------------------
    with tab1:
        st.markdown("### 📊 Enterprise Health Metrics")
        
        # Row 1: KPI metrics cards
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Health Score</div><div class="metric-val">{health_score}%</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Missing Assets</div><div class="metric-val">{summary.get("missing", 0)}</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Untracked Assets</div><div class="metric-val">{summary.get("untracked", 0)}</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Config Drifts</div><div class="metric-val">{summary.get("config_drifts", 0)}</div></div>', unsafe_allow_html=True)
        with col5:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Naming Mismatches</div><div class="metric-val">{summary.get("naming_mismatches", 0)}</div></div>', unsafe_allow_html=True)
            
        # Row 2: Plots & Summary statement
        chart_col1, chart_col2 = st.columns([1, 1])
        with chart_col1:
            if discrepancies:
                df_disc = pd.DataFrame(discrepancies)
                fig_pie = px.pie(df_disc, names="classification", title="Anomalies Classification Group", hole=0.35)
                fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="#CBD5E1")
                st.plotly_chart(fig_pie, use_container_width=True)
        with chart_col2:
            st.markdown("#### 💡 AI Analysis Summary")
            st.write(analysis.get("analysis_summary", ""))
            
            st.markdown("#### 🔍 Key Findings")
            for finding in analysis.get("key_findings", []):
                st.markdown(f"- {finding}")
                
    # ---------------------------------------------------------
    # TAB 2: DRIFT INVENTORY
    # ---------------------------------------------------------
    with tab2:
        st.markdown("### 🔍 Filterable Configuration Drifts")
        
        # Grid filtering selectors
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            search_query = st.text_input("🔍 Search by Server Name", "")
        with col_f2:
            selected_sev = st.selectbox("Filter Severity Level", ["All", "High", "Medium", "Low"])
            
        # Filter items
        filtered_items = discrepancies
        if search_query:
            filtered_items = [d for d in filtered_items if search_query.lower() in d["target_asset"].lower()]
        if selected_sev != "All":
            filtered_items = [d for d in filtered_items if d["risk_level"] == selected_sev]
            
        # Render Table
        if filtered_items:
            table_html = """
            <table class="styled-table">
                <thead>
                    <tr>
                        <th>Server Name</th>
                        <th>Classification</th>
                        <th>Risk Severity</th>
                        <th>Risk Score</th>
                        <th>Focus Parameter</th>
                    </tr>
                </thead>
                <tbody>
            """
            for item in filtered_items:
                badge = "badge-healthy"
                if item["risk_level"] == "High":
                    badge = "badge-critical"
                elif item["risk_level"] == "Medium":
                    badge = "badge-warning"
                    
                focus = "Asset Presence"
                if item["anomaly_type"] == "config_drift":
                    focus = ", ".join([d["display"] for d in item.get("details", {}).get("drifts", {}).values()])
                elif item["anomaly_type"] == "naming_mismatch":
                    focus = "Server Hostname"

                table_html += f"""
                    <tr>
                        <td><strong>{item['target_asset']}</strong></td>
                        <td>{item['classification']}</td>
                        <td><span class="badge {badge}">{item['risk_level']}</span></td>
                        <td>{item['risk_score']} / 10.0</td>
                        <td>{focus}</td>
                    </tr>
                """
            table_html += "</tbody></table>"
            st.markdown(table_html, unsafe_allow_html=True)
            
            # Drilldown Details
            st.markdown("---")
            st.markdown("#### ⚙️ Comparative Configuration Drilldown")
            inspect_asset = st.selectbox("Select Server to Inspect", [d["target_asset"] for d in filtered_items])
            inspected_item = next(d for d in filtered_items if d["target_asset"] == inspect_asset)
            
            det_col1, det_col2 = st.columns(2)
            with det_col1:
                st.write("**Configuration Values**")
                details = inspected_item.get("details", {})
                if inspected_item["anomaly_type"] == "missing":
                    st.warning("Server is present in CMDB but completely missing in Live scanners.")
                    st.json(details.get("cmdb", details))
                elif inspected_item["anomaly_type"] == "untracked":
                    st.error("Server is running Live but is not registered in the CMDB.")
                    st.json(details.get("live", details))
                elif inspected_item["anomaly_type"] == "naming_mismatch":
                    st.write(f"CMDB Asset Name: `{details.get('cmdb', {}).get('name')}`")
                    st.write(f"Live Discovered Name: `{details.get('live', {}).get('name')}`")
                    st.write(f"Shared IP Address: `{inspected_item.get('ip_address')}`")
                elif inspected_item["anomaly_type"] == "config_drift":
                    for d in details.get("drifts", {}).values():
                        st.markdown(f"- **{d['display']}**: CMDB value = `{d['cmdb']}` | Live value = `{d['live']}`")
            with det_col2:
                st.write("**AI Risk Analysis & Impact**")
                st.write(f"**Vulnerability Risk Assessment**: {inspected_item.get('impact_statement')}")
                if inspected_item.get("compliance_implications"):
                    st.write("**Compliance Violations:**")
                    for cl in inspected_item["compliance_implications"]:
                        st.markdown(f"- ⚠️ {cl}")
        else:
            st.info("No matching discrepancies found.")

    # ---------------------------------------------------------
    # TAB 3: AGENT THOUGHT CONSOLE
    # ---------------------------------------------------------
    with tab3:
        st.markdown("### 🖥️ Multi-Agent Console Logs")
        st.markdown("Below is the timestamped execution output and thoughts log compile of all 6 agents.")
        
        # Display logs
        logs = workflow_results.get("execution_logs", [])
        log_text = "\n".join(logs)
        st.markdown(f'<div class="agent-terminal">{log_text}</div>', unsafe_allow_html=True)
        
        # JSON Tab selectors
        st.markdown("#### 📤 Structured Agent Output Files")
        selected_tab = st.selectbox("Select Agent Payload File:", ["Analysis Output", "Reconciliation Output", "Classification Output", "Risk Assessment Output", "Recommendation Output", "Validation Output"])
        
        if selected_tab == "Analysis Output":
            st.json(workflow_results.get("analysis", {}))
        elif selected_tab == "Reconciliation Output":
            st.json(workflow_results.get("reconciliation", {}))
        elif selected_tab == "Classification Output":
            st.json(workflow_results.get("classification", {}))
        elif selected_tab == "Risk Assessment Output":
            st.json(workflow_results.get("risk_assessment", {}))
        elif selected_tab == "Recommendation Output":
            st.json(workflow_results.get("recommendation", {}))
        elif selected_tab == "Validation Output":
            st.json(workflow_results.get("validation", {}))

    # ---------------------------------------------------------
    # TAB 4: REPORT EXPORTER
    # ---------------------------------------------------------
    with tab4:
        st.markdown("### 📥 Export Reports Hub")
        st.markdown("Save and export compliance audit reports to your local system.")
        
        csv_rows = []
        for item in safety_plan:
            match_risk = next((d for d in discrepancies if d["target_asset"] == item["target_asset"]), {})
            csv_rows.append({
                "Server Name": item["target_asset"],
                "Anomaly Group": match_risk.get("anomaly_type", ""),
                "Classification": item["classification"],
                "Risk Level": match_risk.get("risk_level", ""),
                "Risk Score": match_risk.get("risk_score", 0.0),
                "Safety Status": item["safety_status"],
                "Remediation Steps": "; ".join(item["remediation_steps"]),
                "Rollback Plan": item["rollback_plan"]
            })
        df_csv = pd.DataFrame(csv_rows)
        
        d_col1, d_col2, d_col3 = st.columns(3)
        with d_col1:
            st.markdown('<div class="glass-card" style="text-align: center; height: 200px;"><h4>📊 Tabular CSV</h4>', unsafe_allow_html=True)
            st.download_button("📥 Download CSV", df_csv.to_csv(index=False), "reconciliation_report.csv", "text/csv", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with d_col2:
            st.markdown('<div class="glass-card" style="text-align: center; height: 200px;"><h4>🧬 Programmatic JSON</h4>', unsafe_allow_html=True)
            st.download_button("📥 Download JSON", json.dumps(workflow_results, indent=2), "workflow_results.json", "application/json", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        with d_col3:
            st.markdown('<div class="glass-card" style="text-align: center; height: 200px;"><h4>📄 Executive PDF</h4>', unsafe_allow_html=True)
            
            pdf_placeholder = st.empty()
            pdf_path = "outputs/sample_output_report.pdf"
            
            # Ensure outputs folder exists
            os.makedirs("outputs", exist_ok=True)
            
            try:
                success = generate_pdf_report(workflow_results, pdf_path)
                if success and os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()
                    pdf_placeholder.download_button("📥 Download PDF", pdf_bytes, "infraguard_executive_report.pdf", "application/pdf", use_container_width=True)
                else:
                    pdf_placeholder.error("fpdf2 library missing. Fallback JSON exported.")
            except Exception as e:
                pdf_placeholder.error(f"PDF failed: {str(e)}")
            st.markdown('</div>', unsafe_allow_html=True)
            
        st.markdown("#### 📋 Executive Audit Preview")
        st.dataframe(df_csv[["Server Name", "Classification", "Risk Level", "Safety Status"]], use_container_width=True)
