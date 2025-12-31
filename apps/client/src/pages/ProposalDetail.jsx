import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Send, User as UserIcon, Bot, ArrowLeft, FileText, CheckCircle, XCircle } from 'lucide-react';
import { useRFP } from '../context/RFPContext';

const API_BASE = 'http://localhost:8000/api';

export default function ProposalDetail() {
    const { id } = useParams();
    const { proposals } = useRFP();
    const [proposal, setProposal] = useState(null);
    const [fullProposal, setFullProposal] = useState(null);
    const [messages, setMessages] = useState([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // First, try to find in context for basic display
        const found = proposals.find(p => String(p.id) === String(id));
        if (found) {
            setProposal(found);
        }

        // Then fetch full details from backend
        fetchProposalDetails();
    }, [id, proposals]);

    const fetchProposalDetails = async () => {
        try {
            const response = await fetch(`${API_BASE}/proposals/${id}`);
            if (!response.ok) throw new Error('Failed to fetch proposal');

            const data = await response.json();
            console.log('✅ Fetched full proposal details:', data);

            setFullProposal(data);
            setProposal(prev => prev || {
                id: data.id,
                vendor: data.contractor,
                price: data.price ? `$${data.price.toLocaleString()}` : 'Not specified',
                status: data.status === 'submitted' ? 'Pending' : data.status.charAt(0).toUpperCase() + data.status.slice(1)
            });

            setMessages([
                { role: 'ai', text: `I have analyzed the proposal from ${data.contractor}. I can answer questions about pricing, warranties, timeline, or their experience. What would you like to know?` }
            ]);

        } catch (err) {
            console.error('Error fetching proposal details:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleSend = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMsg = { role: 'user', text: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');

        try {
            // Prepare history for context
            const history = messages.map(m => ({
                role: m.role,
                content: m.text // Backend expects 'content', frontend uses 'text'
            }));

            const response = await fetch(`${API_BASE}/proposals/${id}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    proposal_id: id,
                    message: userMsg.text,
                    conversation_history: history
                })
            });

            if (!response.ok) throw new Error('Chat request failed');

            const data = await response.json();

            setMessages(prev => [...prev, {
                role: 'ai',
                text: data.reply
            }]);

        } catch (err) {
            console.error('Chat error:', err);
            setMessages(prev => [...prev, {
                role: 'ai',
                text: "I'm having trouble connecting to the backend. Please ensure the server is running."
            }]);
        }
    };

    if (!proposal) {
        return (
            <div className="p-12 text-center">
                <div className="text-slate-400 mb-4">Proposal not found ({id})</div>
                <Link to="/comparisons" className="text-blue-600 hover:underline">Return to Comparisons</Link>
            </div>
        );
    }

    return (
        <div className="h-[calc(100vh-80px)] flex flex-col animate-fade-in pb-4">
            {/* Header */}
            <div className="flex items-center justify-between mb-6 shrink-0">
                <div className="flex items-center gap-4">
                    <Link to={fullProposal?.rfpId ? `/rfp/${fullProposal.rfpId}?tab=proposals` : (proposal?.rfpId ? `/rfp/${proposal.rfpId}?tab=proposals` : "/comparisons")} className="p-2 hover:bg-slate-100 rounded-full text-slate-500 transition-colors">
                        <ArrowLeft size={20} />
                    </Link>
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-3">
                            {proposal.vendor}
                            <span className={`text-sm px-3 py-1 rounded-full border ${proposal.status === 'Accepted' ? 'bg-green-100 text-green-700 border-green-200' :
                                proposal.status === 'Rejected' ? 'bg-red-50 text-red-600 border-red-100' :
                                    'bg-blue-50 text-blue-600 border-blue-100'
                                }`}>
                                {proposal.status}
                            </span>
                        </h1>
                        <p className="text-slate-500 text-sm">Submitted on {new Date().toLocaleDateString()}</p>
                    </div>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={() => fullProposal && window.open(`http://localhost:8000/storage/proposals/${fullProposal.rfpId}/${fullProposal.id}.pdf`, '_blank')}
                        className="btn bg-white border border-slate-200 text-slate-700 hover:bg-slate-50 shadow-sm"
                    >
                        <FileText size={16} /> View PDF
                    </button>
                    {proposal.status !== 'Accepted' && proposal.status !== 'Rejected' && (
                        <>
                            <button
                                onClick={() => useRFP().updateProposalStatus(id, 'Rejected')}
                                className="btn bg-red-50 text-red-600 border border-red-100 hover:bg-red-100"
                            >
                                <XCircle size={16} /> Reject
                            </button>
                            <button
                                onClick={() => useRFP().updateProposalStatus(id, 'Accepted')}
                                className="btn bg-green-600 text-white hover:bg-green-700 shadow-md"
                            >
                                <CheckCircle size={16} /> Accept Proposal
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* Content Grid */}
            <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-6 overflow-hidden">

                {/* Proposal Details */}
                <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 overflow-y-auto">
                    {loading ? (
                        <div className="flex items-center justify-center h-full">
                            <div className="text-slate-400">Loading proposal details...</div>
                        </div>
                    ) : !fullProposal ? (
                        <div className="flex items-center justify-center h-full">
                            <div className="text-center">
                                <FileText size={48} className="mx-auto text-slate-300 mb-3" />
                                <p className="text-slate-500 font-medium">Proposal data not available</p>
                            </div>
                        </div>
                    ) : (
                        <div className="p-6 space-y-6">
                            <h2 className="text-xl font-bold text-slate-900 border-b border-slate-200 pb-3">
                                Proposal Details
                            </h2>

                            {/* Summary */}
                            {fullProposal.summary && (
                                <div>
                                    <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-2">
                                        Summary
                                    </h3>
                                    <p className="text-slate-700">{fullProposal.summary}</p>
                                </div>
                            )}

                            {/* Key Info Grid */}
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-1">
                                        Price
                                    </h3>
                                    <p className="text-lg font-mono text-slate-900">
                                        {fullProposal.price ? `${fullProposal.currency} $${fullProposal.price.toLocaleString()}` : 'Not specified'}
                                    </p>
                                </div>
                                <div>
                                    <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-1">
                                        Start Date
                                    </h3>
                                    <p className="text-lg text-slate-900">
                                        {fullProposal.start_date || 'Not specified'}
                                    </p>
                                </div>
                            </div>

                            {/* Experience */}
                            {fullProposal.experience && (
                                <div>
                                    <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-2">
                                        💼 Experience & Qualifications
                                    </h3>
                                    <p className="text-slate-700 whitespace-pre-wrap">{fullProposal.experience}</p>
                                </div>
                            )}

                            {/* Methodology */}
                            {fullProposal.methodology && (
                                <div>
                                    <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-2">
                                        🔧 Methodology & Approach
                                    </h3>
                                    <p className="text-slate-700 whitespace-pre-wrap">{fullProposal.methodology}</p>
                                </div>
                            )}

                            {/* Warranties */}
                            {fullProposal.warranties && (
                                <div>
                                    <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-2">
                                        🛡️ Warranties & Guarantees
                                    </h3>
                                    <p className="text-slate-700 whitespace-pre-wrap">{fullProposal.warranties}</p>
                                </div>
                            )}

                            {/* Timeline */}
                            {fullProposal.timeline_details && (
                                <div>
                                    <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-2">
                                        📅 Timeline Details
                                    </h3>
                                    <p className="text-slate-700 whitespace-pre-wrap">{fullProposal.timeline_details}</p>
                                </div>
                            )}

                            {/* Contact Info */}
                            {fullProposal.contractor_email && (
                                <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
                                    <h3 className="text-sm font-bold text-slate-500 uppercase tracking-wide mb-2">
                                        Contact Information
                                    </h3>
                                    <p className="text-slate-700">
                                        <span className="font-semibold">{fullProposal.contractor}</span>
                                        <br />
                                        <a href={`mailto:${fullProposal.contractor_email}`} className="text-blue-600 hover:underline">
                                            {fullProposal.contractor_email}
                                        </a>
                                    </p>
                                </div>
                            )}
                        </div>
                    )}
                </div>

                {/* Chat */}
                <div className="bg-white rounded-xl border border-slate-200 shadow-xl flex flex-col overflow-hidden">
                    <div className="p-4 border-b border-slate-100 bg-slate-50 flex items-center gap-2 font-semibold text-slate-700">
                        <Bot size={18} className="text-blue-600" />
                        Chat with {proposal.vendor}
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-white">
                        {messages.map((msg, idx) => (
                            <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-emerald-100 text-emerald-600'
                                    }`}>
                                    {msg.role === 'user' ? <UserIcon size={14} /> : <Bot size={14} />}
                                </div>
                                <div className={`py-2 px-3 rounded-2xl text-sm max-w-[85%] ${msg.role === 'user' ? 'bg-blue-600 text-white rounded-tr-none' : 'bg-slate-100 text-slate-700 rounded-tl-none'
                                    }`}>
                                    {msg.text}
                                </div>
                            </div>
                        ))}
                    </div>

                    <form onSubmit={handleSend} className="p-3 border-t border-slate-100 bg-slate-50">
                        <div className="flex gap-2">
                            <input
                                className="flex-1 bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400"
                                placeholder="Ask about this proposal..."
                                value={input}
                                onChange={e => setInput(e.target.value)}
                            />
                            <button type="submit" className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors shadow-sm">
                                <Send size={16} />
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
    );
}
