/**
 * Edge entry point.
 *
 * The Worker owns three things the FastAPI container should not:
 *   - secrets, injected into the container as env vars at start
 *   - the R2 binding for learner media
 *   - a cheap /health that answers without waking a sleeping container
 *
 * Everything else is proxied through untouched.
 */

import { Container, getContainer } from "@cloudflare/containers";

interface Env {
  BACKEND: DurableObjectNamespace<Backend>;
  MEDIA: R2Bucket;
  DATABASE_URL: string;
  JWT_SECRET: string;
  AI_API_KEY?: string;
  ENVIRONMENT: string;
  ALLOWED_ORIGINS: string;
  AI_ENABLED: string;
}

export class Backend extends Container<Env> {
  defaultPort = 8000;

  // Long enough that a learner pausing mid-question does not pay a cold
  // start, short enough that idle time is not billed.
  sleepAfter = "15m";

  override envVars = {
    DATABASE_URL: this.env.DATABASE_URL,
    JWT_SECRET: this.env.JWT_SECRET,
    ENVIRONMENT: this.env.ENVIRONMENT,
    ALLOWED_ORIGINS: this.env.ALLOWED_ORIGINS,
    AI_ENABLED: this.env.AI_ENABLED,
    AI_API_KEY: this.env.AI_API_KEY ?? "",
    LOG_LEVEL: "INFO",
  };

  override onStart() {
    console.log(JSON.stringify({ event: "container_started" }));
  }

  override onError(error: unknown) {
    console.error(JSON.stringify({ event: "container_error", error: String(error) }));
    return new Response("Backend unavailable", { status: 503 });
  }
}

/**
 * One container instance per named id. "main" keeps a single warm instance,
 * which is what you want for a study: shared connection pool, predictable
 * latency, no per-user cold starts. Switch to a per-session id only if you
 * later need isolation between participants.
 */
const INSTANCE = "main";

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Answered at the edge so uptime checks never wake the container.
    if (url.pathname === "/edge-health") {
      return Response.json({ status: "ok", environment: env.ENVIRONMENT });
    }

    const container = getContainer(env.BACKEND, INSTANCE);
    return container.fetch(request);
  },
} satisfies ExportedHandler<Env>;
