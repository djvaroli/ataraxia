/**
 * The sign-in boundary. The app talks to this interface; Firebase and the
 * local-mode owner are two implementations, and tests use a fake.
 */

export interface AuthUser {
  email: string | null;
}

export interface AuthClient {
  readonly mode: 'firebase' | 'local';
  /** Calls `listener` once the state is known and again on every change. */
  subscribe(listener: (user: AuthUser | null) => void): () => void;
  /** Rejects with `SignInError` carrying a message fit to show. */
  signIn(email: string, password: string): Promise<void>;
  signOut(): Promise<void>;
  /** A current ID token, refreshed when close to expiry; null in local mode. */
  getToken(): Promise<string | null>;
}

export class SignInError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'SignInError';
  }
}

/** Plain-language messages for Firebase Auth error codes seen at sign-in. */
export function signInErrorMessage(code: string): string {
  switch (code) {
    case 'auth/invalid-credential':
    case 'auth/invalid-login-credentials':
    case 'auth/wrong-password':
    case 'auth/user-not-found':
    case 'auth/invalid-email':
      return 'That email and password don’t match.';
    case 'auth/user-disabled':
      return 'This account has been disabled in Firebase.';
    case 'auth/too-many-requests':
      return 'Too many attempts. Wait a few minutes, then try again.';
    case 'auth/network-request-failed':
      return 'Firebase could not be reached. Check the connection and try again.';
    case 'auth/operation-not-allowed':
      return 'Email and password sign-in is not enabled for this Firebase project.';
    default:
      return 'Sign-in failed. Try again.';
  }
}

/** Local mode: the API treats every request as the owner; there is no sign-in. */
export function createLocalAuth(): AuthClient {
  const owner: AuthUser = { email: null };
  return {
    mode: 'local',
    subscribe(listener) {
      listener(owner);
      return () => {};
    },
    signIn: () => Promise.resolve(),
    signOut: () => Promise.resolve(),
    getToken: () => Promise.resolve(null),
  };
}
