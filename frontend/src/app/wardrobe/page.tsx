"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
    listItems,
    uploadItem,
    deleteItem,
    getImageUrl,
    type ClothingItem,
} from "@/lib/api";

export default function WardrobePage() {
    const [items, setItems] = useState<ClothingItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [showUpload, setShowUpload] = useState(false);
    const [filter, setFilter] = useState({ category: "", color: "" });

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
        loadItems();
    }, [loadItems]);

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
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                        <h1 className="heading-lg">My Wardrobe</h1>
                        <p>Upload and manage your clothing catalog. AI classifies each item automatically.</p>
                    </div>
                    <button className="btn btn-primary" onClick={() => setShowUpload(true)}>
                        📸 Add Item
                    </button>
                </div>
            </div>

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
                    <div className="empty-state-icon">📸</div>
                    <h3>No items yet</h3>
                    <p>Upload your first clothing item and our AI will classify it automatically.</p>
                    <button className="btn btn-primary" onClick={() => setShowUpload(true)} style={{ marginTop: 8 }}>
                        Add Your First Item
                    </button>
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
                                    {item.pattern && item.pattern !== "solid" && (
                                        <span className="tag tag-neutral">{item.pattern}</span>
                                    )}
                                </div>
                                <div className="clothing-card-tags" style={{ marginTop: 4 }}>
                                    <span className="tag tag-neutral">{item.fabric}</span>
                                    <span className="tag tag-neutral">{item.season}</span>
                                </div>
                                {item.confidence && (
                                    <div className="clothing-card-confidence">
                                        <span>AI: {Math.round(item.confidence * 100)}%</span>
                                        <div className="confidence-bar">
                                            <div
                                                className="confidence-fill"
                                                style={{ width: `${item.confidence * 100}%` }}
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
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

// ─── Upload Modal Component ─────────────────────────────────────────────

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
                            <p className="text-xs text-muted">JPG, PNG, WebP — max 10MB</p>
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
                                {uploading && (
                                    <p className="text-xs text-muted" style={{ textAlign: "center" }}>
                                        AI is analyzing your item — this may take a moment on first run
                                    </p>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
