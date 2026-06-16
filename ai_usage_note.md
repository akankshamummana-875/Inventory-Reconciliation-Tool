# AI Usage Note

This document summarizes the contributions of AI during the development of the **InfraGuard Inventory Reconciliation Tool** as part of the AI Prototype Challenge requirements.

---

## 1. What AI Helped With
* **Multi-Agent Orchestration Blueprint**: Designing the sequential flow of context from the Analysis Agent to the Validation Agent.
* **Complex UI CSS Injections**: Formulating glassmorphism layouts and color badges to build a premium enterprise dark dashboard in Streamlit.
* **Advanced Reconciler Algorithms**: Recommending IP cross-referencing alongside SequenceMatcher similarity scores to handle naming mismatches and drifts correctly.
* **Testing Asserts**: Generating unit tests for the reconciler and agent pipelines with complex datasets.
* **ReportLab / FPDF Code**: Translating multi-agent dictionary outputs into clean layout formats for print-ready PDFs.

---

## 2. What AI Got Wrong & How It Was Resolved
* **Streamlit Page Routing**: Initially suggested using Streamlit's file-based multi-page directory routing (`pages/` folder). This was corrected to use standard Python modules inside a main `app.py` script routing via session state. This avoids folder-scanning discrepancies on server deployments (like Streamlit Cloud or Render) and enables clean state sharing.
* **Similarity Thresholds**: Recommended an overly simple string comparison that flagged similar systems (like `prod-db-postgres` and `prod-db-pg-01`) as separate "missing" and "untracked" assets. The logic was adjusted to prioritize **IP-address matching** as a hard check first, then apply `SequenceMatcher` for remaining elements.
* **Package Import Failures**: Proposed using `reportlab` canvas elements directly without checking package availability, which could cause app crashes on environments without binary libraries. The design was refactored to support `fpdf2` (which is lightweight and has zero C-extensions) and implement a graceful fallback to JSON saving if imports fail.

---

## 3. Best Prompts Used during Development
* **System Prompt for Agent Sequential Chain**:
  ```text
  You are the Validation Agent in a multi-agent inventory reconciliation system.
  Your job is to audit the proposed remediation plan and security ratings. You must:
  1. Run safety checks (e.g., flag any drop/delete/destroy/decommission operations targeting Production systems).
  2. Assign a safety_status ('Approved', 'Approved with Caveats', 'Needs Manual Verification').
  3. Append detailed validation remarks and a solid Rollback Plan for each remediation item.
  4. Provide an overall approved status and a validation summary.
  Return a structured JSON output.
  ```
* **CSS Ingestion for Custom UI**:
  ```text
  Provide a CSS block that overrides Streamlit's dark-mode container margins, renders metrics values using linear gradients, and creates dark glassmorphism card containers suitable for a DevOps dashboard.
  ```
