"use client";

import { MessageSquarePlus } from "lucide-react";

export function FollowUpChips({
  suggestions,
  onSelect,
  disabled,
}: {
  suggestions: string[];
  onSelect: (text: string) => void;
  disabled?: boolean;
}) {
  if (!suggestions.length) return null;

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {suggestions.map((suggestion) => (
        <button
          key={suggestion}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(suggestion)}
          className="capability-pill disabled:opacity-50"
        >
          <MessageSquarePlus size={10} className="text-[var(--accent)]" />
          {suggestion}
        </button>
      ))}
    </div>
  );
}
