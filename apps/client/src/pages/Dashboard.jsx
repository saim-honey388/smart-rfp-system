import React from 'react';
import { FileText, Files, BarChart2, Plus, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useRFP } from '../context/RFPContext';

export default function Dashboard() {
    const { rfps } = useRFP();

    // Computed KPIs
    const openCount = rfps.filter(r => r.status === 'open').length;
    const draftCount = rfps.filter(r => r.status === 'draft').length;

    // Helper for "Time Ago"
    const timeAgo = (dateString) => {
        if (!dateString) return 'Just now';

        // Ensure we treat the date as UTC if it comes without timezone info (naive from backend)
        const dateStr = dateString.endsWith('Z') || dateString.includes('+') ? dateString : dateString + 'Z';
        const date = new Date(dateStr);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);

        let interval = seconds / 31536000;
        if (interval > 1) return Math.floor(interval) + " years ago";
        interval = seconds / 2592000;
        if (interval > 1) return Math.floor(interval) + " months ago";
        interval = seconds / 86400;
        if (interval > 1) return Math.floor(interval) + " days ago";
        interval = seconds / 3600;
        if (interval > 1) return Math.floor(interval) + " hours ago";
        interval = seconds / 60;
        if (interval > 1) return Math.floor(interval) + " minutes ago";
        return Math.floor(seconds) + " seconds ago";
    };

    // Sorted RFPs for Recent Activity
    const recentActivity = [...rfps].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 5);

    const kpis = [
        { label: 'Open RFPs', value: openCount, icon: <FileText className="text-blue-600" size={24} />, color: 'bg-blue-100', link: '/open-rfps?status=open' },
        { label: 'Drafts', value: draftCount, icon: <Files className="text-amber-600" size={24} />, color: 'bg-amber-100', link: '/open-rfps?status=draft' },
        { label: 'Saved Comparisons', value: rfps.filter(r => r.proposals > 0).length, icon: <BarChart2 className="text-teal-600" size={24} />, color: 'bg-teal-100', link: '/comparisons' },
    ];

    return (
        <div className="animate-fade-in">
            <h1 style={{ fontSize: '1.875rem', fontWeight: '700', marginBottom: '1.5rem', color: 'var(--text-main)' }}>Dashboard</h1>

            {/* KPIs */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                {kpis.map((kpi, idx) => (
                    <Link key={idx} to={kpi.link} className="card hover:shadow-lg transition-shadow" style={{ display: 'flex', alignItems: 'center', gap: '1rem', textDecoration: 'none' }}>
                        <div style={{ padding: '1rem', borderRadius: '12px', background: kpi.color.replace('bg-', 'var(--').replace('-100', '-light)') }}>
                            <div style={{
                                width: 48, height: 48, borderRadius: 12,
                                backgroundColor: idx === 0 ? '#dbeafe' : idx === 1 ? '#fef3c7' : '#ccfbf1',
                                display: 'flex', alignItems: 'center', justifyContent: 'center'
                            }}>
                                {kpi.icon}
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', fontWeight: '500' }}>{kpi.label}</div>
                            <div style={{ fontSize: '1.875rem', fontWeight: '700', color: 'var(--text-main)' }}>{kpi.value}</div>
                        </div>
                    </Link>
                ))}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem' }}>

                {/* Recent Activity */}
                <section className="card">
                    <h3 style={{ marginBottom: '1rem', borderBottom: '1px solid var(--border-light)', paddingBottom: '0.75rem' }}>Recent Activity</h3>
                    <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                        {recentActivity.length === 0 ? (
                            <li className="text-slate-400 italic">No recent activity.</li>
                        ) : (
                            recentActivity.map(rfp => (
                                <li key={rfp.id} style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', alignItems: 'flex-start' }}>
                                    <div
                                        className={`mt-1 w-3 h-3 rounded-full flex-shrink-0 animate-pulse ${rfp.status === 'draft'
                                                ? 'bg-amber-500 ring-4 ring-amber-100'
                                                : 'bg-emerald-500 ring-4 ring-emerald-100'
                                            }`}
                                    ></div>
                                    <div>
                                        <div style={{ fontWeight: '500' }}>
                                            {rfp.status === 'draft' ? 'Draft Saved: ' : 'RFP Created: '}
                                            {rfp.title}
                                        </div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                            {timeAgo(rfp.created_at)}
                                        </div>
                                    </div>
                                </li>
                            ))
                        )}
                    </ul>
                </section>

                {/* Quick Actions */}
                <section className="card">
                    <h3 style={{ marginBottom: '1rem' }}>Quick Actions</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        <Link to="/create-rfp" className="btn btn-primary" style={{ justifyContent: 'center', textDecoration: 'none' }}>
                            <Plus size={18} /> Create New RFP
                        </Link>
                        <Link to="/open-rfps?status=open" className="btn btn-secondary" style={{ justifyContent: 'center', textDecoration: 'none' }}>
                            View Open RFPs <ArrowRight size={16} />
                        </Link>
                    </div>
                </section>
            </div>
        </div>
    );
}
