"use client";

import { useEffect, useState } from "react";
import {
    getShoppingSuggestions,
    type ShoppingResponse,
    type ShoppingSuggestion,
} from "@/lib/api";

const OCCASIONS = [
    { value: "", label: "All / General" },
    { value: "casual", label: "Casual" },
    { value: "work", label: "Work" },
    { value: "formal", label: "Formal" },
    { value: "outerwear", label: "Outerwear" },
    { value: "versatile", label: "Versatile" },
];

export default function ShoppingPage() {
    const [occasion, setOccasion] = useState("");
    const [data, setData] = useState<ShoppingResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    const handleAnalyze = async () => {
        setLoading(true);
        setError("");
        try {
            const result = await getShoppingSuggestions(occasion || undefined);
            setData(result);
        } catch {
            setError("Failed to analyze wardrobe. Is the backend running?");
        } finally {
            setLoading(false);
        }
    };

    // Auto-load on mount
    useEffect(() => {
        handleAnalyze();
    }, []);

    return (
        <div className="page-container">
            <div className="page-header">
                <h1 className="heading-lg">Shopping Guide</h1>
                <p>Discover gaps in your wardrobe and get personalized shopping recommendations.</p>
            </div>

            {/* Controls */}
            <div className="glass-card" style={{ padding: 24, marginBottom: 24 }}>
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
                    <div className="form-group" style={{ flex: 1, minWidth: 200 }}>
                        <label className="form-label">Focus Area</label>
                        <select
                            className="select"
                            value={occasion}
                            onChange={(e) => setOccasion(e.target.value)}
                        >
                            {OCCASIONS.map((occ) => (
                                <option key={occ.value} value={occ.value}>{occ.label}</option>
                            ))}
                        </select>
                    </div>
                    <button
                        className="btn btn-primary"
                        onClick={handleAnalyze}
                        disabled={loading}
                        style={{ height: 46 }}
                    >
                        {loading ? (
                            <>
                                <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                                Analyzing...
                            </>
                        ) : (
                            "🔍 Analyze Wardrobe"
                        )}
                    </button>
                </div>
            </div>

            {error && (
                <div className="glass-card" style={{ padding: 20, marginBottom: 24, textAlign: "center" }}>
                    <p style={{ color: "#f07070" }}>{error}</p>
                </div>
            )}

            {data && (
                <>
                    {/* Analysis Stats */}
                    {data.analysis && data.analysis.total_items > 0 && (
                        <div className="stats-bar" style={{ marginBottom: 24 }}>
                            <div className="glass-card stat-card">
                                <div className="stat-value">{data.analysis.total_items}</div>
                                <div className="stat-label">Total Items</div>
                            </div>
                            <div className="glass-card stat-card">
                                <div className="stat-value">{Object.keys(data.analysis.categories || {}).length}</div>
                                <div className="stat-label">Categories</div>
                            </div>
                            <div className="glass-card stat-card">
                                <div className="stat-value">{Object.keys(data.analysis.colors || {}).length}</div>
                                <div className="stat-label">Colors</div>
                            </div>
                            <div className="glass-card stat-card">
                                <div className="stat-value">{Object.keys(data.analysis.seasons || {}).length}</div>
                                <div className="stat-label">Seasons</div>
                            </div>
                        </div>
                    )}

                    {/* Gaps */}
                    {data.gaps.length > 0 && (
                        <div style={{ marginBottom: 32 }}>
                            <h2 className="heading-md" style={{ marginBottom: 16 }}>Identified Gaps</h2>
                            <div className="glass-card" style={{ padding: 20 }}>
                                {data.gaps.map((gap, idx) => (
                                    <div
                                        key={idx}
                                        style={{
                                            display: "flex",
                                            alignItems: "center",
                                            gap: 12,
                                            padding: "10px 0",
                                            borderBottom: idx < data.gaps.length - 1 ? "1px solid var(--border-subtle)" : "none",
                                        }}
                                    >
                                        <span style={{ fontSize: "1.1rem" }}>
                                            {gap.includes("Missing") ? "⚠️" : gap.includes("No ") ? "📝" : "💡"}
                                        </span>
                                        <span style={{ fontSize: "0.9rem" }}>{gap}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Shopping Suggestions */}
                    {data.suggestions.length > 0 && (
                        <div>
                            <h2 className="heading-md" style={{ marginBottom: 16 }}>Recommended Purchases</h2>
                            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 16 }}>
                                {data.suggestions.map((suggestion, idx) => (
                                    <ShoppingCard key={idx} suggestion={suggestion} />
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Message for empty wardrobe */}
                    {data.analysis?.message && (
                        <div className="empty-state">
                            <div className="empty-state-icon">🛍️</div>
                            <h3>{data.analysis.message}</h3>
                        </div>
                    )}
                </>
            )}

            {!data && !loading && !error && (
                <div className="loading-container">
                    <div className="spinner" />
                    <p>Loading analysis...</p>
                </div>
            )}
        </div>
    );
}

function ShoppingCard({ suggestion }: { suggestion: ShoppingSuggestion }) {
    const priorityClass =
        suggestion.priority === "high"
            ? "priority-high"
            : suggestion.priority === "medium"
                ? "priority-medium"
                : "priority-low";

    return (
        <div className="glass-card shopping-card">
            <div className="shopping-card-header">
                <h3>{suggestion.item}</h3>
                <span className={`shopping-priority ${priorityClass}`}>{suggestion.priority}</span>
            </div>
            <p className="shopping-card-reason">{suggestion.reason}</p>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span className="tag tag-neutral">{suggestion.category}</span>
                <span className="shopping-card-price">{suggestion.estimated_price_range}</span>
            </div>
        </div>
    );
}
