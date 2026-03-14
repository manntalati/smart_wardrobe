"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listItems, getHealth, getImageUrl, type ClothingItem, type ApiResponse, type HealthStatus } from "@/lib/api";

export default function DashboardPage() {
  const [items, setItems] = useState<ClothingItem[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [health, setHealth] = useState<ApiResponse<HealthStatus> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const [itemRes, healthRes] = await Promise.all([
          listItems(1, 50).catch(() => ({ data: [] as ClothingItem[], error: null, meta: { total: 0 } })),
          getHealth().catch(() => null),
        ]);
        setItems(itemRes.data);
        setTotalItems(itemRes.meta.total ?? itemRes.data.length);
        setHealth(healthRes);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const categoryCounts: Record<string, number> = {};
  items.forEach((item) => {
    categoryCounts[item.category] = (categoryCounts[item.category] || 0) + 1;
  });

  const topCategories = Object.entries(categoryCounts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 6);

  return (
    <div className="page-container">
      {/* Hero */}
      <div className="page-header" style={{ textAlign: "center", marginBottom: 48 }}>
        <h1 className="heading-xl">
          Your <span style={{ background: "var(--accent-gradient)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>Smart</span> Wardrobe
        </h1>
        <p style={{ maxWidth: 500, margin: "12px auto 0", fontSize: "1.1rem" }}>
          AI-powered clothing catalog, outfit recommendations, and style insights.
        </p>
      </div>

      {loading ? (
        <div className="loading-container">
          <div className="spinner" />
          <p>Loading your wardrobe...</p>
        </div>
      ) : (
        <>
          {/* Stats */}
          <div className="stats-bar">
            <div className="glass-card stat-card">
              <div className="stat-value">{totalItems}</div>
              <div className="stat-label">Items</div>
            </div>
            <div className="glass-card stat-card">
              <div className="stat-value">{Object.keys(categoryCounts).length}</div>
              <div className="stat-label">Categories</div>
            </div>
            <div className="glass-card stat-card">
              <div className="stat-value">{new Set(items.map((i) => i.color)).size}</div>
              <div className="stat-label">Colors</div>
            </div>
            <div className="glass-card stat-card">
              <div className="stat-value">
                {health?.data?.gemini_configured ? "✅" : "❌"}
              </div>
              <div className="stat-label">Gemini AI</div>
            </div>
          </div>

          {/* Quick Actions */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: 20, marginBottom: 40 }}>
            <Link href="/wardrobe" style={{ textDecoration: "none" }}>
              <div className="glass-card" style={{ padding: 24, cursor: "pointer" }}>
                <div style={{ fontSize: "2rem", marginBottom: 12 }}>📸</div>
                <h3 className="heading-md" style={{ marginBottom: 8, fontFamily: "'Inter', sans-serif" }}>Add Clothes</h3>
                <p className="text-muted">Upload photos of your clothing items. AI will classify them automatically.</p>
              </div>
            </Link>
            <Link href="/outfits" style={{ textDecoration: "none" }}>
              <div className="glass-card" style={{ padding: 24, cursor: "pointer" }}>
                <div style={{ fontSize: "2rem", marginBottom: 12 }}>✨</div>
                <h3 className="heading-md" style={{ marginBottom: 8, fontFamily: "'Inter', sans-serif" }}>Get Outfit Ideas</h3>
                <p className="text-muted">AI-powered recommendations based on weather, occasion, and your style.</p>
              </div>
            </Link>
            <Link href="/shopping" style={{ textDecoration: "none" }}>
              <div className="glass-card" style={{ padding: 24, cursor: "pointer" }}>
                <div style={{ fontSize: "2rem", marginBottom: 12 }}>🛍️</div>
                <h3 className="heading-md" style={{ marginBottom: 8, fontFamily: "'Inter', sans-serif" }}>Shopping Guide</h3>
                <p className="text-muted">Discover what&apos;s missing from your wardrobe and what to buy next.</p>
              </div>
            </Link>
          </div>

          {/* Recent Items */}
          {items.length > 0 && (
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                <h2 className="heading-md">Recent Additions</h2>
                <Link href="/wardrobe" className="btn btn-secondary btn-sm">
                  View All →
                </Link>
              </div>
              <div className="grid-auto">
                {items.slice(0, 4).map((item) => (
                  <div key={item.id} className="glass-card clothing-card">
                    <div className="clothing-card-img">
                      <img src={getImageUrl(item.image_path)} alt={item.name || item.category} />
                    </div>
                    <div className="clothing-card-body">
                      <div className="clothing-card-name">{item.name || `${item.color} ${item.category}`}</div>
                      <div className="clothing-card-tags">
                        <span className="tag">{item.category}</span>
                        <span className="tag tag-neutral">{item.color}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Category Distribution */}
          {topCategories.length > 0 && (
            <div style={{ marginTop: 40 }}>
              <h2 className="heading-md" style={{ marginBottom: 20 }}>Wardrobe Breakdown</h2>
              <div className="glass-card" style={{ padding: 24 }}>
                {topCategories.map(([cat, count]) => (
                  <div key={cat} style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
                    <span style={{ width: 90, fontSize: "0.85rem", color: "var(--text-secondary)", textTransform: "capitalize" }}>{cat}</span>
                    <div style={{ flex: 1, height: 8, background: "var(--border-subtle)", borderRadius: 4, overflow: "hidden" }}>
                      <div
                        style={{
                          height: "100%",
                          width: `${(count / items.length) * 100}%`,
                          background: "var(--accent-gradient)",
                          borderRadius: 4,
                          transition: "width 0.5s ease",
                        }}
                      />
                    </div>
                    <span style={{ fontSize: "0.85rem", fontWeight: 600, minWidth: 24, textAlign: "right" }}>{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {totalItems === 0 && items.length === 0 && (
            <div className="empty-state">
              <div className="empty-state-icon">👗</div>
              <h3>Your wardrobe is empty</h3>
              <p>Start by uploading photos of your clothes. Our AI will classify and catalog them for you.</p>
              <Link href="/wardrobe" className="btn btn-primary" style={{ marginTop: 8 }}>
                📸 Add Your First Item
              </Link>
            </div>
          )}
        </>
      )}
    </div>
  );
}
