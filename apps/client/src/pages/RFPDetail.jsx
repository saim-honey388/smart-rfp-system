import React, { useState } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import { Download, XCircle, Upload, CheckCircle, X, MessageSquare, Briefcase, FileText } from 'lucide-react';
import { useRFP } from '../context/RFPContext';

export default function RFPDetail() {
    const { id } = useParams();
    const { getRFP, getProposalsForRFP, addProposal, updateProposalStatus, updateRFP } = useRFP();

    const rfp = getRFP(id);
    const proposals = getProposalsForRFP(id);

    const [searchParams] = useSearchParams();
    const initialTab = searchParams.get('tab');
    const [activeTab, setActiveTab] = useState(initialTab || 'overview');

    if (!rfp) {
        return <div className="p-8 text-center text-red-500 font-bold">RFP Not Found (ID: {id})</div>;
    }

    const handleCloseRFP = () => {
        if (window.confirm("Are you sure you want to close this RFP? No more proposals can be submitted.")) {
            updateRFP(id, { status: 'closed' });
        }
    };

    const handleDownload = () => {
        // Mock Download
        const btn = document.getElementById('download-btn');
        const originalText = btn.innerHTML;
        btn.innerHTML = "Downloading...";
        setTimeout(() => {
            btn.innerHTML = originalText;
            alert("PDF downloaded successfully!");
        }, 1000);
    };

    const handleFileUpload = (e) => {
        const file = e.target.files[0];
        if (file) {
            addProposal(id, file);
            // alert("File uploaded! AI is processing...");
        }
    };

    return (
        <div className="animate-fade-in pb-12">
            {/* Breadcrumbs */}
            <div className="mb-4 text-sm text-slate-500 flex gap-2">
                <Link to="/open-rfps" className="hover:text-blue-600">Open RFPs</Link> / <span>{rfp.title}</span>
            </div>

            {/* Header */}
            <div className="flex justify-between items-start mb-8 bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                <div>
                    <h1 className="text-2xl font-bold text-slate-900 mb-2">{rfp.title}</h1>
                    <div className="flex gap-4 text-sm text-slate-500">
                        <span className="flex items-center gap-1">
                            <Briefcase size={14} /> Status:
                            <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${rfp.status === 'open' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                                }`}>{rfp.status?.toUpperCase()}</span>
                        </span>
                        <span>Due: <span className="font-semibold text-slate-700">{rfp.due}</span></span>
                        <span>Budget: <span className="font-semibold text-slate-700">{rfp.budget || 'N/A'}</span></span>
                    </div>
                </div>

                <div className="flex gap-2">
                    <button id="download-btn" onClick={handleDownload} className="btn btn-secondary flex items-center gap-2">
                        <Download size={16} /> Download PDF
                    </button>
                    {rfp.status === 'open' && (
                        <button onClick={handleCloseRFP} className="btn bg-white border border-red-200 text-red-600 hover:bg-red-50 flex items-center gap-2">
                            <XCircle size={16} /> Close RFP
                        </button>
                    )}
                </div>
            </div>

            {/* Navigation Tabs */}
            <div className="flex gap-8 border-b border-slate-200 mb-8">
                {['overview', 'proposals', 'comparison', 'documents'].map(tab => (
                    <button
                        key={tab}
                        onClick={() => setActiveTab(tab)}
                        className={`pb-3 text-sm font-semibold capitalize transition-all border-b-2 ${activeTab === tab
                            ? 'border-blue-600 text-blue-600'
                            : 'border-transparent text-slate-500 hover:text-slate-700'
                            }`}
                    >
                        {tab}
                    </button>
                ))}
            </div>

            {/* Overview Tab */}
            {activeTab === 'overview' && (
                <section className="bg-white p-8 rounded-xl border border-slate-200 shadow-sm">
                    <h3 className="text-lg font-bold mb-4 text-slate-800">RFP Details</h3>
                    <div className="prose prose-slate max-w-none">
                        <div className="mb-6">
                            <h4 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-2">Scope of Work</h4>
                            <p className="whitespace-pre-wrap">{rfp.scope || "No scope defined."}</p>
                        </div>
                        {rfp.requirements && (
                            <div>
                                <h4 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-2">Requirements</h4>
                                <ul className="list-disc pl-5">
                                    {Array.isArray(rfp.requirements) ? rfp.requirements.map((r, i) => (
                                        <li key={i}>
                                            {typeof r === 'string' ? r : r.text || JSON.stringify(r)}
                                        </li>
                                    )) : <li>See PDF for details.</li>}
                                </ul>
                            </div>
                        )}
                    </div>
                </section>
            )}

            {/* Proposals Tab */}
            {activeTab === 'proposals' && (
                <div className="space-y-6">

                    {/* Upload Card - Only for Open RFPs */}
                    {rfp.status === 'open' ? (
                        <div className="bg-slate-50 border-2 border-dashed border-slate-300 rounded-xl p-8 text-center hover:bg-slate-100 transition-colors">
                            <input type="file" id="prop-upload" className="hidden" onChange={handleFileUpload} />
                            <label htmlFor="prop-upload" className="cursor-pointer flex flex-col items-center">
                                <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center mb-3">
                                    <Upload size={24} />
                                </div>
                                <h3 className="font-semibold text-slate-900">Upload New Proposal</h3>
                                <p className="text-slate-500 text-sm mb-4">Drag and drop or click to browse</p>
                                <div className="btn btn-primary pointer-events-none">Select File</div>
                            </label>
                        </div>
                    ) : (
                        <div className="bg-amber-50 border-2 border-amber-200 rounded-xl p-8 text-center">
                            <div className="w-12 h-12 bg-amber-100 text-amber-600 rounded-full flex items-center justify-center mb-3 mx-auto">
                                <X size={24} />
                            </div>
                            <h3 className="font-semibold text-amber-900 mb-2">Proposal Submission Closed</h3>
                            <p className="text-amber-700 text-sm">
                                This RFP is currently <span className="font-bold">{rfp.status.toUpperCase()}</span>.
                                {rfp.status === 'draft' ? ' Complete the RFP and publish it to accept proposals.' : ' No new proposals are being accepted.'}
                            </p>
                        </div>
                    )}

                    {/* List */}
                    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
                        <div className="p-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                            <h3 className="font-semibold text-slate-700">Received Proposals ({proposals.length})</h3>
                            <Link to={`/comparisons?rfp=${id}`} className="text-sm font-medium text-blue-600 hover:underline">Compare All &rarr;</Link>
                        </div>

                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-slate-50 border-b border-slate-200 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                                    <th className="p-4">Vendor</th>
                                    <th className="p-4">Price</th>
                                    <th className="p-4">Summary</th>
                                    <th className="p-4">Status</th>
                                    <th className="p-4 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100">
                                {(!proposals || proposals.length === 0) ? (
                                    <tr><td colSpan="5" className="p-8 text-center text-slate-400">No proposals received yet.</td></tr>
                                ) : proposals.map(p => (
                                    <tr key={p.id} className="hover:bg-slate-50 transition-colors">
                                        <td className="p-4">
                                            <div className="font-semibold text-slate-800">{p.vendor}</div>
                                            <div className="text-xs text-slate-500 flex items-center gap-1"><FileText size={12} /> {p.file}</div>
                                        </td>
                                        <td className="p-4 font-mono text-slate-700">{p.price}</td>
                                        <td className="p-4 max-w-xs">
                                            <div className="text-sm text-slate-600 line-clamp-2" title={p.summary}>
                                                {p.summary || 'No summary available'}
                                            </div>
                                            {p.experience && (
                                                <div className="text-xs text-slate-400 mt-1">
                                                    💼 Experience available
                                                </div>
                                            )}
                                        </td>
                                        <td className="p-4">
                                            {p.status === 'Processing' ? (
                                                <span className="flex items-center gap-1 text-slate-500 text-xs font-medium animate-pulse">
                                                    <Upload size={12} className="animate-bounce" /> Analyzing...
                                                </span>
                                            ) : (
                                                <span className={`px-2 py-1 rounded-full text-xs font-bold border ${p.status === 'Accepted' ? 'bg-green-50 text-green-700 border-green-200' :
                                                    p.status === 'Rejected' ? 'bg-red-50 text-red-700 border-red-200' :
                                                        'bg-amber-50 text-amber-700 border-amber-200'
                                                    }`}>
                                                    {p.status}
                                                </span>
                                            )}
                                        </td>
                                        <td className="p-4 text-right">
                                            <div className="flex justify-end gap-2">
                                                <Link to={`/proposal/${p.id}`} className="p-2 text-slate-500 hover:bg-slate-100 rounded-lg hover:text-blue-600 transition-colors" title="Chat with AI">
                                                    <MessageSquare size={18} />
                                                </Link>

                                                <button
                                                    onClick={() => updateProposalStatus(p.id, 'Accepted')}
                                                    disabled={p.status === 'Accepted' || p.status === 'Rejected'}
                                                    className={`p-2 rounded-lg transition-colors ${p.status === 'Rejected'
                                                        ? 'text-slate-300 cursor-not-allowed'
                                                        : p.status === 'Accepted'
                                                            ? 'text-green-600 bg-green-50 cursor-default'
                                                            : 'text-slate-500 hover:bg-green-50 hover:text-green-600'
                                                        }`}
                                                    title={p.status === 'Rejected' ? 'Locked - Cannot accept rejected proposal' : p.status === 'Accepted' ? 'Already Accepted' : 'Accept'}
                                                >
                                                    <CheckCircle size={18} />
                                                </button>

                                                <button
                                                    onClick={() => updateProposalStatus(p.id, 'Rejected')}
                                                    disabled={p.status === 'Rejected' || p.status === 'Accepted'}
                                                    className={`p-2 rounded-lg transition-colors ${p.status === 'Accepted'
                                                        ? 'text-slate-300 cursor-not-allowed'
                                                        : p.status === 'Rejected'
                                                            ? 'text-red-600 bg-red-50 cursor-default'
                                                            : 'text-slate-500 hover:bg-red-50 hover:text-red-600'
                                                        }`}
                                                    title={p.status === 'Accepted' ? 'Locked - Cannot reject accepted proposal' : p.status === 'Rejected' ? 'Already Rejected' : 'Reject'}
                                                >
                                                    <X size={18} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            )}

            {/* Fallbacks */}
            {activeTab === 'comparison' && <div className="p-12 text-center bg-white rounded-xl border border-slate-200"><Link to="/comparisons" className="btn btn-primary">Go to Comparison Report</Link></div>}
            {activeTab === 'documents' && <div className="p-12 text-center text-slate-400 bg-white rounded-xl border border-slate-200">No legal documents available yet.</div>}
        </div>
    );
}
