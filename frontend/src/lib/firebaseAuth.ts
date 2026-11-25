/**
 * Firebase email/password sign-in. Loaded only in firebase mode.
 *
 * `initializeAuth` is used instead of `getAuth` so that no popup/redirect
 * resolver is registered: that resolver loads an iframe and scripts from
 * Google, which the Content Security Policy does not allow and this app
 * does not need.
 */
import { FirebaseError, initializeApp } from 'firebase/app';
import {
  browserLocalPersistence,
  indexedDBLocalPersistence,
  initializeAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
} from 'firebase/auth';
import type { FirebaseWebConfig } from './api';
import { type AuthClient, SignInError, signInErrorMessage } from './auth';

export function createFirebaseAuth(config: FirebaseWebConfig): AuthClient {
  const app = initializeApp(
    {
      apiKey: config.api_key,
      authDomain: config.auth_domain,
      projectId: config.project_id,
      appId: config.app_id,
    },
    'ataraxia',
  );
  const auth = initializeAuth(app, {
    persistence: [indexedDBLocalPersistence, browserLocalPersistence],
  });

  return {
    mode: 'firebase',
    subscribe(listener) {
      return onAuthStateChanged(auth, (user) =>
        listener(user ? { email: user.email } : null),
      );
    },
    async signIn(email, password) {
      try {
        await signInWithEmailAndPassword(auth, email, password);
      } catch (error) {
        const code = error instanceof FirebaseError ? error.code : '';
        throw new SignInError(signInErrorMessage(code));
      }
    },
    signOut: () => signOut(auth),
    async getToken() {
      const user = auth.currentUser;
      return user ? user.getIdToken() : null;
    },
  };
}
