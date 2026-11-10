/**
 * Mizan Production Frontend Node.js Server for Hostinger
 * 
 * Zero-dependency, high-performance static file server, SPA routing engine,
 * and optional built-in API proxy to Mizan Cloud Backend.
 * Fully compatible with Hostinger hPanel Node.js (Phusion Passenger / Reverse Proxy).
 */

import http from "node:http";
import https from "node:https";
import tls from "node:tls";
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = Number(process.env.PORT) || 3000;
const HOST = process.env.HOST || "0.0.0.0";
const BACKEND_URL = process.env.BACKEND_URL || "https://mizan-api-mq0i.onrender.com";

// Determine static root directory (checks ./dist, then current directory)
function resolveStaticRoot() {
  const candidates = [
    path.join(__dirname, "dist"),
    path.join(__dirname, "public"),
    __dirname,
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(path.join(candidate, "index.html"))) {
      return candidate;
    }
  }
  return __dirname;
}

const STATIC_ROOT = resolveStaticRoot();
console.log(`[Mizan Server] Static root directory: ${STATIC_ROOT}`);
console.log(`[Mizan Server] Backend proxy target: ${BACKEND_URL}`);

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".mjs": "application/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".webp": "image/webp",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
  ".ttf": "font/ttf",
  ".eot": "application/vnd.ms-fontobject",
  ".map": "application/json",
};

const COMPRESSIBLE_EXTENSIONS = new Set([
  ".html",
  ".js",
  ".mjs",
  ".css",
  ".json",
  ".svg",
  ".map",
  ".txt",
]);

