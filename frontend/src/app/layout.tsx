"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import "./globals.css";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  const links = [
    { href: "/", label: "Dashboard", icon: "🏠" },
    { href: "/wardrobe", label: "Wardrobe", icon: "👔" },
    { href: "/outfits", label: "Outfits", icon: "✨" },
    { href: "/shopping", label: "Shopping", icon: "🛍️" },
  ];

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
        <nav className="navbar">
          <Link href="/" className="navbar-brand">
            <span className="navbar-brand-icon">👗</span>
            Smart Wardrobe
          </Link>
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
        </nav>
        {children}
      </body>
    </html>
  );
}
