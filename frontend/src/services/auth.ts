// Secure local and production behavior is the default. Set
// VITE_AUTH_ENABLED=false only for the deliberate offline/fallback preview.
const AUTH_ENABLED = import.meta.env.VITE_AUTH_ENABLED !== 'false';
const KEYCLOAK_BASE_URL = import.meta.env.VITE_KEYCLOAK_BASE_URL || 'http://localhost:8180';
const REALM = import.meta.env.VITE_KEYCLOAK_REALM || 'home-energy';
const CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'home-energy-dashboard';
const TOKEN_KEY = 'home-energy.access-token';
const REFRESH_TOKEN_KEY = 'home-energy.refresh-token';
const PKCE_VERIFIER_KEY = 'home-energy.pkce-verifier';
const PKCE_STATE_KEY = 'home-energy.pkce-state';
const ACCESS_TOKEN_REFRESH_SKEW_MS = 10_000;

const realmBase = `${KEYCLOAK_BASE_URL}/realms/${REALM}/protocol/openid-connect`;

type TokenResponse = {
  access_token?: string;
  refresh_token?: string;
};

let refreshInFlight: Promise<boolean> | null = null;

function base64Url(bytes: Uint8Array): string {
  let binary = '';
  bytes.forEach(byte => { binary += String.fromCharCode(byte); });
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function randomValue(): string {
  const bytes = new Uint8Array(32);
  crypto.getRandomValues(bytes);
  return base64Url(bytes);
}

async function challengeFor(verifier: string): Promise<string> {
  const bytes = new TextEncoder().encode(verifier);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return base64Url(new Uint8Array(digest));
}

function redirectUri(): string {
  return `${window.location.origin}/`;
}

function decodePayload(token: string): Record<string, unknown> | null {
  try {
    const payload = token.split('.')[1];
    if (!payload) return null;
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), '=');
    return JSON.parse(atob(padded));
  } catch {
    return null;
  }
}

function accessTokenExpiresSoon(token: string): boolean {
  const expirySeconds = Number(decodePayload(token)?.exp);
  return Number.isFinite(expirySeconds)
    && expirySeconds * 1000 <= Date.now() + ACCESS_TOKEN_REFRESH_SKEW_MS;
}

function storeTokens(tokens: TokenResponse): boolean {
  if (!tokens.access_token) return false;
  sessionStorage.setItem(TOKEN_KEY, tokens.access_token);
  if (tokens.refresh_token) sessionStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  return true;
}

function clearTokens(): void {
  sessionStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function requestRefreshToken(): Promise<boolean> {
  const refreshToken = sessionStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) return false;

  try {
    const body = new URLSearchParams({
      grant_type: 'refresh_token',
      client_id: CLIENT_ID,
      refresh_token: refreshToken
    });
    const response = await fetch(`${realmBase}/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body
    });

    if (!response.ok) {
      // Keycloak uses 400/401 when the refresh token is no longer valid. Keep
      // tokens for transient server/network failures so a later retry can recover.
      if (response.status === 400 || response.status === 401) clearTokens();
      return false;
    }

    return storeTokens(await response.json() as TokenResponse);
  } catch {
    // Do not log a response body or token-derived data.
    return false;
  }
}

export const auth = {
  enabled: AUTH_ENABLED,

  getAccessToken(): string | null {
    return sessionStorage.getItem(TOKEN_KEY);
  },

  async refreshAccessToken(): Promise<boolean> {
    if (!AUTH_ENABLED) return false;
    if (!refreshInFlight) {
      refreshInFlight = requestRefreshToken().finally(() => {
        refreshInFlight = null;
      });
    }
    return refreshInFlight;
  },

  async getAccessTokenForRequest(): Promise<string | null> {
    if (!AUTH_ENABLED) return null;

    const accessToken = this.getAccessToken();
    if (!accessToken || accessTokenExpiresSoon(accessToken)) {
      await this.refreshAccessToken();
    }
    return this.getAccessToken();
  },

  async fetchWithAuth(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    const createRequest = async (): Promise<Response> => {
      const headers = new Headers(init?.headers);
      const accessToken = await this.getAccessTokenForRequest();
      headers.delete('Authorization');
      if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`);
      return fetch(input, { ...init, headers });
    };

    const response = await createRequest();
    if (AUTH_ENABLED && response.status === 401 && await this.refreshAccessToken()) {
      return createRequest();
    }
    return response;
  },

  getHomeEnergyUserId(): number | null {
    const token = this.getAccessToken();
    const claim = token ? decodePayload(token)?.home_energy_user_id : null;
    const id = Number(claim);
    return Number.isInteger(id) && id > 0 ? id : null;
  },

  isAdmin(): boolean {
    const token = this.getAccessToken();
    const access = token ? decodePayload(token)?.realm_access as { roles?: string[] } | undefined : undefined;
    return access?.roles?.includes('ADMIN') ?? false;
  },

  async beginLogin(): Promise<void> {
    if (!AUTH_ENABLED) return;
    const verifier = randomValue();
    const state = randomValue();
    sessionStorage.setItem(PKCE_VERIFIER_KEY, verifier);
    sessionStorage.setItem(PKCE_STATE_KEY, state);
    const query = new URLSearchParams({
      client_id: CLIENT_ID,
      response_type: 'code',
      redirect_uri: redirectUri(),
      scope: 'openid profile',
      state,
      code_challenge: await challengeFor(verifier),
      code_challenge_method: 'S256'
    });
    window.location.assign(`${realmBase}/auth?${query.toString()}`);
  },

  async completeLogin(): Promise<boolean> {
    if (!AUTH_ENABLED) return true;
    const query = new URLSearchParams(window.location.search);
    const code = query.get('code');
    if (!code) return (await this.getAccessTokenForRequest()) !== null;
    const verifier = sessionStorage.getItem(PKCE_VERIFIER_KEY);
    const expectedState = sessionStorage.getItem(PKCE_STATE_KEY);
    if (!verifier || query.get('state') !== expectedState) {
      throw new Error('Keycloak login state could not be validated.');
    }
    const body = new URLSearchParams({
      grant_type: 'authorization_code',
      client_id: CLIENT_ID,
      code,
      redirect_uri: redirectUri(),
      code_verifier: verifier
    });
    const response = await fetch(`${realmBase}/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body
    });
    if (!response.ok) throw new Error(`Keycloak token exchange failed (${response.status}).`);
    const tokens = await response.json() as TokenResponse;
    if (!storeTokens(tokens)) throw new Error('Keycloak token exchange did not return an access token.');
    sessionStorage.removeItem(PKCE_VERIFIER_KEY);
    sessionStorage.removeItem(PKCE_STATE_KEY);
    window.history.replaceState({}, document.title, redirectUri());
    return true;
  },

  logout(): void {
    clearTokens();
  }
};
