const AUTH_KEY = "jobradar_auth_session";
const PASSCODES = ["himanshu2027", "radar2027", "admin123"];

export function isSessionAuthed(): boolean {
  try {
    return localStorage.getItem(AUTH_KEY) === "true";
  } catch {
    return false;
  }
}

export function verifyPasscode(input: string): boolean {
  const clean = input.trim().toLowerCase();
  if (PASSCODES.includes(clean)) {
    try {
      localStorage.setItem(AUTH_KEY, "true");
    } catch {
      /* storage disabled */
    }
    return true;
  }
  return false;
}

export function clearAuthSession(): void {
  try {
    localStorage.removeItem(AUTH_KEY);
  } catch {
    /* storage disabled */
  }
}