function setSecurityHeaders(res) {
  res.setHeader("X-Content-Type-Options", "nosniff");
  res.setHeader("X-Frame-Options", "DENY");
  res.setHeader("Referrer-Policy", "strict-origin-when-cross-origin");
  res.setHeader("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
}

function sendFile(req, res, filePath, statusCode = 200) {
  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || "application/octet-stream";

  fs.stat(filePath, (err, stats) => {
    if (err || !stats.isFile()) {
      return sendSpaFallback(req, res);
    }

    setSecurityHeaders(res);
    res.setHeader("Content-Type", contentType);

    // Cache Control headers
    if (filePath.includes(path.sep + "assets" + path.sep)) {
      // Fingerprinted assets: 1 year immutable
      res.setHeader("Cache-Control", "public, max-age=31536000, immutable");
    } else if (ext === ".html" || path.basename(filePath) === "config.js") {
      // index.html and config.js: never stale cache
      res.setHeader("Cache-Control", "no-cache, no-store, must-revalidate");
      res.setHeader("Pragma", "no-cache");
      res.setHeader("Expires", "0");
    } else {
      res.setHeader("Cache-Control", "public, max-age=86400");
    }

    // Compression support (Gzip / Deflate)
    const acceptEncoding = req.headers["accept-encoding"] || "";
    const shouldCompress = COMPRESSIBLE_EXTENSIONS.has(ext) && stats.size > 1024;

    res.statusCode = statusCode;

    if (shouldCompress && /\bgzip\b/.test(acceptEncoding)) {
      res.setHeader("Content-Encoding", "gzip");
      res.setHeader("Vary", "Accept-Encoding");
      const raw = fs.createReadStream(filePath);
      const gzip = zlib.createGzip({ level: zlib.constants.Z_BEST_SPEED });
      raw.pipe(gzip).pipe(res);
    } else if (shouldCompress && /\bdeflate\b/.test(acceptEncoding)) {
      res.setHeader("Content-Encoding", "deflate");
      res.setHeader("Vary", "Accept-Encoding");
      const raw = fs.createReadStream(filePath);
      const deflate = zlib.createDeflate();
      raw.pipe(deflate).pipe(res);
    } else {
      res.setHeader("Content-Length", stats.size);
      const raw = fs.createReadStream(filePath);
      raw.pipe(res);
    }
  });
}

function sendSpaFallback(req, res) {
  const indexPath = path.join(STATIC_ROOT, "index.html");
  if (fs.existsSync(indexPath)) {
    sendFile(req, res, indexPath, 200);
  } else {
    setSecurityHeaders(res);
    res.statusCode = 404;
    res.setHeader("Content-Type", "text/plain; charset=utf-8");
    res.end("404 Not Found - Mizan React application bundle missing.");
  }
}

// Transparently proxy /api/ requests to the Render cloud backend
function proxyApiRequest(req, res) {
  const targetUrl = new URL(req.url, BACKEND_URL);
  const clientReqHeaders = { ...req.headers };

  delete clientReqHeaders.host;
  clientReqHeaders["x-forwarded-host"] = req.headers.host;
  clientReqHeaders["x-forwarded-proto"] = req.headers["x-forwarded-proto"] || "https";

  const isHttps = targetUrl.protocol === "https:";
  const client = isHttps ? https : http;

  const proxyReq = client.request(
    targetUrl,
    {
      method: req.method,
      headers: clientReqHeaders,
      timeout: 60000,
    },
    (proxyRes) => {
      setSecurityHeaders(res);
      res.writeHead(proxyRes.statusCode, proxyRes.headers);
      proxyRes.pipe(res);
    }
  );

  proxyReq.on("error", (err) => {
    console.error("[Proxy Error]", err.message);
    setSecurityHeaders(res);
    res.statusCode = 502;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(
      JSON.stringify({
        error: {
          code: "BAD_GATEWAY",
          message: `Unable to connect to Mizan cloud backend: ${err.message}`,
        },
      })
    );
  });

  proxyReq.on("timeout", () => {
    proxyReq.destroy();
    setSecurityHeaders(res);
    res.statusCode = 504;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(
      JSON.stringify({
        error: {
          code: "GATEWAY_TIMEOUT",
          message: "Mizan cloud backend timed out while waking up.",
        },
      })
    );
  });

  req.pipe(proxyReq);
}

// Direct Hostinger SMTP delivery engine for HTTPS mail relay
function sendSmtpViaHostinger({ to, subject, text, html, host = "smtp.hostinger.com", port = 465, user = "llmguru@hennt.in", pass = "yeswantH@181#" }) {
  return new Promise((resolve, reject) => {
    let resolved = false;
    const socket = tls.connect({ host, port, minVersion: "TLSv1.2" }, () => {
      let step = 0;
      let buffer = "";

      socket.on("data", (chunk) => {
        buffer += chunk.toString("utf8");
        const lines = buffer.split("\r\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line) continue;
          const code = line.slice(0, 3);
          const isFinal = line[3] === " ";
          if (!isFinal) continue;

          try {
            if (step === 0 && code === "220") {
              step = 1;
              socket.write("EHLO llmguru.hennt.in\r\n");
            } else if (step === 1 && code === "250") {
              step = 2;
              socket.write("AUTH LOGIN\r\n");
            } else if (step === 2 && code === "334") {
              step = 3;
              socket.write(Buffer.from(user).toString("base64") + "\r\n");
            } else if (step === 3 && code === "334") {
              step = 4;
              socket.write(Buffer.from(pass).toString("base64") + "\r\n");
            } else if (step === 4 && code === "235") {
              step = 5;
              socket.write(`MAIL FROM: <${user}>\r\n`);
            } else if (step === 5 && code === "250") {
              step = 6;
              socket.write(`RCPT TO: <${to}>\r\n`);
            } else if (step === 6 && code === "250") {
              step = 7;
              socket.write("DATA\r\n");
            } else if (step === 7 && code === "354") {
              step = 8;
              const boundary = `----=_Mizan_${Date.now()}`;
              const fromEncoded = "=?UTF-8?B?" + Buffer.from("Mizan Platform").toString("base64") + "?=";
              const subjectEncoded = "=?UTF-8?B?" + Buffer.from(subject).toString("base64") + "?=";
              const payload = [
                `From: ${fromEncoded} <${user}>`,
                `To: <${to}>`,
                `Subject: ${subjectEncoded}`,
                `Date: ${new Date().toUTCString()}`,
                "MIME-Version: 1.0",
                `Content-Type: multipart/alternative; boundary="${boundary}"`,
                "",
                `--${boundary}`,
                "Content-Type: text/plain; charset=utf-8",
                "Content-Transfer-Encoding: base64",
                "",
                Buffer.from(text || "").toString("base64"),
                "",
                `--${boundary}`,
                "Content-Type: text/html; charset=utf-8",
                "Content-Transfer-Encoding: base64",
                "",
                Buffer.from(html || "").toString("base64"),
                "",
                `--${boundary}--`,
                ".",
                ""
              ].join("\r\n");
              socket.write(payload);
            } else if (step === 8 && code === "250") {
              step = 9;
              resolved = true;
              socket.write("QUIT\r\n");
              socket.end();
              resolve({ ok: true, messageId: line });
            } else if (parseInt(code, 10) >= 400) {
              socket.destroy();
              if (!resolved) {
                resolved = true;
                reject(new Error(`SMTP error at step ${step} with code ${code}: ${line}`));
              }
            }
          } catch (err) {
            socket.destroy();
            if (!resolved) {
              resolved = true;
              reject(err);
            }
          }
        }
      });
    });

    socket.on("error", (err) => {
      if (!resolved) {
        resolved = true;
        reject(err);
      }
    });

    socket.setTimeout(20000, () => {
      socket.destroy(new Error("SMTP socket timeout"));
      if (!resolved) {
        resolved = true;
        reject(new Error("SMTP socket timeout"));
      }
    });
  });
}

const server = http.createServer((req, res) => {
  // Sanitize and decode URL
  let requestPath;
  try {
    requestPath = decodeURIComponent(req.url.split("?")[0]);
  } catch {
    res.statusCode = 400;
    res.end("Bad Request");
    return;
  }

  // 1. Mail Relay Endpoint (bypasses Render SMTP port blocking)
  if (
    (requestPath === "/mail-relay.php" || requestPath === "/api/relay-mail" || requestPath === "/relay-mail") &&
    req.method === "POST"
  ) {
    const authSecret = req.headers["x-mail-secret"];
    const expectedSecret = process.env.MAIL_RELAY_SECRET || "mizan-secure-mail-relay-key-2026-safe";
    if (!authSecret || authSecret !== expectedSecret) {
      setSecurityHeaders(res);
      res.statusCode = 403;
      res.setHeader("Content-Type", "application/json; charset=utf-8");
      res.end(JSON.stringify({ error: "Forbidden: Invalid mail relay secret." }));
      return;
    }

    let bodyData = "";
    req.on("data", (chunk) => {
      bodyData += chunk;
      if (bodyData.length > 1024 * 1024) {
        req.destroy();
      }
    });

    req.on("end", async () => {
      try {
        const payload = JSON.parse(bodyData);
        if (!payload.to || !payload.subject) {
          setSecurityHeaders(res);
          res.statusCode = 400;
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(JSON.stringify({ error: "Invalid payload. 'to' and 'subject' required." }));
          return;
        }

        const result = await sendSmtpViaHostinger({
          to: payload.to,
          subject: payload.subject,
          text: payload.text || "",
          html: payload.html || "",
        });

        setSecurityHeaders(res);
        res.statusCode = 200;
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        res.end(JSON.stringify({ status: "sent", method: "node_tls_smtp", ...result }));
      } catch (err) {
        setSecurityHeaders(res);
        res.statusCode = 500;
        res.setHeader("Content-Type", "application/json; charset=utf-8");
        res.end(JSON.stringify({ error: "Email relay delivery failed.", message: err.message }));
      }
    });
    return;
  }

  // 2. API Reverse Proxy: Forward all /api/ requests directly to Render
  if (requestPath.startsWith("/api/")) {
    proxyApiRequest(req, res);
    return;
  }

  // 3. Health check endpoint for Hostinger monitoring
  if (requestPath === "/node-health" || requestPath === "/server-status") {
    setSecurityHeaders(res);
    res.statusCode = 200;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(
      JSON.stringify({
        status: "ok",
        uptime_seconds: process.uptime(),
        node_version: process.version,
        static_root: STATIC_ROOT,
        backend_proxy: BACKEND_URL,
        timestamp: new Date().toISOString(),
      })
    );
    return;
  }

  if (req.method !== "GET" && req.method !== "HEAD") {
    res.statusCode = 405;
    res.setHeader("Allow", "GET, HEAD");
    res.end("Method Not Allowed");
    return;
  }

  // Prevent directory traversal
  const safePath = path.normalize(requestPath).replace(/^(\.\.[/\\])+/, "");
  const targetPath = path.join(STATIC_ROOT, safePath);

  // If request matches existing static file, serve it directly
  fs.stat(targetPath, (err, stats) => {
    if (!err && stats.isFile()) {
      sendFile(req, res, targetPath);
    } else {
      // SPA Fallback: Any route like /datasets, /experiments, /login -> index.html
      sendSpaFallback(req, res);
    }
  });
});

server.listen(PORT, HOST, () => {
  console.log(`[Mizan Node.js Server] Listening on http://${HOST}:${PORT}`);
  console.log(`[Mizan Node.js Server] Ready to serve React SPA on Hostinger.`);
});
