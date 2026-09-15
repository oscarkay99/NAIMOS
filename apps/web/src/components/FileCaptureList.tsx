"use client";

/** Reusable capture-or-upload input for photos/video. Using
 * `capture="environment"` triggers the phone's native camera app directly
 * on mobile browsers (a real, well-supported pattern) rather than building
 * a custom in-browser camera UI - the same file input works as a plain
 * upload picker on desktop for the demo. */
export function FileCaptureList({
  label,
  accept,
  capture,
  multiple = true,
  files,
  onChange,
  disabled,
}: {
  label: string;
  accept: string;
  capture?: "environment" | "user";
  multiple?: boolean;
  files: File[];
  onChange: (files: File[]) => void;
  disabled?: boolean;
}) {
  function handleAdd(e: React.ChangeEvent<HTMLInputElement>) {
    const newFiles = Array.from(e.target.files || []);
    onChange(multiple ? [...files, ...newFiles] : newFiles.slice(0, 1));
    e.target.value = "";
  }

  function remove(idx: number) {
    onChange(files.filter((_, i) => i !== idx));
  }

  return (
    <div>
      <label className="block text-xs font-medium text-slate-500 mb-1">{label}</label>
      <input
        type="file"
        accept={accept}
        capture={capture}
        multiple={multiple}
        onChange={handleAdd}
        disabled={disabled}
        className="text-sm"
      />
      {files.length > 0 && (
        <ul className="mt-2 grid grid-cols-2 sm:grid-cols-3 gap-2">
          {files.map((f, i) => (
            <li key={i} className="relative border border-border rounded-md overflow-hidden bg-slate-50">
              {f.type.startsWith("image/") ? (
                <img src={URL.createObjectURL(f)} alt={f.name} className="w-full h-20 object-cover" />
              ) : (
                <div className="w-full h-20 flex items-center justify-center text-[10px] text-slate-500 px-2 text-center">
                  {f.type.startsWith("video/") ? "🎥" : "📄"} {f.name}
                </div>
              )}
              <button
                type="button"
                onClick={() => remove(i)}
                className="absolute top-1 right-1 w-5 h-5 rounded-full bg-black/60 text-white text-xs leading-none hover:bg-black/80"
                aria-label={`Remove ${f.name}`}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
