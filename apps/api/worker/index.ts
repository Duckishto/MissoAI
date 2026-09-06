/**
 * Edge entry point.
 *
 * The Worker owns four things the FastAPI container should not:
 *   - secrets, injected into the container as env vars at start
 *   - the R2 binding for learner media
 *   - a cheap /edge-health that answers without waking a sleeping container
 *   - CORS preflight, answered at the edge
 *
 * Preflight is handled here rather than in FastAPI because a sleeping
 * container returns a start-up error with no CORS headers, which the browser
 * reports as an unreachable server. During a timed study that would land
 * inside a participant's recorded response time.
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

const INSTANCE = "main";

function parseOrigins(raw: string): string[] {
  const text = (raw ?? "").trim();
  if (!text) return [];
  if (text.startsWith("[")) {
    try {
      return JSON.parse(text) as string[];
    } catch {
      return [];
    }
  }
  return text.split(",").map((s) => s.trim()).filter(Boolean);
}

function corsHeaders(origin: string | null, env: Env): Headers {
  const headers = new Headers();
  const allowed = parseOrigins(env.ALLOWED_ORIGINS);
  if (origin && allowed.includes(origin)) {
    headers.set("access-control-allow-origin", origin);
    headers.set("access-control-allow-credentials", "true");
    headers.set("vary", "Origin");
  }
  return headers;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const origin = request.headers.get("Origin");

    // Answered at the edge so uptime checks never wake the container.
    if (url.pathname === "/edge-health") {
      return Response.json({ status: "ok", environment: env.ENVIRONMENT });
    }

    // Preflight never reaches the container. A cold start must not present
    // itself to the browser as a CORS failure.
    if (request.method === "OPTIONS") {
      const headers = corsHeaders(origin, env);
      if (!headers.has("access-control-allow-origin")) {
        return new Response(null, { status: 403 });
      }
      headers.set(
        "access-control-allow-methods",
        "GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS",
      );
      headers.set(
        "access-control-allow-headers",
        request.headers.get("Access-Control-Request-Headers") ?? "content-type, authorization",
      );
      headers.set("access-control-max-age", "600");
      return new Response(null, { status: 204, headers });
    }

    const container = getContainer(env.BACKEND, INSTANCE);

    let response: Response;
    try {
      response = await container.fetch(request);
    } catch (error) {
      // A waking container would otherwise surface as an opaque network
      // error. 503 with Retry-After lets the client say something useful.
      console.error(JSON.stringify({ event: "container_fetch_failed", error: String(error) }));
      response = Response.json(
        {
          error: { code: "backend_starting", message: "The server is starting. Try again in a moment." },
        },
        { status: 503, headers: { "retry-after": "5" } },
      );
    }

    // Error responses generated here have no CORS headers of their own, so
    // the browser would report them as network failures rather than showing
    // the message. Attach them on the way out.
    if (!response.headers.has("access-control-allow-origin")) {
      const merged = new Headers(response.headers);
      for (const [k, v] of corsHeaders(origin, env)) merged.set(k, v);
      response = new Response(response.body, {
        status: response.status,
        statusText: response.statusText,
        headers: merged,
      });
    }

    return response;
  },
} satisfies ExportedHandler<Env>;
