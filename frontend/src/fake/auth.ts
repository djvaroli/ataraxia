/** A stand-in for Firebase sign-in, for tests and the demo build. */
import type { AuthClient, AuthUser } from '../lib/auth';
import { SignInError, signInErrorMessage } from '../lib/auth';

export interface FakeAuth extends AuthClient {
  signedIn(): boolean;
}

export function createFakeAuth(
  options: {
    signedIn?: boolean;
    email?: string;
    password?: string;
    /** Firebase error code every sign-in fails with. */
    failWith?: string;
  } = {},
): FakeAuth {
  const email = options.email ?? 'owner@example.com';
  const password = options.password ?? 'correct horse';
  let user: AuthUser | null = options.signedIn ? { email } : null;
  const listeners = new Set<(user: AuthUser | null) => void>();
  const emit = () => listeners.forEach((listener) => listener(user));

  return {
    mode: 'firebase',
    signedIn: () => user !== null,
    subscribe(listener) {
      listeners.add(listener);
      listener(user);
      return () => listeners.delete(listener);
    },
    async signIn(givenEmail, givenPassword) {
      if (options.failWith) {
        throw new SignInError(signInErrorMessage(options.failWith));
      }
      if (givenEmail !== email || givenPassword !== password) {
        throw new SignInError(signInErrorMessage('auth/invalid-credential'));
      }
      user = { email };
      emit();
    },
    async signOut() {
      user = null;
      emit();
    },
    getToken: async () => (user ? 'fake-id-token' : null),
  };
}
