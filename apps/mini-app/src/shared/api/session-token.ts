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

  return {
    ...requestInit,
    headers: {
      ...(init.headers as Record<string, string> | undefined),
      Authorization: `${SESSION_AUTH_SCHEME} ${activeSessionToken}`,
    },
  };
}
