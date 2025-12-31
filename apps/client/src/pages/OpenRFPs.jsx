import React, { useState, useMemo } from 'react';
import { Search, Filter, X, Calendar } from 'lucide-react';
import { Link, useSearchParams } from 'react-router-dom';
import { useRFP } from '../context/RFPContext';

export default function OpenRFPs() {
    const { rfps } = useRFP();
    const [searchParams, setSearchParams] = useSearchParams();

    // Initialize filters from URL params or default to 'all'
    const [filterStatus, setFilterStatus] = useState(searchParams.get('status') || 'all');
    const [filterTime, setFilterTime] = useState(searchParams.get('time') || 'all');
    const [searchQuery, setSearchQuery] = useState('');

    // Robust Filter Logic
    const filteredRFPs = rfps.filter(rfp => {
        // 1. Search (Case insensitive, safe access)
        const title = rfp.title ? rfp.title.toLowerCase() : '';
        const id = rfp.id ? rfp.id.toString() : '';
        const query = searchQuery.toLowerCase().trim();

        // Fuzzy-ish match (if query is empty, allow all)
        const matchesSearch = !query || title.includes(query) || id.includes(query);

        // 2. Status Filter
        const rfpStatus = rfp.status?.toLowerCase() || 'open';
        const matchesStatus = filterStatus === 'all' || rfpStatus === filterStatus.toLowerCase();

        // 3. Time Filter
        let matchesTime = true;
        if (filterTime !== 'all' && rfp.created_at) {
            const created = new Date(rfp.created_at);
            const now = new Date();
            const startOfDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());

            switch (filterTime) {
                case 'today':
                    matchesTime = created >= startOfDay;
                    break;
                case 'week': {
                    const firstDayOfWeek = new Date(now.setDate(now.getDate() - now.getDay())); // Sunday
                    firstDayOfWeek.setHours(0, 0, 0, 0);
                    matchesTime = created >= firstDayOfWeek;
                    break;
                }
                case 'month': {
                    const firstDayOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
                    matchesTime = created >= firstDayOfMonth;
                    break;
                }
                case 'year': {
                    const firstDayOfYear = new Date(now.getFullYear(), 0, 1);
                    matchesTime = created >= firstDayOfYear;
                    break;
                }
                default:
                    matchesTime = true;
            }
        }

        return matchesSearch && matchesStatus && matchesTime;
    });

    const clearFilters = () => {
        setSearchQuery('');
        setFilterStatus('all');
        setFilterTime('all');
    };

    const hasFilters = searchQuery !== '' || filterStatus !== 'all' || filterTime !== 'all';

    return (
        <div className="animate-fade-in pb-16">
            <div className="flex justify-between items-center mb-8">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 mb-2">Open RFPs</h1>
                    <p className="text-slate-500">Manage and track your request for proposals.</p>
                </div>
                <Link to="/create-rfp" className="btn btn-primary shadow-md hover:shadow-lg transition-all">
                    + Create New RFP
                </Link>
            </div>

            {/* Filters Toolbar */}
            <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm mb-6 flex flex-wrap gap-4 items-center">

                {/* Search */}
                <div className="flex-1 min-w-[250px] relative">
                    <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                        type="text"
                        placeholder="Search by Title or ID..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-400 transition-all text-sm"
                    />
                    {searchQuery && (
                        <button
                            onClick={() => setSearchQuery('')}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                        >
                            <X size={14} />
                        </button>
                    )}
                </div>

                {/* Divider */}
                <div className="h-8 w-px bg-slate-200 hidden md:block"></div>

                {/* Status Filter */}
                <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-slate-600 flex items-center gap-2">
                        <Filter size={16} /> Status:
                    </span>
                    <select
                        value={filterStatus}
                        onChange={(e) => setFilterStatus(e.target.value)}
                        className="py-2 px-3 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-blue-400 cursor-pointer"
                    >
                        <option value="all">All Statuses</option>
                        <option value="open">Open</option>
                        <option value="closed">Closed</option>
                        <option value="draft">Draft</option>
                    </select>
                </div>

                {/* Time Filter */}
                <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-slate-600 flex items-center gap-2">
                        <Calendar size={16} /> Time:
                    </span>
                    <select
                        value={filterTime}
                        onChange={(e) => setFilterTime(e.target.value)}
                        className="py-2 px-3 bg-slate-50 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-blue-400 cursor-pointer"
                    >
                        <option value="all">All Time</option>
                        <option value="today">Today</option>
                        <option value="week">This Week</option>
                        <option value="month">This Month</option>
                        <option value="year">This Year</option>
                    </select>
                </div>

                {/* Clear Button */}
                {hasFilters && (
                    <button
                        onClick={clearFilters}
                        className="text-sm text-red-500 hover:text-red-700 font-medium ml-auto"
                    >
                        Clear Filters
                    </button>
                )}
            </div>

            {/* Table */}
            <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-slate-50 border-b border-slate-200">
                        <tr>
                            <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-wide">RFP Title</th>
                            <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-wide">Due Date</th>
                            <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-wide">Proposals</th>
                            <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-wide">Status</th>
                            <th className="p-4 text-xs font-bold text-slate-500 uppercase tracking-wide text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                        {filteredRFPs.length === 0 ? (
                            <tr>
                                <td colSpan="5" className="p-12 text-center">
                                    <div className="text-slate-400 mb-2">No RFPs found</div>
                                    <p className="text-sm text-slate-500">Try adjusting your search or filters.</p>
                                </td>
                            </tr>
                        ) : filteredRFPs.map(rfp => (
                            <tr key={rfp.id} className="hover:bg-blue-50/50 transition-colors group">
                                <td className="p-4">
                                    <Link
                                        to={rfp.status === 'draft' ? `/create-rfp/${rfp.id}` : `/rfp/${rfp.id}`}
                                        className="font-bold text-slate-800 hover:text-blue-600 transition-colors block mb-1"
                                    >
                                        {rfp.title}
                                    </Link>
                                    <span className="text-xs text-slate-400 font-mono">ID: {rfp.id.substring(0, 8)}</span>
                                </td>
                                <td className="p-4 text-slate-600 text-sm">{rfp.due}</td>
                                <td className="p-4">
                                    <div className="flex items-center gap-2">
                                        <div className="h-1.5 w-16 bg-slate-100 rounded-full overflow-hidden">
                                            <div className="h-full bg-blue-500" style={{ width: `${Math.min((rfp.proposals || 0) * 20, 100)}%` }}></div>
                                        </div>
                                        <span className="text-xs font-medium text-slate-600">{rfp.proposals}</span>
                                    </div>
                                </td>
                                <td className="p-4">
                                    <span className={`px-2.5 py-1 rounded-full text-xs font-bold border ${rfp.status === 'open' ? 'bg-green-100 text-green-700 border-green-200' :
                                        rfp.status === 'closed' ? 'bg-slate-100 text-slate-700 border-slate-200' :
                                            'bg-amber-100 text-amber-700 border-amber-200'
                                        }`}>
                                        {rfp.status ? rfp.status.toUpperCase() : 'UNKNOWN'}
                                    </span>
                                </td>
                                <td className="p-4 text-right">
                                    <Link
                                        to={rfp.status === 'draft' ? `/create-rfp/${rfp.id}` : `/rfp/${rfp.id}`}
                                        className="btn btn-secondary text-xs py-1.5 px-3 opacity-0 group-hover:opacity-100 transition-opacity"
                                    >
                                        {rfp.status === 'draft' ? 'Edit Draft' : 'Manage'}
                                    </Link>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>

                <div className="bg-slate-50 p-3 border-t border-slate-200 text-xs text-slate-500 text-center">
                    Showing {filteredRFPs.length} of {rfps.length} RFPs
                </div>
            </div>
        </div>
    );
}
