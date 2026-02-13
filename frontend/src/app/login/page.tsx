"use client";

import { GoogleLogin } from "@react-oauth/google";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/lib/auth";
import { API_BASE } from "@/lib/api";

export default function LoginPage() {
    const { login } = useAuth();
    const [error, setError] = useState("");
    const [loading, setLoading] = useState(false);

    const handleSuccess = async (credentialResponse: any) => {
        setLoading(true);
        try {
            const res = await fetch(`${API_BASE}/api/auth/login`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ token: credentialResponse.credential }),
            });

            if (!res.ok) throw new Error("Login failed");

            const data = await res.json();
            login(data.access_token, data.user);
        } catch (err) {
            setError("Authentication failed. Please try again.");
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: "var(--bg-primary)",
            backgroundImage: "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(232, 116, 97, 0.15), transparent)"
        }}>
            <div className="glass-card" style={{ padding: 40, width: "100%", maxWidth: 400, textAlign: "center" }}>
                <div style={{ marginBottom: 32 }}>
                    <div style={{
                        width: 64, height: 64,
                        background: "var(--accent-gradient)",
                        borderRadius: 16,
                        margin: "0 auto 20px",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: "2rem"
                    }}>
                        ✨
                    </div>
                    <h1 className="heading-md" style={{ marginBottom: 8 }}>Welcome Back</h1>
                    <p className="text-muted">Sign in to your Smart Wardrobe</p>
                </div>

                {error && (
                    <div style={{
                        padding: 12,
                        background: "rgba(220, 60, 60, 0.1)",
                        color: "#f07070",
                        borderRadius: 8,
                        marginBottom: 20,
                        fontSize: "0.9rem"
                    }}>
                        {error}
                    </div>
                )}

                {loading ? (
                    <div className="spinner" style={{ margin: "20px auto" }} />
                ) : (
                    <div style={{ display: "flex", justifyContent: "center" }}>
                        <GoogleLogin
                            onSuccess={handleSuccess}
                            onError={() => setError("Google Sign-In failed")}
                            theme="filled_black"
                            shape="pill"
                        />
                    </div>
                )}

                <p className="text-xs text-muted" style={{ marginTop: 32 }}>
                    By signing in, you agree to organize your life with style.
                </p>
            </div>
        </div>
    );
}
