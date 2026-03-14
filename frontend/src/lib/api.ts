import Cookies from "js-cookie";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function getHeaders() {
    const token = Cookies.get("token");
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;
    return headers;
}

// ─── Response envelope ────────────────────────────────────────────────────────

export interface ApiResponse<T> {
    data: T;
    error: string | null;
    meta: {
        total?: number;
        page?: number;
        limit?: number;
    };
}

// ─── Domain types ─────────────────────────────────────────────────────────────

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
    thumbnail_path: string | null;
    confidence: number | null;
    notes: string | null;
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

// ─── API functions ────────────────────────────────────────────────────────────

export async function uploadItem(
    image: File,
    name?: string,
): Promise<ApiResponse<{ item: ClothingItem; classification: Record<string, unknown> }>> {
    const formData = new FormData();
    formData.append("image", image);
    if (name) formData.append("name", name);

    const res = await fetch(`${API_BASE}/api/v1/items`, {
        method: "POST",
        body: formData,
        headers: getHeaders(),
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }));
        throw new Error(err.detail || "Upload failed");
    }
    return res.json();
}

export async function listItems(
    page = 1,
    limit = 20,
): Promise<ApiResponse<ClothingItem[]>> {
    const res = await fetch(
        `${API_BASE}/api/v1/items?page=${page}&limit=${limit}`,
        { headers: getHeaders() },
    );
    if (!res.ok) throw new Error("Failed to load wardrobe");
    return res.json();
}

export async function patchItem(
    id: number,
    updates: {
        name?: string;
        occasion_tags?: string[];
        season?: string;
        notes?: string;
    },
): Promise<ApiResponse<ClothingItem>> {
    const res = await fetch(`${API_BASE}/api/v1/items/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...getHeaders() },
        body: JSON.stringify(updates),
    });
    if (!res.ok) throw new Error("Failed to update item");
    return res.json();
}

export async function deleteItem(id: number): Promise<void> {
    const res = await fetch(`${API_BASE}/api/v1/items/${id}`, {
        method: "DELETE",
        headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to delete item");
}

export async function findSimilar(
    id: number,
    k = 5,
): Promise<ApiResponse<ClothingItem[]>> {
    const res = await fetch(
        `${API_BASE}/api/v1/items/${id}/similar?k=${k}`,
        { headers: getHeaders() },
    );
    if (!res.ok) throw new Error("Failed to find similar items");
    return res.json();
}

export async function getRecommendations(
    occasion = "casual",
    city?: string,
    numOutfits = 3,
    style?: string,
): Promise<ApiResponse<RecommendationResponse>> {
    const params = new URLSearchParams({ occasion, num_outfits: String(numOutfits) });
    if (city) params.set("city", city);
    if (style) params.set("style", style);

    const res = await fetch(`${API_BASE}/api/v1/recommendations?${params}`, {
        headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get recommendations");
    return res.json();
}

export async function getShoppingSuggestions(
    occasion?: string,
): Promise<ApiResponse<ShoppingResponse>> {
    const params = new URLSearchParams();
    if (occasion) params.set("occasion", occasion);

    const res = await fetch(`${API_BASE}/api/v1/shopping?${params}`, {
        headers: getHeaders(),
    });
    if (!res.ok) throw new Error("Failed to get shopping suggestions");
    return res.json();
}

export async function getHealth(): Promise<ApiResponse<HealthStatus>> {
    const res = await fetch(`${API_BASE}/api/v1/health`);
    if (!res.ok) throw new Error("API not available");
    return res.json();
}

export function getImageUrl(imagePath: string): string {
    if (imagePath.startsWith("http")) return imagePath;
    return `${API_BASE}${imagePath}`;
}

export async function searchImages(
    query: string,
): Promise<ApiResponse<{ images: string[] }>> {
    const res = await fetch(
        `${API_BASE}/api/v1/search?q=${encodeURIComponent(query)}`,
        { headers: getHeaders() },
    );
    if (!res.ok) throw new Error("Search failed");
    return res.json();
}

export async function addItemFromUrl(
    imageUrl: string,
    name?: string,
): Promise<ApiResponse<{ item: ClothingItem; classification: Record<string, unknown> }>> {
    const res = await fetch(`${API_BASE}/api/v1/items/from-url`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getHeaders() },
        body: JSON.stringify({ image_url: imageUrl, name }),
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Failed to add item" }));
        throw new Error(err.detail || "Failed to add item");
    }
    return res.json();
}
