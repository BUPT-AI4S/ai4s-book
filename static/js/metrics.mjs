const API = "https://events.vercount.one/api/v2/log";
const VISITOR_COOKIE = "vercount_uv_ai4s_book";
const CHAPTER_ID = /^[A-Za-z0-9_-]+$/;

export function siteRoot(href = location.href) {
  const url = new URL(href);
  url.search = "";
  url.hash = "";
  if (url.pathname.endsWith("/index.html")) url.pathname = url.pathname.slice(0, -"index.html".length);
  else if (!url.pathname.endsWith("/")) url.pathname = url.pathname.slice(0, url.pathname.lastIndexOf("/") + 1);
  return url;
}

export function homeAddress(href = location.href) {
  return siteRoot(href).href;
}

export function chapterAddress(id, href = location.href) {
  if (typeof id !== "string" || !CHAPTER_ID.test(id)) throw new Error("Invalid chapter");
  // VerCount keeps the path and drops the query, so every read.html?chapter= URL would share one count.
  return new URL("visits/" + id, siteRoot(href)).href;
}

function consumeNewVisitor() {
  const seen = document.cookie.split("; ").some((part) => part.startsWith(`${VISITOR_COOKIE}=1`));
  if (!seen) document.cookie = `${VISITOR_COOKIE}=1; path=/; max-age=31536000; samesite=lax`;
  return !seen;
}

function readCount(payload) {
  const page = Number(payload && payload.data ? payload.data.page_pv : NaN);
  return Number.isFinite(page) ? page : null;
}

async function postCount(url) {
  const response = await fetch(API, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, isNewUv: consumeNewVisitor() }),
    keepalive: true,
  });
  if (!response.ok) throw new Error(String(response.status));
  return readCount(await response.json());
}

async function getCount(url) {
  const response = await fetch(`${API}?url=${encodeURIComponent(url)}`, { cache: "no-store" });
  if (!response.ok) throw new Error(String(response.status));
  return readCount(await response.json());
}

export function formatCount(value) {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toLocaleString("zh-CN");
}

export function recordHome() {
  postCount(homeAddress()).catch(() => {});
}

export function recordChapter(id) {
  let url;
  try { url = chapterAddress(id); } catch { return; }
  postCount(url).catch(() => {});
}

export async function readHome() {
  try { return await getCount(homeAddress()); } catch { return null; }
}

export async function readChapter(id) {
  try { return await getCount(chapterAddress(id)); } catch { return null; }
}
