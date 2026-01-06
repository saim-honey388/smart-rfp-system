import React, { createContext, useContext, useState, useEffect } from 'react';

const RFPContext = createContext();
const API_BASE = 'http://localhost:8000/api';

export function useRFP() {
    return useContext(RFPContext);
}

export function RFPProvider({ children }) {
    const [rfps, setRfps] = useState([]);
    const [proposals, setProposals] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Fetch RFPs from backend on mount
    useEffect(() => {
        fetchRFPs();
    }, []);

    // Fetch proposals from backend on mount
    useEffect(() => {
        fetchProposals();
    }, []);

    const fetchRFPs = async () => {
        try {
            const response = await fetch(`${API_BASE}/rfps`);
            if (!response.ok) throw new Error('Failed to fetch RFPs');

            const data = await response.json();

            // Transform backend data to frontend format
            const transformedRFPs = data.map(rfp => ({
                id: rfp.id,
                title: rfp.title,
                due: rfp.deadline || 'No deadline',
                proposals: 0, // Will be calculated from proposals
                status: rfp.status,
                budget: rfp.budget ? `$${rfp.budget.toLocaleString()}` : 'N/A',
                scope: rfp.description || '',
                requirements: (rfp.requirements || []).map(r => typeof r === 'object' ? r.text : r),
                created_at: rfp.created_at // Added for time filtering
            }));

            setRfps(transformedRFPs);
        } catch (err) {
            console.error('Error fetching RFPs:', err);
            setError(err.message);
            // Fallback to empty array instead of mock data
            setRfps([]);
        } finally {
            setLoading(false);
        }
    };

    const fetchProposals = async () => {
        try {
            const response = await fetch(`${API_BASE}/proposals`);
            if (!response.ok) throw new Error('Failed to fetch proposals');

            const data = await response.json();
            console.log('✅ Fetched proposals from backend:', data);

            // Transform backend data to frontend format
            const transformedProposals = data.map(p => ({
                id: p.id,
                rfpId: p.rfp_id,
                file: `${p.contractor}.pdf`, // We don't store filename in backend
                vendor: p.contractor || 'Unknown Vendor',
                price: p.price ? `$${p.price.toLocaleString()}` : 'Not specified',
                summary: p.summary || 'No summary available',
                status: p.status === 'submitted' ? 'Pending' : p.status.charAt(0).toUpperCase() + p.status.slice(1),
                // Extended fields
                experience: p.experience,
                methodology: p.methodology,
                warranties: p.warranties,
                timeline_details: p.timeline_details,
                extracted_text: p.extracted_text,
                contractor_email: p.contractor_email,
                start_date: p.start_date,
                currency: p.currency,
                // Form data for comparison matrix
                proposal_form_data: p.proposal_form_data || [],
                dimensions: p.dimensions || {}
            }));


            setProposals(transformedProposals);

            // Update RFP proposal counts
            setRfps(prevRfps => prevRfps.map(rfp => ({
                ...rfp,
                proposals: transformedProposals.filter(p => p.rfpId === rfp.id).length
            })));

        } catch (err) {
            console.error('Error fetching proposals:', err);
            setError(err.message);
            setProposals([]);
        }
    };


    // Actions
    const addRFP = async (newRfp) => {
        try {
            // Handle budget parsing with 'k' support (e.g., "20k" -> 20000)
            let rawBudget = newRfp.budget || '';
            const isK = rawBudget.toLowerCase().includes('k');
            let dbBudget = parseInt(rawBudget.replace(/[^0-9]/g, '')); // Removed || 5000
            if (isNaN(dbBudget)) dbBudget = null; // Send null if optional/invalid
            if (dbBudget !== null && isK && dbBudget < 1000) dbBudget *= 1000;

            // Handle date parsing: 'TBD' or empty should be null
            let deadline = newRfp.due;
            if (!deadline || deadline === "TBD") {
                deadline = null;
            }

            const response = await fetch(`${API_BASE}/rfps`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: newRfp.title,
                    description: newRfp.scope || '',
                    requirements: (newRfp.requirements || []).map((req, i) =>
                        typeof req === 'string'
                            ? { id: `req-${Date.now()}-${i}`, text: req }
                            : req
                    ),
                    budget: dbBudget,
                    currency: 'USD',
                    deadline: deadline,
                    status: newRfp.status || 'open',
                    // Include proposal form data for vendor extraction
                    proposal_form_schema: newRfp.proposal_form_schema || {},
                    proposal_form_rows: newRfp.proposal_form_rows || []
                })
            });


            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ detail: response.statusText }));
                throw new Error(errorData.detail || 'Failed to create RFP');
            }

            // Refresh RFP list from backend
            await fetchRFPs();
            return true;
        } catch (err) {
            console.error('Error creating RFP:', err);
            // Re-throw so the component knows it failed
            throw err;
        }
    };

    const updateRFP = async (id, updates) => {
        // For now, just update locally (backend doesn't have update endpoint yet)
        setRfps(prev => prev.map(r => r.id === id ? { ...r, ...updates } : r));
    };

    // ✅ REAL PDF EXTRACTION - Calls Backend API
    const addProposal = async (rfpId, file) => {
        const tempId = `temp-${Date.now()}`;

        console.log('🚀 Uploading proposal to REAL backend API...', { rfpId, filename: file.name });

        // 1. Show immediate "Processing" feedback
        setProposals(prev => [...prev, {
            id: tempId,
            rfpId,
            file: file.name,
            vendor: 'AI Extracting from PDF...',
            status: 'Processing',
            price: '...',
            summary: 'Reading document with AI...'
        }]);

        // 2. Increment count optimistically
        setRfps(prev => prev.map(r => r.id === rfpId ? { ...r, proposals: (r.proposals || 0) + 1 } : r));

        try {
            // 3. Call REAL BACKEND API (/api/proposals/upload)
            // Backend uses: PyPDF2 → extract_text() → extract_details_with_ai()
            const formData = new FormData();
            formData.append('file', file);
            formData.append('rfp_id', rfpId);
            formData.append('contractor', 'AI will extract this');

            const response = await fetch(`${API_BASE}/proposals/upload`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Backend error: ${response.status} - ${errorText}`);
            }

            const extractedData = await response.json();
            console.log('✅ Backend AI Extraction Success:', extractedData);

            // 4. Re-fetch ALL proposals from backend to get complete data
            // This ensures we get ALL extracted fields including experience, methodology, etc.
            await fetchProposals();

        } catch (error) {
            console.error('❌ Proposal upload/extraction error:', error);

            // Show error state
            setProposals(prev => prev.map(p => p.id === tempId ? {
                ...p,
                vendor: 'Extraction Failed',
                status: 'Error',
                price: 'N/A',
                summary: `Error: ${error.message}. Check backend logs.`
            } : p));

            alert(`Failed to upload proposal: ${error.message}\n\nMake sure the backend is running at http://localhost:8000`);
        }
    };

    const updateProposalStatus = async (id, newStatus) => {
        // Get the proposal
        const proposal = proposals.find(p => p.id === id);
        if (!proposal) return;

        // Status locking logic
        if (proposal.status === 'Accepted' && newStatus === 'Rejected') {
            alert("❌ Cannot reject an accepted proposal. Accepted proposals are locked.");
            return;
        }
        if (proposal.status === 'Rejected' && newStatus === 'Accepted') {
            alert("❌ Cannot accept a rejected proposal. Rejected proposals are locked.");
            return;
        }

        try {
            // Map frontend status to backend status
            const backendStatus = newStatus.toLowerCase();
            const endpoint = backendStatus === 'accepted' ? 'approve' : 'reject';

            const response = await fetch(`${API_BASE}/proposals/${id}/${endpoint}`, {
                method: 'POST'
            });

            if (!response.ok) throw new Error('Failed to update proposal status');

            // Update local state
            setProposals(prev => prev.map(p =>
                p.id === id ? { ...p, status: newStatus } : p
            ));

        } catch (err) {
            console.error('Error updating proposal status:', err);
            alert(`Failed to update status: ${err.message}`);
        }
    };

    // ✅ NEW: Upload RFP PDF for Extraction
    const uploadRFPFile = async (file) => {
        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch(`${API_BASE}/rfps/upload`, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Upload failed: ${response.status} - ${errorText}`);
            }

            return await response.json();
        } catch (err) {
            console.error('RFP Upload Error:', err);
            throw err;
        }
    };

    const chatWithRFPConsultant = async (message, currentState, history) => {
        try {
            const response = await fetch(`${API_BASE}/chat/rfp`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message,
                    current_state: currentState,
                    conversation_history: history
                })
            });

            if (!response.ok) throw new Error('AI Chat failed');
            return await response.json();
        } catch (err) {
            console.error('AI Chat Error:', err);
            throw err;
        }
    };


    const getRFP = (id) => rfps.find(r => r.id === id);
    const getProposalsForRFP = (rfpId) => proposals.filter(p => p.rfpId === rfpId);

    return (
        <RFPContext.Provider value={{
            rfps,
            proposals,
            loading,
            error,
            addRFP,
            updateRFP,
            getRFP,
            addProposal,
            updateProposalStatus,
            getProposalsForRFP,
            fetchRFPs,
            fetchProposals,
            chatWithRFPConsultant,
            uploadRFPFile
        }}>
            {children}
        </RFPContext.Provider>
    );
}
