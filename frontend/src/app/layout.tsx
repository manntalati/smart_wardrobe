"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { GoogleOAuthProvider } from "@react-oauth/google";
import { AuthProvider, useAuth } from "@/lib/auth";
import "./globals.css";

// Placeholder ID - User must replace this in real app or .env
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || "YOUR_GOOGLE_CLIENT_ID_HERE";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <title>Smart Wardrobe — AI-Powered Style Assistant</title>
        <meta
          name="description"
          content="Catalog your wardrobe, get AI-powered outfit recommendations based on weather and occasion, and discover what to buy next."
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body>
        <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
          <AuthProvider>
            <AppContent>{children}</AppContent>
          </AuthProvider>
        </GoogleOAuthProvider>
      </body>
    </html>
  );
}

function AppContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [showDropdown, setShowDropdown] = useState(false);

  // Hide navbar on login page
  if (pathname === "/login") {
    return <>{children}</>;
  }

  const links = [
    { href: "/", label: "Dashboard", icon: "🏠" },
    { href: "/wardrobe", label: "Wardrobe", icon: "👔" },
    { href: "/outfits", label: "Outfits", icon: "✨" },
    { href: "/shopping", label: "Shopping", icon: "🛍️" },
  ];

  return (
    <>
      <nav className="navbar">
        <Link href="/" className="navbar-brand">
          <span className="navbar-brand-icon">👗</span>
          Smart Wardrobe
        </Link>

        {user && (
          <div className="navbar-links">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`navbar-link ${pathname === link.href ? "active" : ""}`}
              >
                <span className="navbar-link-icon">{link.icon}</span>
                <span>{link.label}</span>
              </Link>
            ))}
          </div>
        )}

        {user && (
          <div className="navbar-user" onClick={() => setShowDropdown(!showDropdown)}>
            <div className="user-avatar">
              {user.avatar_url ? (
                <img src={user.avatar_url} alt={user.full_name} />
              ) : (
                <span>{user.full_name?.charAt(0) || "U"}</span>
              )}
            </div>

            {showDropdown && (
              <>
                <div className="dropdown-overlay" onClick={(e) => { e.stopPropagation(); setShowDropdown(false); }} />
                <div className="dropdown-menu">
                  <div className="dropdown-header">
                    <strong>{user.full_name}</strong>
                    <span className="text-xs text-muted">{user.email}</span>
                  </div>
                  <div className="dropdown-divider" />
                  <button className="dropdown-item text-danger" onClick={logout}>
                    Sign Out
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </nav>
      {children}
    </>
  );
}
