"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
    listItems,
    uploadItem,
    deleteItem,
    getImageUrl,
    searchImages,
    addItemFromUrl,
    type ClothingItem,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function WardrobePage() {
    const { user } = useAuth();
    const [activeTab, setActiveTab] = useState<"wardrobe" | "search">("wardrobe");

    // Wardrobe State
    const [items, setItems] = useState<ClothingItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [showUpload, setShowUpload] = useState(false);
    const [filter, setFilter] = useState({ category: "", color: "" });

    // Search State
    const [query, setQuery] = useState("");
    const [searchResults, setSearchResults] = useState<string[]>([]);
    const [searching, setSearching] = useState(false);
    const [addingUrl, setAddingUrl] = useState<string | null>(null);

    const loadItems = useCallback(async () => {
        try {
            const data = await listItems();
            setItems(data.items);
        } catch {
            console.error("Failed to load items");
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        if (user) loadItems();
    }, [user, loadItems]);

    const handleDelete = async (id: number) => {
        if (!confirm("Remove this item from your wardrobe?")) return;
        try {
            await deleteItem(id);
            setItems((prev) => prev.filter((item) => item.id !== id));
        } catch {
            alert("Failed to delete item");
        }
    };

    const handleUploadComplete = () => {
        setShowUpload(false);
        loadItems();
    };

    const handleSearch = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!query.trim()) return;
        setSearching(true);
        try {
            const data = await searchImages(query);
            setSearchResults(data.images);
        } catch (err) {
            alert("Search failed. Please try again.");
        } finally {
            setSearching(false);
        }
    };

    const handleAddFromSearch = async (imageUrl: string) => {
        setAddingUrl(imageUrl);
        try {
            await addItemFromUrl(imageUrl);
            alert("Item added to wardrobe!");
            loadItems();
            // Optional: Switch back to wardrobe tab?
        } catch (err) {
            alert("Failed to add item. Try another image.");
        } finally {
            setAddingUrl(null);
        }
    };

    // Filter items
    const categories = [...new Set(items.map((i) => i.category))].sort();
    const colors = [...new Set(items.map((i) => i.color))].sort();
    const filtered = items.filter((item) => {
        if (filter.category && item.category !== filter.category) return false;
        if (filter.color && item.color !== filter.color) return false;
        return true;
    });

    return (
        <div className="page-container">
            <div className="page-header">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 16 }}>
                    <div>
                        <h1 className="heading-lg">My Wardrobe</h1>
                        <p>Manage your collection or discover new items.</p>
                    </div>

                    <div style={{ display: "flex", gap: 10 }}>
                        <div className="tab-group" style={{ background: "var(--bg-glass)", padding: 4, borderRadius: 8, display: "flex" }}>
                            <button
                                className={`btn btn-sm ${activeTab === "wardrobe" ? "btn-primary" : "btn-ghost"}`}
                                onClick={() => setActiveTab("wardrobe")}
                                style={{ borderRadius: 6 }}
                            >
                                👔 Your Items
                            </button>
                            <button
                                className={`btn btn-sm ${activeTab === "search" ? "btn-primary" : "btn-ghost"}`}
                                onClick={() => setActiveTab("search")}
                                style={{ borderRadius: 6 }}
                            >
                                🔍 Search & Add
                            </button>
                        </div>
                        {activeTab === "wardrobe" && (
                            <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
                                📸 Upload
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {activeTab === "wardrobe" ? (
                <>
                    {/* Filters */}
                    {items.length > 0 && (
                        <div className="filter-bar">
                            <div className="form-group">
                                <label className="form-label">Category</label>
                                <select
                                    className="select"
                                    value={filter.category}
                                    onChange={(e) => setFilter((f) => ({ ...f, category: e.target.value }))}
                                >
                                    <option value="">All Categories</option>
                                    {categories.map((c) => (
                                        <option key={c} value={c}>{c}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="form-group">
                                <label className="form-label">Color</label>
                                <select
                                    className="select"
                                    value={filter.color}
                                    onChange={(e) => setFilter((f) => ({ ...f, color: e.target.value }))}
                                >
                                    <option value="">All Colors</option>
                                    {colors.map((c) => (
                                        <option key={c} value={c}>{c}</option>
                                    ))}
                                </select>
                            </div>
                            <div style={{ display: "flex", alignItems: "flex-end" }}>
                                <span className="text-sm text-muted" style={{ paddingBottom: 12 }}>
                                    {filtered.length} item{filtered.length !== 1 ? "s" : ""}
                                </span>
                            </div>
                        </div>
                    )}

                    {loading ? (
                        <div className="loading-container">
                            <div className="spinner" />
                            <p>Loading wardrobe...</p>
                        </div>
                    ) : items.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-state-icon">👔</div>
                            <h3>Wardrobe is empty</h3>
                            <p>Upload clothes or use the Search tab to find items online.</p>
                        </div>
                    ) : (
                        <div className="grid-auto">
                            {filtered.map((item) => (
                                <div key={item.id} className="glass-card clothing-card">
                                    <div className="clothing-card-img">
                                        <img src={getImageUrl(item.image_path)} alt={item.name || item.category} />
                                        <div className="clothing-card-actions">
                                            <button
                                                className="btn btn-danger btn-icon"
                                                onClick={() => handleDelete(item.id)}
                                                title="Remove"
                                            >
                                                ✕
                                            </button>
                                        </div>
                                    </div>
                                    <div className="clothing-card-body">
                                        <div className="clothing-card-name">
                                            {item.name || `${item.color} ${item.category}`}
                                        </div>
                                        <div className="clothing-card-tags">
                                            <span className="tag">{item.category}</span>
                                            <span className="tag tag-neutral">{item.color}</span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </>
            ) : (
                <div className="search-section">
                    <form onSubmit={handleSearch} style={{ display: "flex", gap: 10, maxWidth: 600, margin: "0 auto 40px" }}>
                        <input
                            className="input"
                            placeholder="Search for items (e.g. 'red cocktail dress', 'navy blazer')..."
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                        />
                        <button type="submit" className="btn btn-primary" disabled={searching}>
                            {searching ? "Searching..." : "Search"}
                        </button>
                    </form>

                    {searchResults.length > 0 && (
                        <div className="grid-auto">
                            {searchResults.map((url, i) => (
                                <div key={i} className="glass-card clothing-card" onClick={() => !addingUrl && handleAddFromSearch(url)} style={{ cursor: "pointer" }}>
                                    <div className="clothing-card-img">
                                        <img src={url} alt="Result" />
                                        {addingUrl === url ? (
                                            <div style={{ position: "absolute", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", color: "white" }}>
                                                <div className="spinner" style={{ width: 24, height: 24, borderTopColor: "white" }} />
                                                <span style={{ marginLeft: 8 }}>Adding...</span>
                                            </div>
                                        ) : (
                                            <div className="clothing-card-actions" style={{ opacity: 1, top: "unset", bottom: 10, right: 10 }}>
                                                <button className="btn btn-primary btn-sm">
                                                    + Add
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Upload Modal */}
            {showUpload && (
                <UploadModal
                    onClose={() => setShowUpload(false)}
                    onComplete={handleUploadComplete}
                />
            )}
        </div>
    );
}

// ─── Reuse Upload Modal (Same as before) ─────────────────────────────────────────────
function UploadModal({
    onClose,
    onComplete,
}: {
    onClose: () => void;
    onComplete: () => void;
}) {
    const [file, setFile] = useState<File | null>(null);
    const [preview, setPreview] = useState<string>("");
    const [name, setName] = useState("");
    const [uploading, setUploading] = useState(false);
    const [result, setResult] = useState<Record<string, unknown> | null>(null);
    const [error, setError] = useState("");
    const [dragover, setDragover] = useState(false);
    const fileRef = useRef<HTMLInputElement>(null);

    const handleFile = (f: File) => {
        setFile(f);
        setPreview(URL.createObjectURL(f));
        setResult(null);
        setError("");
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setDragover(false);
        const f = e.dataTransfer.files[0];
        if (f && f.type.startsWith("image/")) handleFile(f);
    };

    const handleUpload = async () => {
        if (!file) return;
        setUploading(true);
        setError("");
        try {
            const data = await uploadItem(file, name || undefined);
            setResult(data.classification);
            setTimeout(onComplete, 1500);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Upload failed");
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
            <div className="modal-content">
                <div className="modal-header">
                    <h2>Add New Item</h2>
                    <button className="btn btn-icon btn-secondary" onClick={onClose}>✕</button>
                </div>
                <div className="modal-body">
                    {!file ? (
                        <div
                            className={`upload-zone ${dragover ? "dragover" : ""}`}
                            onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
                            onDragLeave={() => setDragover(false)}
                            onDrop={handleDrop}
                            onClick={() => fileRef.current?.click()}
                        >
                            <div className="upload-zone-icon">📷</div>
                            <p><strong>Click or drag</strong> to upload a photo</p>
                            <button className="btn btn-secondary btn-sm" style={{ marginTop: 10 }} onClick={(e) => { e.stopPropagation(); fileRef.current?.click(); }}>Select File</button>
                            <input
                                ref={fileRef}
                                type="file"
                                accept="image/*"
                                style={{ display: "none" }}
                                onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
                            />
                        </div>
                    ) : result ? (
                        <div style={{ textAlign: "center", padding: 20 }}>
                            <div style={{ fontSize: "3rem", marginBottom: 12 }}>✅</div>
                            <h3 style={{ fontFamily: "'Inter', sans-serif", marginBottom: 8 }}>Item Added!</h3>
                            <p className="text-muted text-sm">
                                Classified as: <strong>{String(result.category)}</strong> — {String(result.color)}, {String(result.pattern)}
                            </p>
                        </div>
                    ) : (
                        <div className="upload-preview">
                            <div className="upload-preview-img">
                                <img src={preview} alt="Preview" />
                            </div>
                            <div className="upload-preview-form">
                                <div className="form-group">
                                    <label className="form-label">Name (optional)</label>
                                    <input
                                        className="input"
                                        type="text"
                                        placeholder="e.g., Favorite blue shirt"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        disabled={uploading}
                                    />
                                </div>
                                {error && (
                                    <p style={{ color: "#f07070", fontSize: "0.85rem" }}>{error}</p>
                                )}
                                <div style={{ display: "flex", gap: 10 }}>
                                    <button className="btn btn-secondary" onClick={() => { setFile(null); setPreview(""); }} disabled={uploading}>
                                        Change
                                    </button>
                                    <button className="btn btn-primary" onClick={handleUpload} disabled={uploading} style={{ flex: 1 }}>
                                        {uploading ? (
                                            <>
                                                <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                                                Classifying...
                                            </>
                                        ) : (
                                            "🤖 Upload & Classify"
                                        )}
                                    </button>
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
