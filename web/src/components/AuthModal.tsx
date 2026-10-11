import { useState, type FormEvent } from "react";
import { verifyPasscode } from "../lib/auth";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function AuthModal({ isOpen, onClose, onSuccess }: Props) {
  const [passcode, setPasscode] = useState("");
  const [error, setError] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (verifyPasscode(passcode)) {
      setError(false);
      onSuccess();
    } else {
      setError(true);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="auth-modal-title">
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-icon" aria-hidden="true">🔒</div>
          <div>
            <h2 id="auth-modal-title" className="modal-title">Candidate Access</h2>
            <p className="modal-subtitle">Enter your private access passcode to view matching jobs.</p>
          </div>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close modal">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <label className="modal-label" htmlFor="passcode-input">
            Passcode
          </label>
          <div className="modal-input-wrap">
            <input
              id="passcode-input"
              type={showPassword ? "text" : "password"}
              value={passcode}
              onChange={(e) => {
                setPasscode(e.target.value);
                if (error) setError(false);
              }}
              placeholder="Enter passcode..."
              className={`modal-input${error ? " is-error" : ""}`}
              autoFocus
              required
            />
            <button
              type="button"
              className="passcode-toggle"
              onClick={() => setShowPassword((p) => !p)}
              aria-label={showPassword ? "Hide passcode" : "Show passcode"}
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>

          {error && (
            <p className="modal-error" role="alert">
              Incorrect passcode. Please try again.
            </p>
          )}

          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              Unlock Radar
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
