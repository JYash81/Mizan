/**
 * Mizan Production Frontend Node.js Server for Hostinger
 * 
 * Zero-dependency, high-performance static file server and SPA routing engine.
 * Fully compatible with Hostinger hPanel Node.js (Phusion Passenger / Reverse Proxy).
 */

import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = Number(process.env.PORT) || 3000;
const HOST = process.env.HOST || "0.0.0.0";

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

const server = http.createServer((req, res) => {
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.statusCode = 405;
    res.setHeader("Allow", "GET, HEAD");
    res.end("Method Not Allowed");
    return;
  }

  // Sanitize and decode URL
  let requestPath;
  try {
    requestPath = decodeURIComponent(req.url.split("?")[0]);
  } catch {
    res.statusCode = 400;
    res.end("Bad Request");
    return;
  }

  // Health check endpoint for Hostinger monitoring
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
        timestamp: new Date().toISOString(),
      })
    );
    return;
  }

  // Prevent directory traversal
  const safePath = path.normalize(requestPath).replace(/^(\.\.[/\\])+/, "");
  const targetPath = path.join(STATIC_ROOT, safePath);

  // If request matches existing file, serve it directly
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
