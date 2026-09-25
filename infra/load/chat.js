/**
 * FinSight AI — k6 load script (Phase 8 scaffolding)
 *
 * Usage:
 *   k6 run infra/load/chat.js
 *   BASE_URL=https://api.example.com k6 run infra/load/chat.js
 *   BASE_URL=... AUTH_TOKEN=eyJ... k6 run infra/load/chat.js
 *
 * Default: 50 VUs hitting GET /health for 30s.
 * When AUTH_TOKEN is set, also POSTs /chat (lightweight smoke).
 */
import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 50,
  duration: "30s",
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<2000"],
  },
};

const BASE_URL = (__ENV.BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const AUTH_TOKEN = __ENV.AUTH_TOKEN || "";

export default function () {
  const health = http.get(`${BASE_URL}/health`);
  check(health, {
    "health status 200": (r) => r.status === 200,
    "health has ok": (r) => {
      try {
        return JSON.parse(r.body).status === "ok";
      } catch (_) {
        return false;
      }
    },
  });

  if (AUTH_TOKEN) {
    const res = http.post(
      `${BASE_URL}/chat`,
      JSON.stringify({
        message: "ping",
        session_id: null,
      }),
      {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${AUTH_TOKEN}`,
        },
        timeout: "60s",
      }
    );
    check(res, {
      "chat not 5xx": (r) => r.status < 500,
    });
  }

  sleep(0.5);
}
