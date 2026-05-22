/**
 * Clears all stored auth tokens and redirects the user to the login page.
 * Used when the server returns a 401 (token expired / invalid / revoked).
 */
export function logout(): void {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  // Hard redirect so every in-memory state (React context, component state, etc.)
  // is wiped clean and the user starts fresh at the login page.
  window.location.href = '/login';
}
