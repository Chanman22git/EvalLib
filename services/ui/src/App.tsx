import { Navigate, Route, Routes } from "react-router-dom";

import { Layout } from "@/components/Layout";
import { AgentDetail } from "@/pages/AgentDetail";
import { Agents } from "@/pages/Agents";
import { Changes } from "@/pages/Changes";
import { ConversationDetail } from "@/pages/ConversationDetail";
import { Conversations } from "@/pages/Conversations";
import { Dashboard } from "@/pages/Dashboard";
import { EvalDetail } from "@/pages/EvalDetail";
import { Evals } from "@/pages/Evals";
import { Governance } from "@/pages/Governance";
import { Regressions } from "@/pages/Regressions";
import { TraceDetail } from "@/pages/TraceDetail";
import { Traces } from "@/pages/Traces";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="agents" element={<Agents />} />
        <Route path="agents/:id" element={<AgentDetail />} />
        <Route path="evals" element={<Evals />} />
        <Route path="evals/:id" element={<EvalDetail />} />
        <Route path="conversations" element={<Conversations />} />
        <Route path="conversations/:sessionId" element={<ConversationDetail />} />
        <Route path="traces" element={<Traces />} />
        <Route path="traces/:traceId" element={<TraceDetail />} />
        <Route path="regressions" element={<Regressions />} />
        <Route path="changes" element={<Changes />} />
        <Route path="governance" element={<Governance />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
