"use client";

import { useEffect, useState } from "react";
import {
    getRecommendations,
    listItems,
    getImageUrl,
    type OutfitSuggestion,
    type WeatherData,
    type ClothingItem,
} from "@/lib/api";

const OCCASIONS = [
    { value: "casual", label: "Casual", icon: "😎" },
    { value: "work", label: "Work", icon: "💼" },
    { value: "formal", label: "Formal", icon: "🎩" },
    { value: "party", label: "Party", icon: "🎉" },
    { value: "outdoor", label: "Outdoor", icon: "🌲" },
    { value: "athletic", label: "Athletic", icon: "🏃" },
];

export default function OutfitsPage() {
    const [occasion, setOccasion] = useState("casual");
    const [city, setCity] = useState("");
    const [style, setStyle] = useState("");
    const [outfits, setOutfits] = useState<OutfitSuggestion[]>([]);
    const [weather, setWeather] = useState<WeatherData | null>(null);
    const [items, setItems] = useState<ClothingItem[]>([]);
    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState("");
    const [hasLoaded, setHasLoaded] = useState(false);

    // Load wardrobe items for rendering outfit thumbnails
    useEffect(() => {
        listItems()
            .then((data) => setItems(data.items))
            .catch(() => { });
    }, []);

    const getItemById = (id: number) => items.find((item) => item.id === id);

    const handleGenerate = async () => {
        setLoading(true);
        setMessage("");
        try {
            const result = await getRecommendations(occasion, city || undefined, 3, style || undefined);
            setOutfits(result.outfits || []);
            setWeather(result.weather || null);
            setMessage(result.message || "");
            setHasLoaded(true);
        } catch {
            setMessage("Failed to get recommendations. Is the backend running?");
        } finally {
            setLoading(false);
        }
    };

    const getWeatherIcon = (main: string) => {
        const icons: Record<string, string> = {
            Clear: "☀️", Clouds: "☁️", Rain: "🌧️", Drizzle: "🌦️",
            Thunderstorm: "⛈️", Snow: "🌨️", Mist: "🌫️", Fog: "🌫️",
        };
        return icons[main] || "🌤️";
    };

    return (
        <div className="page-container">
            <div className="page-header">
                <h1 className="heading-lg">Outfit Recommendations</h1>
                <p>Get AI-powered outfit suggestions tailored to your wardrobe, weather, and occasion.</p>
            </div>

            {/* Controls */}
            <div className="glass-card" style={{ padding: 24, marginBottom: 24 }}>
                {/* Occasion Selector */}
                <div style={{ marginBottom: 20 }}>
                    <label className="form-label" style={{ marginBottom: 10, display: "block" }}>Occasion</label>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                        {OCCASIONS.map((occ) => (
                            <button
                                key={occ.value}
                                className={`btn ${occasion === occ.value ? "btn-primary" : "btn-secondary"} btn-sm`}
                                onClick={() => setOccasion(occ.value)}
                            >
                                {occ.icon} {occ.label}
                            </button>
                        ))}
                    </div>
                </div>

                <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "flex-end" }}>
                    <div className="form-group" style={{ flex: 1, minWidth: 180 }}>
                        <label className="form-label">City (for weather)</label>
                        <input
                            className="input"
                            type="text"
                            placeholder="e.g., New York"
                            value={city}
                            onChange={(e) => setCity(e.target.value)}
                        />
                    </div>
                    <div className="form-group" style={{ flex: 1, minWidth: 180 }}>
                        <label className="form-label">Style Preference</label>
                        <input
                            className="input"
                            type="text"
                            placeholder="e.g., minimalist, streetwear"
                            value={style}
                            onChange={(e) => setStyle(e.target.value)}
                        />
                    </div>
                    <button
                        className="btn btn-primary"
                        onClick={handleGenerate}
                        disabled={loading}
                        style={{ height: 46 }}
                    >
                        {loading ? (
                            <>
                                <div className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} />
                                Generating...
                            </>
                        ) : (
                            "✨ Get Outfits"
                        )}
                    </button>
                </div>
            </div>

            {/* Weather Widget */}
            {weather && (
                <div className="glass-card weather-widget" style={{ marginBottom: 24 }}>
                    <div className="weather-icon">{getWeatherIcon(weather.main)}</div>
                    <div className="weather-details">
                        <div className="weather-city">{weather.city}</div>
                        <div className="weather-desc">{weather.description}</div>
                    </div>
                    <div className="weather-temp">{weather.temperature_f}°F</div>
                    <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                        Feels like {weather.feels_like_f}°F
                    </div>
                </div>
            )}

            {/* Message */}
            {message && (
                <div className="glass-card" style={{ padding: 20, marginBottom: 24, textAlign: "center" }}>
                    <p className="text-muted">{message}</p>
                </div>
            )}

            {/* Outfit Cards */}
            {outfits.length > 0 ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                    {outfits.map((outfit, idx) => (
                        <div key={idx} className="glass-card outfit-card">
                            <div className="outfit-card-header">
                                <div className="outfit-card-number">{idx + 1}</div>
                                <h3>{outfit.name}</h3>
                            </div>
                            <p className="outfit-card-desc">{outfit.description}</p>
                            <div className="outfit-card-items">
                                {outfit.items.map((itemId) => {
                                    const item = getItemById(itemId);
                                    return item ? (
                                        <div key={itemId} className="outfit-item-thumb" title={item.name || `${item.color} ${item.category}`}>
                                            <img src={getImageUrl(item.image_path)} alt={item.name || item.category} />
                                        </div>
                                    ) : (
                                        <div key={itemId} className="outfit-item-thumb" style={{
                                            display: "flex", alignItems: "center", justifyContent: "center",
                                            fontSize: "0.7rem", color: "var(--text-muted)", padding: 4, textAlign: "center"
                                        }}>
                                            #{itemId}
                                        </div>
                                    );
                                })}
                            </div>
                            {outfit.style_notes && (
                                <div className="outfit-card-notes">
                                    💡 {outfit.style_notes}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            ) : hasLoaded && !loading ? (
                <div className="empty-state">
                    <div className="empty-state-icon">👔</div>
                    <h3>No outfits generated</h3>
                    <p>Make sure you have items in your wardrobe, then try generating outfits.</p>
                </div>
            ) : !hasLoaded ? (
                <div className="empty-state">
                    <div className="empty-state-icon">✨</div>
                    <h3>Ready to style</h3>
                    <p>Select an occasion, optionally enter your city for weather, and click &quot;Get Outfits&quot; to see AI-powered recommendations.</p>
                </div>
            ) : null}
        </div>
    );
}
