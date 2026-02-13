/**
 * API client for communicating with the FastAPI backend.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ClothingItem {
    id: number;
    name: string | null;
    category: string;
    color: string;
    pattern: string;
    season: string;
    fabric: string;
    occasion_tags: string[];
    image_path: string;
    confidence: number | null;
    created_at: string | null;
    similarity_score?: number;
}

export interface OutfitSuggestion {
    name: string;
    items: number[];
    description: string;
    style_notes: string;
}

export interface WeatherData {
    city: string;
    temperature_f: number;
    feels_like_f: number;
    humidity: number;
    description: string;
    main: string;
    wind_speed: number;
    style_hints: string[];
}

export interface RecommendationResponse {
    outfits: OutfitSuggestion[];
    weather: WeatherData | null;
    occasion: string;
    message?: string;
}

export interface ShoppingSuggestion {
    item: string;
    category: string;
    reason: string;
    priority: string;
    estimated_price_range: string;
}

export interface ShoppingResponse {
    gaps: string[];
    suggestions: ShoppingSuggestion[];
    analysis: {
        total_items: number;
        categories?: Record<string, number>;
        colors?: Record<string, number>;
        seasons?: Record<string, number>;
        message?: string;
    };
}

export interface HealthStatus {
    status: string;
    service: string;
    gemini_configured: boolean;
    weather_configured: boolean;
}

// ─── API Functions ────────────────────────────────────────────────────────

export async function uploadItem(image: File, name?: string): Promise<{ item: ClothingItem; classification: Record<string, unknown> }> {
    const formData = new FormData();
    formData.append("image", image);
    if (name) formData.append("name", name);

    const res = await fetch(`${API_BASE}/api/items`, {
        method: "POST",
        body: formData,
    });

    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(error.detail || "Upload failed");
    }

    return res.json();
}

export async function listItems(): Promise<{ items: ClothingItem[]; total: number }> {
    const res = await fetch(`${API_BASE}/api/items`);
    if (!res.ok) throw new Error("Failed to load wardrobe");
    return res.json();
}

export async function deleteItem(id: number): Promise<void> {
    const res = await fetch(`${API_BASE}/api/items/${id}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Failed to delete item");
}

export async function findSimilar(id: number, k = 5): Promise<{ similar_items: ClothingItem[] }> {
    const res = await fetch(`${API_BASE}/api/items/${id}/similar?k=${k}`);
    if (!res.ok) throw new Error("Failed to find similar items");
    return res.json();
}

export async function getRecommendations(
    occasion = "casual",
    city?: string,
    numOutfits = 3,
    style?: string,
): Promise<RecommendationResponse> {
    const params = new URLSearchParams({ occasion, num_outfits: String(numOutfits) });
    if (city) params.set("city", city);
    if (style) params.set("style", style);

    const res = await fetch(`${API_BASE}/api/recommendations?${params}`);
    if (!res.ok) throw new Error("Failed to get recommendations");
    return res.json();
}

export async function getShoppingSuggestions(occasion?: string): Promise<ShoppingResponse> {
    const params = new URLSearchParams();
    if (occasion) params.set("occasion", occasion);

    const res = await fetch(`${API_BASE}/api/shopping?${params}`);
    if (!res.ok) throw new Error("Failed to get shopping suggestions");
    return res.json();
}

export async function getHealth(): Promise<HealthStatus> {
    const res = await fetch(`${API_BASE}/api/health`);
    if (!res.ok) throw new Error("API not available");
    return res.json();
}

export function getImageUrl(imagePath: string): string {
    if (imagePath.startsWith("http")) return imagePath;
    return `${API_BASE}${imagePath}`;
}
