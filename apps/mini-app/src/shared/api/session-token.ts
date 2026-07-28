let activeSessionToken: string | null = null;

const SESSION_AUTH_SCHEME = "Bearer";

export function activateSessionToken(token: string): void {
  activeSessionToken = token;
}

export function clearSessionToken(): void {
  activeSessionToken = null;
}

export function withSessionAuth(init: RequestInit = {}): RequestInit {
  const requestInit: RequestInit = { ...init, credentials: "include" };
  if (!activeSessionToken) {
    return requestInit;
  }

  const headers = new Headers(init.headers);
  headers.set("Authorization", `${SESSION_AUTH_SCHEME} ${activeSessionToken}`);
  return { ...requestInit, headers };
}
