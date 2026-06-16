import os
import time
import json
from dotenv import load_dotenv
import streamlit as st

# Load environment variables
load_dotenv()

# =========================================================
# Configuration Settings
# =========================================================
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "demo").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_API_BASE = os.getenv("OLLAMA_API_BASE", "http://localhost:11434/api")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

if LLM_PROVIDER == "openai" and not OPENAI_API_KEY:
    LLM_PROVIDER = "demo"
elif LLM_PROVIDER == "ollama" and not OLLAMA_API_BASE:
    LLM_PROVIDER = "demo"

# =========================================================
# Premium CSS Injection Style
# =========================================================
def inject_premium_style():
    css = """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    
    <style>
        .stApp {
            background-color: #0B0F19;
            color: #E2E8F0;
            font-family: 'Inter', sans-serif;
        }
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Outfit', sans-serif !important;
            font-weight: 600 !important;
            color: #F8FAFC !important;
        }
        [data-testid="stSidebar"] {
            background-color: #0F172A !important;
            border-right: 1px solid #1E293B !important;
        }
        .glass-card {
            background: rgba(30, 41, 59, 0.45);
            border: 1px solid rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(8px);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        .metric-card {
            background: rgba(30, 41, 59, 0.45);
            border: 1px solid rgba(255, 255, 255, 0.08);
            backdrop-filter: blur(8px);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            height: 125px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .metric-label {
            font-size: 0.85rem;
            color: #94A3B8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
            font-weight: 500;
        }
        .metric-val {
            font-size: 2.25rem;
            font-family: 'Outfit', sans-serif;
            font-weight: 700;
            background: linear-gradient(135deg, #38BDF8, #818CF8);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.025em;
        }
        .badge-critical {
            background-color: rgba(239, 68, 68, 0.15);
            color: #F87171;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }
        .badge-warning {
            background-color: rgba(245, 158, 11, 0.15);
            color: #FBBF24;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }
        .badge-healthy {
            background-color: rgba(16, 185, 129, 0.15);
            color: #34D399;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .agent-terminal {
            background-color: #020617;
            border: 1px solid #1E293B;
            border-radius: 8px;
            padding: 16px;
            font-family: 'Courier New', Courier, monospace;
            color: #10B981;
            font-size: 0.85rem;
            max-height: 400px;
            overflow-y: auto;
            line-height: 1.5;
            margin-bottom: 20px;
        }
        .stButton>button {
            background: linear-gradient(135deg, #2563EB, #4F46E5);
            color: white;
            border: none;
            border-radius: 6px;
            font-weight: 500;
            padding: 8px 16px;
            transition: all 0.2s ease-in-out;
        }
        .stButton>button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
            background: linear-gradient(135deg, #3B82F6, #6366F1);
        }
        .styled-table {
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-size: 0.9rem;
        }
        .styled-table th {
            background-color: #1E293B;
            color: #F8FAFC;
            text-align: left;
            padding: 12px;
            font-weight: 600;
            border-bottom: 2px solid #334155;
        }
        .styled-table td {
            padding: 12px;
            border-bottom: 1px solid #1E293B;
            color: #CBD5E1;
        }
        .styled-table tr:hover {
            background-color: rgba(30, 41, 59, 0.2);
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# =========================================================
# Styled PDF Executive Summary Exporter
# =========================================================
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

if FPDF_AVAILABLE:
    class ReconciliationPDF(FPDF):
        def header(self):
            self.set_fill_color(15, 23, 42)
            self.rect(0, 0, 210, 40, 'F')
            self.set_y(10)
            self.set_text_color(255, 255, 255)
            self.set_font('Helvetica', 'B', 15)
            self.cell(0, 10, 'INFRAGUARD ENTERPRISE RECONCILIATION REPORT', ln=True, align='C')
            self.set_font('Helvetica', 'I', 9)
            self.set_text_color(148, 163, 184)
            self.cell(0, 5, f'Generated: {time.strftime("%Y-%m-%d %H:%M:%S")} | Configuration Audit Summary', ln=True, align='C')
            self.ln(15)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(156, 163, 175)
            self.line(10, self.get_y(), 200, self.get_y())
            self.cell(0, 10, f'Confidential | Page {self.page_no()}/{{nb}}', align='L')
            self.cell(0, 10, 'Powered by InfraGuard Multi-Agent AI Workflow', align='R')

        def chapter_title(self, label):
            self.set_font('Helvetica', 'B', 11)
            self.set_fill_color(241, 245, 249)
            self.set_text_color(15, 23, 42)
            self.cell(0, 8, f'  {label}', ln=True, fill=True)
            self.ln(4)

        def chapter_body(self, text):
            self.set_font('Helvetica', '', 9.5)
            self.set_text_color(51, 65, 85)
            self.multi_cell(0, 5, text)
            self.ln(5)

def generate_pdf_report(workflow_results: dict, output_path: str) -> bool:
    if not FPDF_AVAILABLE:
        with open(output_path + ".json", "w") as f:
            json.dump(workflow_results, f, indent=2)
        return False

    pdf = ReconciliationPDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.ln(10)

    # 1. Executive Summary
    pdf.chapter_title("1. EXECUTIVE HEALTH SUMMARY")
    analysis_data = workflow_results.get("analysis", {})
    health_score = analysis_data.get("infrastructure_health_score", 100)
    summary_text = analysis_data.get("analysis_summary", "")
    
    pdf.set_fill_color(254, 242, 242) if health_score < 70 else pdf.set_fill_color(240, 253, 250)
    pdf.set_text_color(153, 27, 27) if health_score < 70 else pdf.set_text_color(15, 118, 110)
    pdf.set_font('Helvetica', 'B', 10.5)
    pdf.cell(0, 10, f'    INFRASTRUCTURE COMPLIANCE HEALTH SCORE: {health_score}/100', ln=True, fill=True)
    pdf.ln(3)

    pdf.chapter_body(summary_text)
    
    pdf.set_font('Helvetica', 'B', 9.5)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, "Key Assessment Findings:", ln=True)
    pdf.ln(2)
    for finding in analysis_data.get("key_findings", []):
        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(5)
        pdf.multi_cell(0, 5, f'- {finding}')
        pdf.ln(1)
    
    pdf.ln(5)

    # 2. Risk Matrix
    pdf.chapter_title("2. CLASSIFIED DISCREPANCIES & RISK MATRIX")
    risk_data = workflow_results.get("risk_assessment", {})
    discrepancies = risk_data.get("assessed_discrepancies", [])
    
    if not discrepancies:
        pdf.chapter_body("No discrepancies were detected during reconciliation.")
    else:
        pdf.set_font('Helvetica', 'B', 8.5)
        pdf.set_fill_color(15, 23, 42)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(30, 7, " Asset Name", fill=True)
        pdf.cell(40, 7, " Classification", fill=True)
        pdf.cell(20, 7, " Severity", fill=True, align='C')
        pdf.cell(15, 7, " Score", fill=True, align='C')
        pdf.cell(85, 7, " Business / Security Risk Impact", fill=True)
        pdf.ln(7)

        pdf.set_font('Helvetica', '', 8)
        row_count = 0
        for item in discrepancies:
            bg_color = (255, 255, 255) if row_count % 2 == 0 else (248, 250, 252)
            pdf.set_fill_color(*bg_color)
            pdf.set_text_color(51, 65, 85)
            
            risk_level = item.get("risk_level", "Low")
            r_color = (239, 68, 68) if risk_level == "High" else (245, 158, 11) if risk_level == "Medium" else (59, 130, 246)

            pdf.cell(30, 8, f" {item.get('target_asset')[:16]}", fill=True)
            pdf.cell(40, 8, f" {item.get('classification')[:22]}", fill=True)
            
            pdf.set_text_color(*r_color)
            pdf.set_font('Helvetica', 'B', 8)
            pdf.cell(20, 8, f"{risk_level}", fill=True, align='C')
            
            pdf.set_text_color(51, 65, 85)
            pdf.set_font('Helvetica', '', 8)
            pdf.cell(15, 8, f"{item.get('risk_score', 0.0)}", fill=True, align='C')
            pdf.cell(85, 8, f" {item.get('impact_statement')[:50]}...", fill=True)
            pdf.ln(8)
            
            row_count += 1
        pdf.ln(5)

    # 3. Action Plan
    pdf.chapter_title("3. SAFETY-AUDITED REMEDIATION ACTION PLAN")
    validation_data = workflow_results.get("validation", {})
    safety_plan = validation_data.get("safety_audited_plan", [])
    
    pdf.chapter_body(validation_data.get("overall_validation_summary", ""))
    
    for item in safety_plan:
        asset = item.get("target_asset")
        classification = item.get("classification")
        safety_status = item.get("safety_status", "Approved")
        
        pdf.set_font('Helvetica', 'B', 9.5)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(0, 6, f"Remediation Action: {asset} ({classification})", ln=True)
        
        if safety_status == "Approved":
            s_fill = (240, 253, 250)
            s_text = (13, 148, 136)
        elif safety_status == "Approved with Caveats":
            s_fill = (255, 251, 235)
            s_text = (217, 119, 6)
        else:
            s_fill = (254, 242, 242)
            s_text = (220, 38, 38)
            
        pdf.set_fill_color(*s_fill)
        pdf.set_text_color(*s_text)
        pdf.set_font('Helvetica', 'B', 8)
        pdf.cell(45, 5, f" SAFETY STATUS: {safety_status.upper()} ", ln=True, fill=True)
        pdf.ln(2)
        
        pdf.set_font('Helvetica', '', 8.5)
        pdf.set_text_color(71, 85, 105)
        
        # Remarks
        pdf.set_font('Helvetica', 'B', 8.5)
        pdf.set_text_color(51, 65, 85)
        pdf.write(5, "Audit: ")
        pdf.set_font('Helvetica', '', 8.5)
        pdf.set_text_color(71, 85, 105)
        pdf.write(5, item.get("validation_remarks", "") + "\n")
        
        # Steps
        pdf.set_font('Helvetica', 'B', 8.5)
        pdf.set_text_color(51, 65, 85)
        pdf.write(5, "Steps: ")
        pdf.set_font('Helvetica', '', 8.5)
        pdf.set_text_color(71, 85, 105)
        pdf.write(5, " -> ".join(item.get("remediation_steps", [])) + "\n")
        
        # Rollback
        pdf.set_font('Helvetica', 'B', 8.5)
        pdf.set_text_color(153, 27, 27)
        pdf.write(5, "Rollback: ")
        pdf.set_font('Helvetica', '', 8.5)
        pdf.set_text_color(71, 85, 105)
        pdf.write(5, item.get("rollback_plan", "") + "\n")
        
        script_content = item.get("script_content", "")
        if script_content:
            pdf.ln(1)
            pdf.set_x(10) # Reset to left margin
            pdf.set_fill_color(248, 250, 252)
            pdf.set_font('Courier', '', 7)
            pdf.set_text_color(15, 23, 42)
            pdf.multi_cell(0, 4, script_content, border=1, fill=True)
            
        pdf.ln(3)
        pdf.set_x(10) # Reset to left margin for next loop

    pdf.output(output_path)
    return True
