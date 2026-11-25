/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** "1" runs the app against the in-memory demo API. Development only. */
  readonly VITE_DEMO?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
