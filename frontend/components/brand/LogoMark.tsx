"use client";

import { useId } from "react";

/** Inline SVG mark — unique gradient id per instance to avoid corruption when repeated. */
export function LogoMark({
  size = 40,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  const gradId = useId();

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden
    >
      <defs>
        <linearGradient id={gradId} x1="6" y1="4" x2="44" y2="44" gradientUnits="userSpaceOnUse">
          <stop stopColor="#2dd4bf" />
          <stop offset="1" stopColor="#2563eb" />
        </linearGradient>
      </defs>
      <rect width="48" height="48" rx="13" fill={`url(#${gradId})`} />
      {/* Path-based F — renders consistently unlike SVG <text> */}
      <path
        d="M15 14h11c2.8 0 4.5 1.3 4.5 3.4 0 1.5-.9 2.6-2.3 3.1 1.5.7 2.5 2 2.5 3.8 0 2.6-2.1 4.2-5.5 4.2H15V14zm3.5 3.2v4.2h6.2c1.1 0 1.8-.6 1.8-1.5 0-.9-.7-1.5-1.8-1.5h-6.2zm0 7.4v4.4h7c1.3 0 2-.7 2-1.7 0-1-.7-1.7-2-1.7h-7z"
        fill="#fff"
      />
      <path
        d="M32 33l4-14"
        stroke="#99f6e4"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <circle cx="37" cy="17" r="2" fill="#5eead4" />
    </svg>
  );
}
