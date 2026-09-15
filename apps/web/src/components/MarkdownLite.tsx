import type { ReactNode } from "react";

/** Minimal markdown renderer (headings, bullets, bold, blockquotes, italic) -
 * avoids pulling in a full markdown dependency for report viewers. */
function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={`${keyPrefix}-${i}`}>{part.slice(2, -2)}</strong>;
    }
    return <span key={`${keyPrefix}-${i}`}>{part}</span>;
  });
}

export function MarkdownLite({ content }: { content: string }) {
  const lines = content.split("\n");
  return (
    <div className="space-y-1.5 text-sm text-navy-900">
      {lines.map((line, i) => {
        if (line.startsWith("# ")) return <h1 key={i} className="text-lg font-semibold mt-2">{renderInline(line.slice(2), `${i}`)}</h1>;
        if (line.startsWith("## ")) return <h2 key={i} className="text-sm font-semibold text-navy-900 mt-4">{renderInline(line.slice(3), `${i}`)}</h2>;
        if (line.startsWith("> "))
          return (
            <blockquote key={i} className="border-l-2 border-navy-700 pl-3 text-sm text-slate-700 italic">
              {renderInline(line.slice(2), `${i}`)}
            </blockquote>
          );
        if (line.startsWith("  - ")) return <p key={i} className="pl-8 text-xs text-slate-600">◦ {renderInline(line.slice(4), `${i}`)}</p>;
        if (line.startsWith("- ")) return <p key={i} className="pl-4 text-sm">• {renderInline(line.slice(2), `${i}`)}</p>;
        if (line.trim() === "") return <div key={i} className="h-1" />;
        if (line.includes("DEMO ENVIRONMENT"))
          return (
            <p key={i} className="inline-block text-xs font-semibold text-amber-800 bg-amber-50 border border-amber-200 rounded px-2 py-1">
              {line}
            </p>
          );
        if (line.startsWith("*") && line.endsWith("*") && !line.startsWith("**"))
          return <p key={i} className="text-xs text-slate-500 italic">{renderInline(line.slice(1, -1), `${i}`)}</p>;
        return <p key={i} className="text-sm">{renderInline(line, `${i}`)}</p>;
      })}
    </div>
  );
}
