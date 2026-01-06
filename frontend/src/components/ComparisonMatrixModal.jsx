import React, { useEffect, useState } from 'react';
import { X, Download, FileText } from 'lucide-react';

export default function ComparisonMatrixModal({ rfpId, isOpen, onClose }) {
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);

    useEffect(() => {
        if (isOpen && rfpId) {
            fetchMatrix();
        }
    }, [isOpen, rfpId]);

    const fetchMatrix = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await fetch(`http://localhost:8000/api/proposals/${rfpId}/matrix`);
            if (!res.ok) throw new Error("Failed to load matrix");
            const json = await res.json();
            setData(json);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const downloadCSV = () => {
        if (!data) return;

        const fixedColumns = data.fixed_columns || [];
        const vendorColumns = data.vendor_columns || [];

        // Headers: Fixed columns + Vendor columns per proposal
        const headers = [...fixedColumns];
        data.proposals.forEach(p => {
            vendorColumns.forEach(col => {
                headers.push(`${p.vendor} ${col}`);
            });
        });

        const rows = [headers];

        data.rows.forEach(row => {
            const csvRow = [];

            // Fixed column values
            fixedColumns.forEach(col => {
                const val = row.fixed_values?.[col] || '';
                csvRow.push(`"${String(val).replace(/"/g, '""')}"`);
            });

            // Vendor column values
            data.proposals.forEach(p => {
                const vendorVals = row.vendor_values?.[p.id] || {};
                vendorColumns.forEach(col => {
                    csvRow.push(vendorVals[col] || '');
                });
            });

            rows.push(csvRow);
        });

        const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.join(",")).join("\n");
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `Comparison_Matrix_${rfpId}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    };

    // Helper to format column name for display
    const formatColumnName = (col) => {
        return col.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
    };

    if (!isOpen) return null;

    const fixedColumns = data?.fixed_columns || [];
    const vendorColumns = data?.vendor_columns || [];

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-8 animate-fade-in">
            <div className="bg-white rounded-2xl shadow-2xl w-full max-w-7xl h-full max-h-[90vh] flex flex-col overflow-hidden">
                {/* Header */}
                <div className="p-6 border-b border-slate-200 flex justify-between items-center bg-slate-50">
                    <div>
                        <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
                            <FileText className="text-blue-600" />
                            Proposal Comparison Matrix
                        </h2>
                        {data && <p className="text-slate-500 text-sm mt-1">{data.rfp_title} • {data.proposals.length} Proposals</p>}
                    </div>
                    <div className="flex gap-4">
                        <button
                            onClick={downloadCSV}
                            disabled={!data}
                            className="btn bg-white border border-slate-300 text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                        >
                            <Download size={18} /> Download CSV
                        </button>
                        <button onClick={onClose} className="p-2 hover:bg-slate-200 rounded-full text-slate-500 transition-colors">
                            <X size={24} />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-auto bg-slate-100 p-6">
                    {loading ? (
                        <div className="flex items-center justify-center h-full">
                            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                        </div>
                    ) : error ? (
                        <div className="text-red-500 text-center p-8 bg-red-50 rounded-lg">{error}</div>
                    ) : data && data.rows.length > 0 ? (
                        <div className="bg-white border border-slate-300 shadow-sm rounded-lg overflow-hidden">
                            <table className="w-full text-sm text-left border-collapse">
                                <thead className="bg-slate-800 text-slate-200 sticky top-0 z-10 shadow-md">
                                    <tr>
                                        {/* Fixed columns header */}
                                        {fixedColumns.map((col, idx) => (
                                            <th key={`fixed-${idx}`} className={`px-4 py-3 border-r border-slate-600 ${idx === 0 ? 'w-20' : ''}`}>
                                                {formatColumnName(col)}
                                            </th>
                                        ))}
                                        {/* Vendor headers */}
                                        {data.proposals.map(p => (
                                            <th key={p.id} colSpan={vendorColumns.length} className="px-4 py-3 border-r border-slate-600 text-center min-w-[180px]">
                                                <div className="font-bold text-white mb-1">{p.vendor}</div>
                                                <div className={`text-[10px] uppercase px-2 py-0.5 rounded-full inline-block ${p.status === 'Accepted' ? 'bg-green-500 text-white' :
                                                    p.status === 'Rejected' ? 'bg-red-500 text-white' : 'bg-slate-600'
                                                    }`}>
                                                    {p.status}
                                                </div>
                                            </th>
                                        ))}
                                    </tr>
                                    {/* Vendor column sub-headers */}
                                    {vendorColumns.length > 0 && (
                                        <tr className="bg-slate-700 text-xs uppercase text-slate-300">
                                            <th className="px-4 py-1 border-r border-slate-600" colSpan={fixedColumns.length}></th>
                                            {data.proposals.map(p => (
                                                <React.Fragment key={p.id}>
                                                    {vendorColumns.map((col, colIdx) => (
                                                        <th key={`${p.id}-${colIdx}`} className="px-2 py-1 border-r border-slate-600 text-right w-24">
                                                            {formatColumnName(col)}
                                                        </th>
                                                    ))}
                                                </React.Fragment>
                                            ))}
                                        </tr>
                                    )}
                                </thead>
                                <tbody className="divide-y divide-slate-200 bg-white">
                                    {data.rows.map((row, idx) => {
                                        // Get section from fixed_values
                                        const section = row.fixed_values?.section;
                                        const prevSection = idx > 0 ? data.rows[idx - 1].fixed_values?.section : null;
                                        const showSection = section && section !== prevSection;
                                        const isGrandTotal = row.is_grand_total;

                                        return (
                                            <React.Fragment key={idx}>
                                                {showSection && (
                                                    <tr className="bg-slate-100 border-b border-slate-300">
                                                        <td colSpan={100} className="px-4 py-2 font-bold text-slate-800 text-xs uppercase tracking-wider sticky left-0">
                                                            {section}
                                                        </td>
                                                    </tr>
                                                )}
                                                <tr className={`transition-colors group ${isGrandTotal ? 'bg-slate-800 text-white font-bold sticky bottom-0' : 'hover:bg-blue-50'}`}>
                                                    {/* Fixed column cells */}
                                                    {fixedColumns.map((col, colIdx) => {
                                                        const value = row.fixed_values?.[col] || '';
                                                        const isDescCol = col.toLowerCase().includes('desc');
                                                        const isItemCol = col.toLowerCase().includes('item');

                                                        return (
                                                            <td
                                                                key={`fixed-${colIdx}`}
                                                                className={`px-4 py-2 border-r ${isGrandTotal
                                                                    ? 'border-slate-600 text-white' + (isDescCol ? ' text-lg' : '')
                                                                    : isDescCol
                                                                        ? 'border-slate-200 text-slate-700 truncate max-w-xs'
                                                                        : 'border-slate-200 font-mono text-slate-600 bg-slate-50/50'}`}
                                                                title={isDescCol ? value : undefined}
                                                            >
                                                                {isGrandTotal && isItemCol ? '' : value}
                                                            </td>
                                                        );
                                                    })}

                                                    {/* Vendor columns */}
                                                    {data.proposals.map(p => {
                                                        const vendorVals = row.vendor_values?.[p.id] || {};
                                                        return (
                                                            <React.Fragment key={p.id}>
                                                                {vendorColumns.map((col, colIdx) => {
                                                                    const isTotalCol = col.toLowerCase().includes('total');
                                                                    const cellValue = vendorVals[col] || '-';
                                                                    const isNotQuoted = cellValue === 'Not Quoted';

                                                                    return (
                                                                        <td
                                                                            key={`${p.id}-${colIdx}`}
                                                                            className={`px-2 py-2 border-r text-right ${isGrandTotal
                                                                                ? `border-slate-600 ${isTotalCol ? 'text-green-400 text-lg' : ''}`
                                                                                : isNotQuoted
                                                                                    ? 'border-slate-200 text-red-400 italic text-xs'
                                                                                    : `border-slate-200 ${isTotalCol ? 'font-medium text-slate-900 bg-slate-50/30' : 'text-slate-600 text-sm'}`
                                                                                }`}
                                                                        >
                                                                            {cellValue}
                                                                        </td>
                                                                    );
                                                                })}
                                                            </React.Fragment>
                                                        );
                                                    })}
                                                </tr>
                                            </React.Fragment>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-slate-400">
                            <FileText size={48} className="mb-4 text-slate-300" />
                            <p>No compatible comparison data available.</p>
                            {data?.message && <p className="text-sm mt-2">{data.message}</p>}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

