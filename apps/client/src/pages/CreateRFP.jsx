import React, { useState, useEffect, useRef } from 'react';
import { Upload, ArrowLeft, CheckCircle, Send, Sparkles, AlertCircle, ChevronRight, FileText } from 'lucide-react';
import { useNavigate, useParams } from 'react-router-dom';
import { useRFP } from '../context/RFPContext';
import { useToast } from '../components/Toast';

export default function CreateRFP() {
    const navigate = useNavigate();
    const { id } = useParams(); // Edit mode if ID present
    const { addRFP, getRFP, updateRFP, chatWithRFPConsultant, uploadRFPFile } = useRFP();
    const { addToast } = useToast();
    const [step, setStep] = useState('select'); // select, editor

    // ... (rest of simple state)

    // ... (rest of logic mostly unchanged until handleFinalize)

    const handleFinalize = async () => {
        const errors = [];

        if (!rfpData.title?.trim()) errors.push("Title");
        if (!rfpData.scope?.trim()) errors.push("Project Scope");
        if (!rfpData.budget) errors.push("Budget");
        if (!rfpData.timeline.end || rfpData.timeline.end === "TBD") errors.push("Due Date");

        if (errors.length > 0) {
            addToast(`Cannot publish - Missing: ${errors.join(', ')}`, 'error');
            return;
        }

        const publishedRFP = {
            ...rfpData,
            status: 'open',
            due: rfpData.timeline.end,
            chatHistory: chatMessages,  // Save chat for history
            conversationState: conversationState
        };

        if (id) {
            // Update existing draft
            await updateRFP(id, publishedRFP);
        } else {
            // Create new
            await addRFP(publishedRFP);
        }

        addToast("RFP Published Successfully!", "success");
        setTimeout(() => navigate('/open-rfps'), 500);
    };

    const handleSaveDraft = async () => {
        if (!rfpData.title?.trim()) {
            addToast("Please provide at least a Title before saving.", "error");
            return;
        }

        const draftData = {
            ...rfpData,
            status: 'draft',
            due: rfpData.timeline.end || "TBD",
            chatHistory: chatMessages,  // ✅ Save chat history
            conversationState: conversationState  // ✅ Save state
        };

        try {
            if (id) {
                // Update existing draft
                await updateRFP(id, draftData);
                addToast("Draft updated successfully!", "success");
            } else {
                // Create new draft
                await addRFP(draftData);
                addToast("Draft saved successfully!", "success");
            }
            // Small delay to let user see the toast before navigating
            setTimeout(() => navigate('/open-rfps'), 1000);
        } catch (error) {
            addToast(`Failed to save draft: ${error.message}`, "error");
        }
    };
    const chatEndRef = useRef(null);

    // -------------------------------------------------------------------------
    // 1. Structured Data Model
    // -------------------------------------------------------------------------
    const [rfpData, setRfpData] = useState({
        title: "",        // Required
        scope: "",        // Required (changed from 'overview')
        requirements: [], // At least 1 recommended
        timeline: { start: "TBD", end: "TBD" },
        budget: "",       // Required
        status: "draft"
    });

    // -------------------------------------------------------------------------
    // 2. Chat & Logic State
    // -------------------------------------------------------------------------
    const [chatMessages, setChatMessages] = useState([]);
    const [chatInput, setChatInput] = useState('');
    const [isTyping, setIsTyping] = useState(false);

    // State Machine for Conversation: 'INIT', 'ASK_TITLE', 'ASK_SCOPE', 'ASK_BUDGET', 'ASK_REQUIREMENTS', 'OPEN_EDIT'
    const [conversationState, setConversationState] = useState('INIT');

    const fileInputRef = useRef(null);

    const startConsultation = () => {
        setStep('editor');
        setConversationState('ASK_TITLE');
        setChatMessages([
            { role: 'ai', text: "Hello! I'm your AI Consultant. Let's build this RFP step-by-step. First, what is the **Title** of this project?" }
        ]);
    };

    const uploadContract = () => {
        // Trigger file input click
        fileInputRef.current?.click();
    };

    const handleFileUpload = async (event) => {
        const file = event.target.files?.[0];
        if (!file) return;

        try {
            setStep('editor');
            setConversationState('OPEN_EDIT');

            // Initial loading state
            setChatMessages([
                { role: 'ai', text: "I'm analyzing your RFP document... identifying scope, requirements, and timeline." }
            ]);

            // Show loading toast? Or just rely on chat message.

            // Call API

            // Call API
            const extracted = await uploadRFPFile(file);
            console.log("Extracted RFP Data:", extracted);

            // Populate Form
            setRfpData({
                title: extracted.title || "Untitled RFP",
                scope: extracted.scope || "",
                requirements: extracted.requirements || [],
                budget: extracted.budget || "TBD",
                timeline: {
                    start: "TBD",
                    end: extracted.timeline_end || "TBD"
                },
                status: "draft"
            });

            // Update Chat
            setChatMessages([
                { role: 'ai', text: "I've extracted the details from your PDF. Please review the draft on the right. You can ask me to change anything." }
            ]);

        } catch (error) {
            console.error("Extraction failed:", error);
            addToast(`Failed to process RFP: ${error.message}`, 'error');
            setStep('select'); // Go back on error
        }
    };

    // -------------------------------------------------------------------------
    // Draft Restoration Logic
    // -------------------------------------------------------------------------
    useEffect(() => {
        if (id) {
            const rfp = getRFP(id);
            if (rfp) {
                // Only restore if it's a draft
                if (rfp.status === 'draft') {
                    console.log("Loading draft RFP:", rfp);

                    // Restore RFP data
                    setRfpData({
                        title: rfp.title || "",
                        scope: rfp.scope || "",
                        requirements: rfp.requirements || [],
                        timeline: rfp.timeline || { start: "TBD", end: "TBD" },
                        budget: rfp.budget || "",
                        status: "draft"
                    });

                    // Restore chat history if it exists
                    if (rfp.chatHistory && rfp.chatHistory.length > 0) {
                        setChatMessages(rfp.chatHistory);
                        setConversationState(rfp.conversationState || 'OPEN_EDIT');
                        setStep('editor'); // Go straight to editor
                    } else {
                        // No chat history, start fresh but with data
                        setStep('editor');
                        setConversationState('OPEN_EDIT');
                        setChatMessages([
                            { role: 'ai', text: "Welcome back! I've restored your draft. You can continue editing or publish when ready." }
                        ]);
                    }
                } else {
                    // Non-draft RFP, redirect to detail view
                    navigate(`/rfp/${id}`);
                }
            }
        }
    }, [id, getRFP, navigate]);

    // Refs to track latest state for async AI operations
    const stateRef = useRef(conversationState);
    const dataRef = useRef(rfpData);

    useEffect(() => {
        stateRef.current = conversationState;
        dataRef.current = rfpData;
    }, [conversationState, rfpData]);

    const processInput = async (input) => {
        setIsTyping(true);

        try {
            // Prepare context for AI
            const currentState = {
                title: dataRef.current.title,
                scope: dataRef.current.scope,
                requirements: dataRef.current.requirements,
                budget: dataRef.current.budget,
                timeline_end: dataRef.current.timeline.end
            };

            // Limit history to plain text for API
            const history = chatMessages.map(m => ({
                role: m.role,
                text: m.text
            }));

            console.log("SENDING TO AI:", { input, currentState });

            const result = await chatWithRFPConsultant(input, currentState, history);

            console.log("AI RESPONSE:", result);

            // Update State with AI's extracted data
            const updates = result.updated_state;
            setRfpData(prev => ({
                ...prev,
                title: updates.title || prev.title,
                scope: updates.scope || prev.scope,
                requirements: updates.requirements && updates.requirements.length > 0 ? updates.requirements : prev.requirements,
                budget: updates.budget || prev.budget,
                timeline: {
                    ...prev.timeline,
                    end: updates.timeline_end || prev.timeline.end
                }
            }));

            // Add AI Reply
            setChatMessages(prev => [...prev, { role: 'ai', text: result.reply }]);

        } catch (err) {
            console.error(err);
            setChatMessages(prev => [...prev, { role: 'ai', text: "I'm having trouble connecting to the brain. Please try again." }]);
        } finally {
            setIsTyping(false);
        }
    };

    const handleSend = (e) => {
        e.preventDefault();
        if (!chatInput.trim()) return;
        setChatMessages(prev => [...prev, { role: 'user', text: chatInput }]);
        const txt = chatInput;
        setChatInput('');
        processInput(txt);
    };

    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatMessages, isTyping]);

    // -------------------------------------------------------------------------
    // Helper for Field Validation
    // -------------------------------------------------------------------------
    const isRFPComplete = () => {
        return !!(
            rfpData.title?.trim() &&
            rfpData.scope?.trim() &&
            rfpData.budget && rfpData.budget !== "TBD" &&
            rfpData.timeline.end && rfpData.timeline.end !== "TBD"
        );
    };



    // -------------------------------------------------------------------------
    // 4. Render Step 1: Selection
    // -------------------------------------------------------------------------
    if (step === 'select') {
        return (
            <div className="animate-fade-in max-w-5xl mx-auto p-12">
                <h1 className="text-3xl font-bold mb-4 text-slate-900">Create New RFP</h1>
                <p className="text-slate-500 mb-12 text-lg">Choose your starting point.</p>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <button onClick={uploadContract} className="bg-white p-8 rounded-2xl border border-slate-200 hover:border-blue-400 hover:shadow-xl transition-all text-left group">
                        <div className="w-16 h-16 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                            <Upload size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-slate-900 mb-2">Upload Contract</h3>
                        <p className="text-slate-500">Analyze an existing PDF to extract scope and pricing.</p>
                    </button>

                    <button onClick={startConsultation} className="bg-white p-8 rounded-2xl border border-slate-200 hover:border-teal-400 hover:shadow-xl transition-all text-left group">
                        <div className="w-16 h-16 bg-teal-50 text-teal-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
                            <Sparkles size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-slate-900 mb-2">Consultant AI</h3>
                        <p className="text-slate-500">Step-by-step interview to define your project needs.</p>
                    </button>

                    {/* Hidden File Input */}
                    <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileUpload}
                        accept=".pdf"
                        className="hidden"
                    />
                </div>
            </div>
        );
    }

    // -------------------------------------------------------------------------
    // 5. Render Step 2: Editor (Strict Grid Layout)
    // -------------------------------------------------------------------------
    return (
        <div className="flex flex-col h-screen overflow-hidden bg-slate-50">

            {/* Header */}
            <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6 flex-shrink-0 z-20 shadow-sm">
                <div className="flex items-center gap-4">
                    <button onClick={() => setStep('select')} className="text-slate-400 hover:text-slate-600"><ArrowLeft size={20} /></button>
                    <h2 className="font-bold text-slate-700">New RFP Draft</h2>
                </div>
                <div className="flex gap-3">
                    <button onClick={handleSaveDraft} className="text-sm font-medium text-slate-500 hover:text-slate-800 px-3">Save Draft</button>
                    <button
                        onClick={handleFinalize}
                        disabled={!isRFPComplete()}
                        className={`btn gap-2 ${isRFPComplete() ? 'btn-primary' : 'bg-slate-300 text-slate-500 cursor-not-allowed'}`}
                        title={!isRFPComplete() ? 'Complete all required fields to publish' : 'Publish RFP'}
                    >
                        <CheckCircle size={16} /> Publish RFP
                    </button>
                </div>
            </header>

            {/* Main Grid: FIXED 400px Sidebar | Flexible Preview */}
            <div className="flex-1 grid grid-cols-[400px_1fr] overflow-hidden">

                {/* LEFT: Chat Panel */}
                <div className="flex flex-col bg-white border-r border-slate-200 h-full overflow-hidden shadow-[4px_0_24px_rgba(0,0,0,0.02)] z-10">
                    <div className="p-4 border-b border-slate-100 font-semibold text-slate-700 flex items-center gap-2">
                        <Sparkles size={16} className="text-teal-500" /> AI Consultant
                    </div>

                    <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-50/50">
                        {chatMessages.map((msg, i) => (
                            <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${msg.role === 'ai' ? 'bg-teal-100 text-teal-600' : 'bg-blue-600 text-white'}`}>
                                    {msg.role === 'ai' ? <Sparkles size={14} /> : <div className="text-[10px] font-bold">YOU</div>}
                                </div>
                                <div className={`py-2 px-3 rounded-2xl text-sm max-w-[85%] ${msg.role === 'ai' ? 'bg-white border border-slate-200 text-slate-700 rounded-tl-none' : 'bg-blue-600 text-white rounded-tr-none'
                                    }`}>
                                    <div style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</div>
                                </div>
                            </div>
                        ))}
                        {isTyping && (
                            <div className="flex items-center gap-2 text-xs text-slate-400 pl-12">
                                <span className="w-2 h-2 bg-slate-300 rounded-full animate-bounce"></span>
                                <span className="w-2 h-2 bg-slate-300 rounded-full animate-bounce delay-75"></span>
                                <span className="w-2 h-2 bg-slate-300 rounded-full animate-bounce delay-150"></span>
                            </div>
                        )}
                        <div ref={chatEndRef} />
                    </div>

                    <form onSubmit={handleSend} className="p-4 bg-white border-t border-slate-200">
                        <div className="flex gap-2">
                            <input
                                autoFocus
                                className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400"
                                placeholder="Type your answer..."
                                value={chatInput}
                                onChange={e => setChatInput(e.target.value)}
                            />
                            <button disabled={!chatInput.trim() || isTyping} type="submit" className="p-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-colors">
                                <Send size={18} />
                            </button>
                        </div>
                    </form>
                </div>

                {/* RIGHT: Document Preview */}
                <div className="h-full overflow-y-auto bg-slate-100 p-8 flex justify-center">
                    <div className="w-[850px] min-h-[1100px] bg-white shadow-sm border border-slate-200 p-12 transition-all">

                        {/* Document Header */}
                        <div className="border-b-2 border-slate-900 pb-6 mb-8">
                            {rfpData.title ? (
                                <h1 className="text-4xl font-serif font-bold text-slate-900">{rfpData.title}</h1>
                            ) : (
                                <h1 className="text-4xl font-serif font-bold text-slate-300 italic">Untitled RFP</h1>
                            )}
                            <div className="mt-4 flex gap-4 text-xs font-bold uppercase tracking-wider text-slate-400">
                                <span>ID: PENDING</span>
                                <span>•</span>
                                <span>Created: {new Date().toLocaleDateString()}</span>
                            </div>
                        </div>

                        {/* Sections */}
                        <div className="space-y-10">

                            {/* Overview */}
                            <section>
                                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide border-b border-slate-200 pb-2 mb-4 flex items-center gap-2">
                                    1. Project Scope
                                    {rfpData.scope?.trim() ? (
                                        <span className="text-green-600" title="Complete">✓</span>
                                    ) : (
                                        <span className="text-red-500" title="Required">✗</span>
                                    )}
                                </h3>
                                {rfpData.scope ? (
                                    <p className="text-slate-700 leading-relaxed text-justify">{rfpData.scope}</p>
                                ) : (
                                    <div className="bg-red-50 border border-red-100 text-red-400 p-4 rounded text-sm flex items-center gap-2">
                                        <AlertCircle size={16} /> Waiting for input...
                                    </div>
                                )}
                            </section>

                            {/* Requirements */}
                            <section>
                                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide border-b border-slate-200 pb-2 mb-4 flex items-center gap-2">
                                    2. Key Requirements
                                    {rfpData.requirements.length > 0 ? (
                                        <span className="text-green-600" title="Complete">✓</span>
                                    ) : (
                                        <span className="text-amber-500" title="Optional">○</span>
                                    )}
                                </h3>
                                {rfpData.requirements.length > 0 ? (
                                    <ul className="list-disc pl-5 space-y-2 text-slate-700">
                                        {rfpData.requirements.map((r, i) => <li key={i}>{r}</li>)}
                                    </ul>
                                ) : (
                                    <p className="text-slate-400 italic">No requirements listed yet.</p>
                                )}
                            </section>

                            {/* Budget & Timeline */}
                            <div className="grid grid-cols-2 gap-8">
                                <section>
                                    <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide border-b border-slate-200 pb-2 mb-4 flex items-center gap-2">
                                        3. Budget
                                        {rfpData.budget ? (
                                            <span className="text-green-600" title="Complete">✓</span>
                                        ) : (
                                            <span className="text-red-500" title="Required">✗</span>
                                        )}
                                    </h3>
                                    {rfpData.budget ? (
                                        <div className="text-2xl font-bold text-slate-900">{rfpData.budget}</div>
                                    ) : (
                                        <span className="inline-block bg-slate-100 text-slate-400 px-3 py-1 rounded text-sm">Pending</span>
                                    )}
                                </section>
                                <section>
                                    <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wide border-b border-slate-200 pb-2 mb-4 flex items-center gap-2">
                                        4. Timeline
                                        {rfpData.timeline.end && rfpData.timeline.end !== 'TBD' ? (
                                            <span className="text-green-600" title="Complete">✓</span>
                                        ) : (
                                            <span className="text-red-500" title="Required">✗</span>
                                        )}
                                    </h3>
                                    <div className="text-sm text-slate-600">
                                        <div className="flex justify-between py-1 border-b border-slate-100"><span>Start:</span> <span>{rfpData.timeline.start}</span></div>
                                        <div className="flex justify-between py-1 border-b border-slate-100"><span>End:</span> <span>{rfpData.timeline.end}</span></div>
                                    </div>
                                </section>
                            </div>

                        </div>
                    </div>
                </div>

            </div>
        </div>
    );
}
