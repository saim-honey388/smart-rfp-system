# Smart RFP System - Workflow Documentation

## 1. Overview
Smart RFP is an AI-powered Request for Proposal (RFP) management system designed to streamline the procurement process. It allows users to create RFPs, manage vendor proposals, and perform deep, AI-driven comparisons to make informed decisions.

## 2. Complete App Workflow

### A. Dashboard & RFP Management
- **Dashboard**: View a high-level summary of "Open", "Draft", and "Closed" RFPs.
- **Open RFPs**: Access a filtered list of all active RFPs currently accepting proposals.
- **Search & Filter**: Quickly locate specific RFPs by ID, title, or status.

### B. Creating an RFP
1.  Navigate to **"Create RFP"**.
2.  Fill in the details:
    - **Title & Overview**: Define the project scope.
    - **Budget & Timeline**: Set constraints.
    - **Requirements**: List specific deliverables (e.g., "Annual Contract", "24/7 Support").
3.  **Publish**: Once refined, publish the RFP to make it "Open" for proposals.

### C. Proposal Management (The "Proposals" Tab)
Navigate to a specific RFP and click the **"Proposals"** tab.
1.  **Submission**: Vendors submit PDF proposals (simulated via file upload or drag-and-drop).
2.  **AI Extraction**: The system automatically parses the PDF to extract:
    - Vendor Name
    - Price / Cost
    - Executive Summary
    - Experience credentials
3.  **Review & Action**:
    - **Accept**: Click the **Green Check mark** for proposals you want to proceed with.
    - **Reject**: Click the **Red X** for proposals that don't meet criteria.
    - **Note**: Only "Accepted" proposals will be available for detailed comparison.

### D. Intelligent Comparison (New Feature)
Navigate to the **"Comparisons"** page (via "Compare All" or the sidebar).

#### 1. Dynamic Dimension Selection
The comparison engine is split into two powerful sections:
-   **General Dimensions**: Standard metrics applicable to all RFPs (e.g., *Cost*, *Timeline*, *Experience*).
-   **RFP Requirement Dimensions**: AI-generated dimensions extracted specifically from *your* RFP's unique requirements (e.g., *preventive maintenance*, *warranty*, *compliance*).

#### 2. Comparison Logic
-   **Strict Filtering**: The system *only* compares vendors you have explicitly **Accepted**. Rejected or pending proposals are excluded to keep the view clean.
-   **Smart Scoring**: Vendors are scored (0-100) on each dimension based on their proposal content vs. your requirements.
-   **Selection Limit**: You can select up to **5 distinct dimensions** to generate a focused, readable report.

#### 3. The Report
Click **"Generate Report"** to view:
-   **Radar Chart**: Visualizes how vendors balance against each other across all selected attributes.
-   **Bar Chart**: Compares "Overall Score" vs "Price Score" to highlight value for money.
-   **Detailed Table**: A side-by-side breakdown of every selected dimension for each vendor (e.g., grading "Emergency Response" as *Top Tier*, *Standard*, or *Low*).

### E. Decision & Closure
1.  Use the comparison insights to select a winning vendor.
2.  Navigate back to the RFP details.
3.  **Close RFP**: Mark the RFP as closed to stop accepting new submissions.
