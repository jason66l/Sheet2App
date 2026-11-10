import { useId, useRef, useState, type ChangeEvent, type DragEvent } from 'react';

const MAX_BYTES = 25 * 1024 * 1024; // matches the import limit in the design doc

type Props = {
  /** Called when the user confirms a valid .xlsx file. Wire this to POST /imports. */
  onUpload: (file: File) => void;
};

export default function UploadDrop({ onUpload }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();

  const accept = (f: File | undefined) => {
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.xlsx')) {
      setFile(null);
      setError('Please choose an Excel .xlsx file.');
      return;
    }
    if (f.size > MAX_BYTES) {
      setFile(null);
      setError('That file is over 25 MB. Try removing unused sheets first.');
      return;
    }
    setError(null);
    setFile(f);
  };

  const onChange = (e: ChangeEvent<HTMLInputElement>) => accept(e.target.files?.[0]);

  const onDrop = (e: DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setDragging(false);
    accept(e.dataTransfer.files?.[0]);
  };

  const reset = () => {
    setFile(null);
    if (inputRef.current) inputRef.current.value = '';
  };

  if (file) {
    return (
      <div className="drop drop-ready">
        <div className="drop-file">
          <span className="drop-name">{file.name}</span>
          <span className="drop-size mono">{(file.size / 1024).toFixed(0)} KB</span>
        </div>
        <div className="drop-actions">
          <button type="button" className="btn btn-primary" onClick={() => onUpload(file)}>
            Continue with Google
          </button>
          <button type="button" className="text-button" onClick={reset}>
            Choose a different file
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        className="sr-only drop-input"
        onChange={onChange}
      />
      <label
        htmlFor={inputId}
        className={`drop${dragging ? ' is-dragging' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path d="M12 15V4m0 0L7.5 8.5M12 4l4.5 4.5M5 19h14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <span className="drop-title">Drop your .xlsx here, or choose a file</span>
        <span className="drop-hint">One table per sheet works best · up to 25 MB</span>
      </label>
      {error && (
        <p className="drop-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
