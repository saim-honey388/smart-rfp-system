# Smart RFP System - Complete Workflow Documentary

Welcome to the **Smart RFP System**! This document serves as a comprehensive guide for new users, walking you through the entire lifecycle of the application—from installation to making data-driven procurement decisions.

---

## 🚀 1. Getting Started

### Prerequisites
-   **Node.js** (v18+)
-   **Python** (v3.10+)
-   **Poetry** (optional, standard `pip` works)

### Installation & Launch
Open your terminal in the project root and run the following commands to start both the Frontend and Backend.

#### Backend (API)
```bash
# Navigate to the backend directory (or root if configured)
# Assuming a virtual environment is active

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI server
python -m apps.api.main
# Server will run at: http://localhost:8000
```

#### Frontend (Client)
```bash
# Navigate to the client directory
cd apps/client

# Install dependencies
npm install

# Start the development server
npm run dev
# App will run at: http://localhost:5173
```

---

## 📖 2. User Journey & Demo Walkthrough

### Step 1: Dashboard Overview
Upon logging in, you are greeted by the **Dashboard**.
-   **Key Metrics**: See the count of Open RFPs, Active Drafts, and Saved Comparisons.
-   **Quick Actions**: Jump straight to "Create RFP" or "View Proposals".
-   **Recent Activity**: A timeline of your recent actions (e.g., "Created HVAC RFP", "Accepted Proposal from Vendor X").

### Step 2: Creating a Request for Proposal (RFP)
1.  Click **"Create RFP"** in the sidebar.
2.  **General Idea**: Enter a title (e.g., "Office Security Upgrade") and a brief description.
3.  **Requirements Generation**:
    -   The system uses AI to suggest standard requirements based on your title.
    -   You can manually add, edit, or remove specific requirements (e.g., "Must include 24/7 monitoring").
4.  **Publish**: Click **Publish** to make the RFP live. It is now ready to receive proposals.

### Step 3: Managing Proposals
Vendors submit PDF proposals in response to your RFP.
1.  Navigate to your **Active RFP**.
2.  Click the **"Proposals"** tab.
3.  **Upload/Simulate**: Drag and drop PDF files to simulate a vendor submission.
4.  **AI Analysis**: The system instantly reads the PDF and extracts:
    -   **Vendor Name**
    -   **Total Cost**
    -   **Experience Highlights**
    -   **Executive Summary**
5.  **Review**:
    -   Click on a proposal card to view details.
    -   **Accept (✓)**: Mark viable proposals for further comparison.
    -   **Reject (✗)**: Discard proposals that don't meet basic criteria.

### Step 4: Intelligent Comparison
This is the core feature of the Smart RFP System.
1.  Go to the **"Comparisons"** page.
2.  **Select an RFP**: Choose the project you are evaluating (only RFPs with accepted proposals appear here).
3.  **Choose Dimensions**:
    -   **General**: Price, Timeline, Experience.
    -   **Custom (AI)**: Select specific criteria extracted from *your* requirements (e.g., "Warranty Period", "Compliance Level").
    -   *Note: Select up to 5 dimensions for the best view.*
4.  **Generate Report**: Click the button to build the comparison.

### Step 5: Analyzing the Report
The system generates a visual report including:
-   **Radar Chart**: A holistic view of how vendors stack up against each other.
-   **Price vs. Performance**: A bar chart highlighting value for money.
-   **Detailed Scoring Table**: A row-by-row comparison of how each vendor scored (0-100) on your selected dimensions, with AI-generated reasoning for every score.

### Step 6: Final Decision
1.  Based on the report, decide on the winning vendor.
2.  Select the **Winner** in the system.
3.  **Close RFP**: Mark the project as complete in the dashboard.

---

## 🛠 Feature Highlights
-   **AI-Driven Extraction**: No manual data entry from PDF proposals.
-   **Dynamic Scoring**: Scores are not random; they are based on how well the proposal text matches your specific requirements.
-   **Clean UI**: Dark/Light mode support with a modern, responsive interface.

---

*This workflow document was generated to assist new users in navigating the Smart RFP System v2.2.*
