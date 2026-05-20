/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GOVERNANCE_API_URL?: string;
  readonly VITE_ORCHESTRATOR_URL?: string;
  readonly VITE_PHOENIX_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
