import React, { useState, useMemo, useEffect } from 'react';
import ReactApexChart from 'react-apexcharts';
import { useRFP } from '../context/RFPContext';
import { useSearchParams } from 'react-router-dom';
import { X } from 'lucide-react';

export default function Comparisons() {
    const { proposals, rfps } = useRFP();
    const [searchParams, setSearchParams] = useSearchParams(); // Fixed: Destructuring setter
    const rfpId = searchParams.get('rfp');

    // UI State
    const [selectedDimensions, setSelectedDimensions] = useState([]);

    const [showReport, setShowReport] = useState(false);
    const [selectedProposal, setSelectedProposal] = useState(null);

    // Get the specific RFP and its proposals
    // State for filtering
    const [showAcceptedOnly, setShowAcceptedOnly] = useState(false);

    // Get the specific RFP and its proposals
    const activeRFP = rfps.find(r => String(r.id) === String(rfpId)) || rfps.find(r => (r.proposals || 0) > 0) || rfps[0];
    const activeProposals = proposals.filter(p => {
        const matchRFP = String(p.rfpId) === String(activeRFP?.id);
        const matchStatus = showAcceptedOnly ? p.status === 'Accepted' : (p.status === 'Submitted' || p.status === 'Processing' || p.status === 'Accepted');
        // Note: Usually we want to exclude 'Rejected' unless specifically asked. 
        // But for 'Compare All', we usually compare active candidates. 
        // If showAcceptedOnly is true -> Accepted.
        // If false -> All non-rejected (Submitted + Accepted + Processing). 
        // User said "Pending/Rejected will be hidden from this final decision view".
        // I'll stick to: True -> Accepted. False -> Submitted + Accepted + Processing. (Exclude Rejected).

        if (!matchRFP) return false;
        if (showAcceptedOnly) return p.status === 'Accepted';
        return p.status !== 'Rejected';
    });

    console.log('DEBUG: Comparisons render cycle', {
        rfpId,
        rfpsCount: rfps.length,
        activeRFP: activeRFP?.id,
        activeProposalsCount: activeProposals.length
    });

    // State for Saved Comparisons List
    const [savedComparisons, setSavedComparisons] = useState([]);
    const [loadingSaved, setLoadingSaved] = useState(true);

    useEffect(() => {
        if (!rfpId) {
            setLoadingSaved(true);
            fetch('http://localhost:8000/api/comparisons')
                .then(res => res.json())
                .then(data => setSavedComparisons(data))
                .catch(err => console.error("Failed to fetch saved comparisons:", err))
                .finally(() => setLoadingSaved(false));
        }
    }, [rfpId]);

    // State to track if cache is stale
    const [cacheStale, setCacheStale] = useState(false);

    // Ref to prevent loading saved comparison multiple times
    const hasLoadedSavedComparison = React.useRef(false);

    // Load saved dimensions AND cached scores on mount (once only)
    useEffect(() => {
        if (rfpId && activeProposals.length > 0 && !hasLoadedSavedComparison.current) {
            hasLoadedSavedComparison.current = true; // Prevent future runs

            // Check for saved comparison on backend
            fetch(`http://localhost:8000/api/comparisons/${rfpId}`)
                .then(res => {
                    if (res.ok) return res.json();
                    throw new Error('No saved comparison');
                })
                .then(data => {
                    console.log("Loaded saved comparison:", data);
                    if (data.dimensions && data.dimensions.length > 0) {
                        // Deduplicate and limit to max 5
                        const uniqueDimensions = [...new Set(data.dimensions)].slice(0, 5);
                        console.log("Setting dimensions (deduplicated):", uniqueDimensions);
                        setSelectedDimensions(uniqueDimensions);

                        // Check if proposals have changed
                        const currentProposalIds = activeProposals.map(p => p.id).sort();
                        const cachedProposalIds = (data.proposal_ids || []).sort();
                        const proposalsChanged = JSON.stringify(currentProposalIds) !== JSON.stringify(cachedProposalIds);

                        if (proposalsChanged) {
                            console.log("⚠️ Proposals changed! Cache is stale, will re-run AI.");
                            setCacheStale(true);
                            setShowReport(false); // Don't show stale report
                        } else if (data.scores_cache && data.scores_cache.proposals) {
                            // Proposals match - use cached scores
                            console.log("✓ Using cached AI scores (proposals unchanged)");
                            setAiScores(data.scores_cache);
                            setCacheStale(false);
                            setShowReport(true);
                        } else {
                            // No cached scores available
                            setCacheStale(true);
                        }
                    }
                })
                .catch(() => {
                    console.log("No saved comparison found for this RFP.");
                });
        }
    }, [rfpId, activeProposals]);

    // =======================
    // EXTRACT DIMENSIONS
    // =======================
    const [aiDimensions, setAiDimensions] = useState([]);
    const [loadingDimensions, setLoadingDimensions] = useState(false);

    useEffect(() => {
        if (activeRFP?.id) {
            setLoadingDimensions(true);
            fetch(`http://localhost:8000/api/analysis/rfp/${activeRFP.id}/dimensions`, {
                method: 'POST'
            })
                .then(res => res.json())
                .then(data => {
                    setAiDimensions(data.dimensions || []);
                })
                .catch(err => console.error("Failed to fetch dimensions:", err))
                .finally(() => setLoadingDimensions(false));
        }
    }, [activeRFP?.id]);

    const availableDimensions = useMemo(() => {
        return aiDimensions.length > 0 ? aiDimensions : [
            { id: 'experience', name: 'Experience', type: 'general', keywords: ['experience', 'years', 'projects', 'portfolio', 'completed', 'similar'] },
            { id: 'cost', name: 'Cost', type: 'general' },
            { id: 'materials_warranty', name: 'Materials/Warranty', type: 'general', keywords: ['materials', 'warranty', 'guarantee', 'quality', 'grade', 'specification'] },
            { id: 'schedule', name: 'Schedule', type: 'general', keywords: ['schedule', 'timeline', 'start', 'completion', 'days', 'weeks', 'months'] },
            { id: 'safety', name: 'Safety', type: 'general', keywords: ['safety', 'osha', 'compliance', 'training', 'incident', 'protection'] },
            { id: 'responsiveness', name: 'Responsiveness', type: 'general', keywords: ['responsive', 'communication', 'availability', 'support', 'contact', 'response'] }
        ];
    }, [aiDimensions]);


    // =======================
    // AI-POWERED SCORES (from backend)
    // =======================
    const [aiScores, setAiScores] = useState(null);
    const [loadingScores, setLoadingScores] = useState(false);

    // Fallback: Simple frontend scores when AI not available
    const dimensionsData = useMemo(() => {
        // If we have AI scores, use them
        if (aiScores?.proposals) {
            return aiScores.proposals.map(p => ({
                id: p.id,
                vendor: p.vendor,
                price: activeProposals.find(ap => ap.id === p.id)?.price || 'N/A',
                summary: activeProposals.find(ap => ap.id === p.id)?.summary || 'No summary',
                scores: Object.fromEntries(
                    Object.entries(p.scores).map(([dimId, scoreData]) => [dimId, scoreData.score])
                ),
                scoreDetails: p.scores, // Keep full details with labels and reasoning
                overallScore: p.overall_score
            }));
        }

        // Fallback: Local calculation if AI not available
        if (availableDimensions.length === 0 || activeProposals.length === 0) return [];

        const prices = activeProposals.map(prop => {
            const safePrice = String(prop.price || '0');
            const raw = parseFloat(safePrice.replace(/[^0-9.]/g, '')) || 0;
            return safePrice.toLowerCase().includes('k') ? raw * 1000 : raw;
        });
        const maxPrice = Math.max(0, ...prices) || 100;

        return activeProposals.map(p => {
            const safePrice = String(p.price || '0');
            const priceRaw = parseFloat(safePrice.replace(/[^0-9.]/g, '')) || 0;
            const priceAmount = safePrice.toLowerCase().includes('k') ? priceRaw * 1000 : priceRaw;

            const scores = {};
            availableDimensions.forEach(dim => {
                if (dim.id === 'cost') {
                    scores[dim.id] = maxPrice > 0 ? Math.round(((maxPrice - priceAmount) / maxPrice) * 100) : 50;
                    scores[dim.id] = Math.max(0, Math.min(100, scores[dim.id]));
                } else {
                    scores[dim.id] = 50; // Default when AI not available
                }
            });

            const selectedScores = selectedDimensions.map(dimId => scores[dimId] || 50);
            const overallScore = selectedScores.length > 0
                ? Math.round(selectedScores.reduce((a, b) => a + b, 0) / selectedScores.length)
                : 50;

            return {
                id: p.id,
                vendor: p.vendor,
                price: p.price,
                summary: p.summary || 'No summary',
                scores: scores,
                overallScore
            };
        });
    }, [activeProposals, availableDimensions, selectedDimensions, aiScores]);

    // =======================
    // DIMENSION SELECTION HANDLERS
    // =======================
    const toggleDimension = (dimId) => {
        if (selectedDimensions.includes(dimId)) {
            setSelectedDimensions(selectedDimensions.filter(d => d !== dimId));
        } else if (selectedDimensions.length < 5) {
            setSelectedDimensions([...selectedDimensions, dimId]);
        }
    };

    const generateReport = async () => {
        if (selectedDimensions.length > 0) {
            const proposalIds = activeProposals.map(p => p.id);
            let fetchedAiData = null;

            // Fetch AI-powered comparison scores
            setLoadingScores(true);
            try {
                const aiRes = await fetch(`http://localhost:8000/api/analysis/rfp/${rfpId}/compare`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        proposal_ids: proposalIds,
                        dimensions: selectedDimensions
                    })
                });

                if (aiRes.ok) {
                    fetchedAiData = await aiRes.json();
                    setAiScores(fetchedAiData);
                    console.log("AI Comparison Scores:", fetchedAiData);
                } else {
                    console.error("AI comparison failed, using fallback scores");
                }
            } catch (e) {
                console.error("Failed to fetch AI scores:", e);
            } finally {
                setLoadingScores(false);
            }

            setShowReport(true);
            setCacheStale(false); // Cache is now fresh

            // Auto-save comparison WITH cached AI scores
            try {
                await fetch('http://localhost:8000/api/comparisons', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        rfp_id: rfpId,
                        dimensions: selectedDimensions,
                        proposal_ids: proposalIds,
                        scores_cache: fetchedAiData  // Save AI scores for instant reload
                    })
                });
                console.log("Comparison with AI scores saved successfully");
            } catch (e) {
                console.error("Failed to auto-save comparison:", e);
            }
        }
    };

    // =======================
    // CHARTS (only for selected dimensions)
    // =======================
    const selectedDimensionNames = selectedDimensions.map(dimId =>
        availableDimensions.find(d => d.id === dimId)?.name || dimId
    );

    const radarOptions = {
        chart: { type: 'radar', toolbar: { show: false } },
        xaxis: { categories: selectedDimensionNames },
        colors: ['#3b82f6', '#10b981', '#f59e0b'],
        stroke: { width: 2 },
        fill: { opacity: 0.2 },
        markers: { size: 4 },
        legend: { position: 'top' }
    };

    const radarSeries = dimensionsData.slice(0, 3).map(d => ({
        name: d.vendor,
        data: selectedDimensions.map(dimId => d.scores[dimId] || 50)
    }));

    const barOptions = {
        chart: { type: 'bar', height: 350, stacked: false, toolbar: { show: false } },
        plotOptions: { bar: { horizontal: false, columnWidth: '45%', borderRadius: 4 } },
        dataLabels: { enabled: false },
        xaxis: { categories: dimensionsData.map(d => d.vendor.split(' ')[0]) },
        yaxis: { title: { text: 'Score (0-100)' }, max: 100 },
        colors: ['#3b82f6', '#10b981'],
        legend: { position: 'top' },
        fill: { opacity: 1 }
    };

    const barSeries = [
        { name: 'Overall Score', data: dimensionsData.map(d => d.overallScore || 0) },
        { name: 'Price Score', data: dimensionsData.map(d => (d.scores && d.scores.cost) || 0) }
    ];

    // =======================
    // RENDER: DIMENSION SELECTION
    // =======================
    // =======================
    // RENDER: LIST OF COMPARISONS (If no specific RFP selected)
    // =======================
    // =======================
    // RENDER: LIST OF COMPARISONS (If no specific RFP selected)
    // =======================
    if (!rfpId) {
        return (
            <div className="animate-fade-in pb-12">
                <h1 className="text-3xl font-bold text-slate-900 mb-6">Saved Comparisons</h1>
                {loadingSaved ? (
                    <div className="text-center py-12 bg-white rounded-xl border border-slate-200">
                        <p className="text-slate-500">Loading saved comparisons...</p>
                    </div>
                ) : savedComparisons.length === 0 ? (
                    <div className="text-center py-12 bg-white rounded-xl border border-slate-200">
                        <p className="text-slate-500 mb-4">No saved comparisons found.</p>
                        <p className="text-sm text-slate-400">Navigate to an RFP, generate a report, and save it to see it here.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                        {savedComparisons.map(comp => (
                            <button
                                key={comp.id}
                                onClick={() => setSearchParams({ rfp: comp.rfp_id })}
                                className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm hover:shadow-md hover:border-blue-300 transition-all text-left"
                            >
                                <h3 className="font-bold text-lg text-slate-800 mb-2">{comp.rfp_title || 'Unknown RFP'}</h3>
                                <p className="text-sm text-slate-500 mb-4 line-clamp-2">Comparison of proposals</p>
                                <div className="flex justify-between items-center text-xs font-medium text-slate-400">
                                    <span>{new Date().toLocaleDateString()}</span>
                                    <span className="text-blue-600">View Report →</span>
                                </div>
                            </button>
                        ))}
                    </div>
                )}
            </div>
        );
    }

    if (!showReport) {
        return (
            <div className="animate-fade-in pb-12">
                <div className="flex justify-between items-center mb-8">
                    <div>
                        <h1 className="text-3xl font-bold text-slate-900 mb-2">Compare Proposals</h1>
                        <p className="text-slate-500">For RFP: <span className="font-bold text-slate-800">{activeRFP?.title}</span></p>
                    </div>

                    <div className="flex items-center gap-3">
                        <div className="flex items-center gap-2 bg-white px-3 py-2 rounded-lg border border-slate-200">
                            <label htmlFor="filter-accepted" className="text-sm font-medium text-slate-700 cursor-pointer select-none">Show Accepted Only</label>
                            <div
                                onClick={() => setShowAcceptedOnly(!showAcceptedOnly)}
                                className={`w-10 h-5 rounded-full relative cursor-pointer transition-colors ${showAcceptedOnly ? 'bg-blue-600' : 'bg-slate-300'}`}
                            >
                                <div className={`absolute top-1 w-3 h-3 bg-white rounded-full transition-all ${showAcceptedOnly ? 'left-6' : 'left-1'}`}></div>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8">
                    <h3 className="font-bold text-slate-700 mb-2">Select Comparison Dimensions (Max 5)</h3>
                    <p className="text-sm text-slate-500 mb-6">Choose the criteria you want to use for comparing proposals</p>

                    {/* General Dimensions */}
                    <div className="mb-6">
                        <div className="text-xs font-bold text-slate-400 uppercase mb-3">General Dimensions</div>
                        <div className="flex flex-wrap gap-3">
                            {availableDimensions.filter(d => d.type === 'general').length > 0 ? (
                                availableDimensions.filter(d => d.type === 'general').map(dim => (
                                    <button
                                        key={dim.id}
                                        onClick={() => toggleDimension(dim.id)}
                                        className={`px-4 py-2 rounded-full font-medium transition-all ${selectedDimensions.includes(dim.id)
                                            ? 'bg-blue-600 text-white'
                                            : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                                            }`}
                                        disabled={!selectedDimensions.includes(dim.id) && selectedDimensions.length >= 5}
                                        title={!selectedDimensions.includes(dim.id) && selectedDimensions.length >= 5 ? "Max 5 dimensions selected" : dim.description}
                                    >
                                        {dim.name}
                                    </button>
                                ))
                            ) : (
                                <p className="text-sm text-slate-400 italic">No general dimensions available.</p>
                            )}
                        </div>
                    </div>

                    {/* AI-Extracted Dimensions */}
                    <div className="mb-6">
                        <div className="text-xs font-bold text-slate-400 uppercase mb-3">RFP Requirement Dimensions</div>
                        {loadingDimensions ? (
                            <div className="flex items-center space-x-2 text-slate-400">
                                <div className="animate-spin h-4 w-4 border-2 border-current border-t-transparent rounded-full"></div>
                                <span className="text-sm italic">AI is extracting dimensions...</span>
                            </div>
                        ) : availableDimensions.filter(d => d.type === 'dynamic').length > 0 ? (
                            <div className="flex flex-wrap gap-3">
                                {availableDimensions.filter(d => d.type === 'dynamic').map(dim => (
                                    <button
                                        key={dim.id}
                                        onClick={() => toggleDimension(dim.id)}
                                        className={`px-4 py-2 rounded-full font-medium transition-all ${selectedDimensions.includes(dim.id)
                                            ? 'bg-teal-600 text-white'
                                            : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                                            }`}
                                        disabled={!selectedDimensions.includes(dim.id) && selectedDimensions.length >= 5}
                                        title={!selectedDimensions.includes(dim.id) && selectedDimensions.length >= 5 ? "Max 5 dimensions selected" : dim.description}
                                    >
                                        {dim.name}
                                    </button>
                                ))}
                            </div>
                        ) : (
                            <p className="text-sm text-slate-400 italic">No specific dimensions extracted yet.</p>
                        )}
                    </div>

                    {/* Stale Cache Warning */}
                    {cacheStale && (
                        <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg flex items-center gap-2">
                            <span className="text-amber-600">⚠️</span>
                            <span className="text-sm text-amber-800">
                                Proposals have changed since last comparison. Click "Update Report" to refresh AI analysis.
                            </span>
                        </div>
                    )}

                    <div className="flex items-center justify-between pt-6 border-t border-slate-200">
                        <div className="text-sm text-slate-600">
                            Selected: <span className="font-bold text-slate-900">{selectedDimensions.length}</span> / 5
                        </div>
                        <button
                            onClick={generateReport}
                            disabled={selectedDimensions.length === 0 || loadingScores}
                            className={`px-6 py-3 rounded-lg font-semibold ${selectedDimensions.length > 0 && !loadingScores
                                ? cacheStale ? 'bg-amber-500 text-white hover:bg-amber-600' : 'bg-blue-600 text-white hover:bg-blue-700'
                                : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                                }`}
                        >
                            {loadingScores ? 'Analyzing...' : cacheStale ? 'Update Report' : 'Generate Report'}
                        </button>
                    </div>
                </div>
            </div>
        );
    }



    const saveComparison = async () => {
        // Should really save current accepted proposals too
        const proposalIds = activeProposals.map(p => p.id);

        try {
            const res = await fetch('http://localhost:8000/api/comparisons', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    rfp_id: rfpId,
                    dimensions: selectedDimensions,
                    proposal_ids: proposalIds
                })
            });

            if (res.ok) {
                alert("Comparison report saved successfully!");
            } else {
                alert("Failed to save comparison.");
            }
        } catch (e) {
            console.error(e);
            alert("Error saving comparison.");
        }
    };

    // =======================
    // RENDER: COMPARISON REPORT
    // =======================
    return (
        <div className="animate-fade-in pb-12">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 mb-2">Comparison Report</h1>
                    <p className="text-slate-500">Analysis for RFP: <span className="font-bold text-slate-800">{activeRFP?.title}</span></p>
                </div>
                <div className="flex gap-3 print:hidden">
                    <button
                        onClick={() => window.print()}
                        className="text-sm px-4 py-2 bg-slate-800 text-white hover:bg-slate-900 rounded font-medium shadow-sm flex items-center gap-2"
                    >
                        <span>Download PDF</span>
                    </button>
                    <button
                        onClick={saveComparison}
                        className="text-sm px-4 py-2 bg-blue-50 text-blue-700 hover:bg-blue-100 rounded font-medium border border-blue-200"
                    >
                        Save Comparison
                    </button>
                    <button
                        onClick={() => setShowReport(false)}
                        className="text-sm px-4 py-2 bg-slate-100 text-slate-700 hover:bg-slate-200 rounded font-medium"
                    >
                        ← Change Dimensions
                    </button>
                </div>
            </div>

            <style>
                {`
                @media print {
                    .print\\:hidden { display: none !important; }
                    body { background: white; }
                    .sidebar, header, nav { display: none !important; } /* Try to hide layout elements if accessible via common classes, otherwise layout specific override needed */
                    #root > div > div.flex > aside { display: none; } /* Specific Layout targeting */
                    main { padding: 0; margin: 0; }
                }
                `}
            </style>

            {/* Charts */}
            {dimensionsData.length > 0 ? (
                <>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                            <h3 className="font-bold text-slate-700 mb-4">Attribute Analysis</h3>
                            <ReactApexChart options={radarOptions} series={radarSeries} type="radar" height={300} />
                        </div>
                        <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                            <h3 className="font-bold text-slate-700 mb-4">Score vs Price</h3>
                            <ReactApexChart options={barOptions} series={barSeries} type="bar" height={300} />
                        </div>
                    </div>
                </>
            ) : (
                <div className="bg-amber-50 border border-amber-200 p-8 rounded-xl text-center mb-8">
                    <p className="text-amber-800 font-semibold mb-2">No comparison data available.</p>
                    <p className="text-amber-600 text-sm">Either no proposals are accepted or data is missing. Please accept proposals in the RFP first.</p>
                </div>
            )}

            {/* Table */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left">
                        <thead className="bg-slate-50 border-b border-slate-200">
                            <tr>
                                <th className="p-4 text-xs font-bold text-slate-500 uppercase">Vendor</th>
                                {selectedDimensions.map(dimId => {
                                    const dim = availableDimensions.find(d => d.id === dimId);
                                    return <th key={dimId} className="p-4 text-xs font-bold text-slate-500 uppercase">{dim?.name}</th>;
                                })}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {dimensionsData.map((d) => (
                                <tr key={d.id} className="hover:bg-slate-50">
                                    <td className="p-4 font-semibold text-slate-800">{d.vendor}</td>
                                    {selectedDimensions.map(dimId => (
                                        <td key={dimId} className="p-4">
                                            <div className="flex flex-col items-start gap-1">
                                                <span className={`px-2 py-1 rounded text-sm font-medium ${d.scores[dimId] >= 80 ? 'bg-green-100 text-green-700' :
                                                    d.scores[dimId] >= 50 ? 'bg-yellow-100 text-yellow-700' :
                                                        'bg-red-100 text-red-700'
                                                    }`}>
                                                    {d.scores[dimId]}%
                                                </span>
                                                <span className="text-xs text-slate-500">
                                                    {d.scoreDetails?.[dimId]?.label ||
                                                        (d.scores[dimId] >= 80 ? 'Strong' :
                                                            d.scores[dimId] >= 50 ? 'Adequate' : 'Weak')}
                                                </span>
                                            </div>
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Modal */}
            {selectedProposal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-auto">
                        <div className="p-6 border-b border-slate-200 flex justify-between items-center">
                            <h3 className="font-bold text-lg">{selectedProposal.vendor} - Details</h3>
                            <button onClick={() => setSelectedProposal(null)} className="text-slate-400 hover:text-slate-600">
                                <X size={24} />
                            </button>
                        </div>
                        <div className="p-6 space-y-4">
                            <div><div className="text-xs font-bold text-slate-500 uppercase mb-1">Price</div><div>{selectedProposal.price}</div></div>
                            <div><div className="text-xs font-bold text-slate-500 uppercase mb-1">Summary</div><div>{selectedProposal.summary}</div></div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
