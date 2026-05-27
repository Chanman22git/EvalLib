import { AlertTriangle } from "lucide-react";
import { useEffect, useState } from "react";

import { GOVERNANCE_API_URL } from "@/lib/config";

type Status = "checking" | "ok" | "down";

async function checkBackend(signal: AbortSignal): Promise<boolean> {
  try {
    const res = await fetch(`${GOVERNANCE_API_URL}/health`, { signal });
    return res.ok;
  } catch {
    return false;
  }
}

export function BackendStatusBanner() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    const ctrl = new AbortController();
    let cancelled = false;

    const tick = async () => {
      const ok = await checkBackend(ctrl.signal);
      if (cancelled) return;
      setStatus(ok ? "ok" : "down");
    };

    tick();
    const id = window.setInterval(tick, 10_000);
    return () => {
      cancelled = true;
      ctrl.abort();
      window.clearInterval(id);
    };
  }, []);

  if (status !== "down") return null;

  return (
    <div className="border-b border-amber-300 bg-amber-50 px-6 py-3 text-sm text-amber-900">
      <div className="mx-auto flex max-w-7xl items-start gap-3">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
        <div className="space-y-1">
          <div className="font-medium">
            Backend not reachable at <code className="rounded bg-amber-100 px-1">{GOVERNANCE_API_URL}</code>
          </div>
          <div className="text-amber-800">
            This UI is a hosted shell — the FastAPI services run on your machine. Clone{" "}
            <a
              className="underline"
              href="https://github.com/Chanman22git/EvalLib"
              target="_blank"
              rel="noreferrer"
            >
              Chanman22git/EvalLib
            </a>{" "}
            and run <code className="rounded bg-amber-100 px-1">docker-compose up</code>, then refresh.
            CLI chat: <code className="rounded bg-amber-100 px-1">make chat</code>.
          </div>
        </div>
      </div>
    </div>
  );
}
