/**
 * Baileys WhatsApp bridge.
 *
 * Logs into WhatsApp as a linked device (QR on first run), forwards each
 * incoming message from the authorized number to the local core service
 * (local_server.py), and sends the reply back. No Facebook, no Selenium.
 *
 * Env:
 *   ALLOWED_WA_ID   the only number allowed to chat, digits only (e.g. 972501234567)
 *   CORE_URL        core service URL (default http://127.0.0.1:8090)
 *   LOCAL_TOKEN     optional shared secret, sent as X-Token to the core
 *
 * Run:  npm install && node index.js   (scan the QR once)
 */

import makeWASocket, {
  useMultiFileAuthState,
  downloadMediaMessage,
  DisconnectReason,
} from "baileys";
import qrcode from "qrcode-terminal";
import pino from "pino";

const CORE_URL = (process.env.CORE_URL || "http://127.0.0.1:8090").replace(/\/$/, "");
const LOCAL_TOKEN = process.env.LOCAL_TOKEN || "";
const ALLOWED = (process.env.ALLOWED_WA_ID || "").replace(/\D/g, "");

if (!ALLOWED) {
  console.error("Set ALLOWED_WA_ID (digits only, e.g. 972501234567)");
  process.exit(1);
}

async function askCore(uid, text, imageDataUri) {
  const headers = { "Content-Type": "application/json" };
  if (LOCAL_TOKEN) headers["X-Token"] = LOCAL_TOKEN;
  const res = await fetch(`${CORE_URL}/reply`, {
    method: "POST",
    headers,
    body: JSON.stringify({ uid, text, image_data_uri: imageDataUri || null }),
  });
  if (!res.ok) return `⚠️ core error ${res.status}`;
  const data = await res.json();
  return data.reply;
}

function extractText(m) {
  return (
    m.conversation ||
    m.extendedTextMessage?.text ||
    m.imageMessage?.caption ||
    ""
  );
}

async function start() {
  const { state, saveCreds } = await useMultiFileAuthState("auth");
  const sock = makeWASocket({
    auth: state,
    logger: pino({ level: "silent" }),
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", (u) => {
    const { connection, lastDisconnect, qr } = u;
    if (qr) {
      console.log("סרוק את ה-QR הבא מ-WhatsApp → מכשירים מקושרים:");
      qrcode.generate(qr, { small: true });
    }
    if (connection === "close") {
      const code = lastDisconnect?.error?.output?.statusCode;
      const loggedOut = code === DisconnectReason.loggedOut;
      console.log("connection closed:", code, "| reconnect:", !loggedOut);
      if (!loggedOut) start();
      else console.log("logged out — delete the auth/ folder and re-run to re-link.");
    } else if (connection === "open") {
      console.log("✅ מחובר ל-WhatsApp. מאזין להודעות מ-" + ALLOWED);
    }
  });

  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    if (type !== "notify") return;
    for (const msg of messages) {
      if (!msg.message || msg.key.fromMe) continue;
      const jid = msg.key.remoteJid;
      if (!jid || jid.endsWith("@g.us") || jid === "status@broadcast") continue;

      const num = jid.split("@")[0].split(":")[0];
      if (num !== ALLOWED) {
        console.log("ignored message from", num);
        continue;
      }

      const m = msg.message;
      const text = extractText(m);
      let imageDataUri = null;

      try {
        await sock.readMessages([msg.key]);
        await sock.sendPresenceUpdate("composing", jid);

        if (m.imageMessage) {
          const buf = await downloadMediaMessage(msg, "buffer", {});
          const mime = (m.imageMessage.mimetype || "image/jpeg").split(";")[0];
          imageDataUri = `data:${mime};base64,${buf.toString("base64")}`;
        }

        const reply = await askCore(num, text, imageDataUri);
        await sock.sendPresenceUpdate("paused", jid);
        await sock.sendMessage(jid, { text: reply });
      } catch (e) {
        console.error("handler error:", e);
        try {
          await sock.sendMessage(jid, { text: `⚠️ שגיאה: ${e.message}` });
        } catch {}
      }
    }
  });
}

start();
