import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { HttpAgent } from "@ag-ui/client";
import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000/agui";
const serviceAdapter = new ExperimentalEmptyAdapter();
const runtime = new CopilotRuntime({
  agents: {
    eval_harness: new HttpAgent({ url: BACKEND_URL }),
  },
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime, serviceAdapter, endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
};
