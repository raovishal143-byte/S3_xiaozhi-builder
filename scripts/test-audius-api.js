#!/usr/bin/env node
// Read-only Audius API smoke test. Does not download or save music.
const query = process.argv.slice(2).join(" ").trim() || "Tum Hi Ho";
const base = "https://api.audius.co/v1";

async function main() {
  const searchUrl = new URL(base + "/tracks/search");
  searchUrl.searchParams.set("query", query);
  searchUrl.searchParams.set("limit", "8");

  console.log("Searching Audius for:", query);
  const search = await fetch(searchUrl, { headers: { Accept: "application/json" } });
  if (!search.ok) throw new Error(`Search returned HTTP ${search.status}`);
  const payload = await search.json();
  const tracks = Array.isArray(payload.data) ? payload.data : [];
  console.log(`Search returned ${tracks.length} result(s).`);

  for (const [i, track] of tracks.entries()) {
    console.log(`${i + 1}. ${track.title || "(untitled)"} — ${track.user?.name || "unknown artist"} [id=${track.id}]`);
  }

  if (!tracks.length) {
    console.log("No matching Audius catalogue entry was returned. API search is reachable, but this song is not confirmed available.");
    return;
  }

  const candidate = tracks.find(t => t.id && t.is_streamable !== false) || tracks.find(t => t.id);
  if (!candidate) {
    console.log("Search works, but no result included a usable track ID.");
    return;
  }

  const streamUrl = new URL(`${base}/tracks/${encodeURIComponent(candidate.id)}/stream`);
  const stream = await fetch(streamUrl, {
    headers: { Accept: "audio/mpeg", Range: "bytes=0-1023" },
    redirect: "follow"
  });
  const contentType = stream.headers.get("content-type") || "(not supplied)";
  console.log("Stream test track:", candidate.title || candidate.id);
  console.log("Final stream URL host:", new URL(stream.url).host);
  console.log("HTTP status:", stream.status);
  console.log("Content-Type:", contentType);
  console.log("Content-Range:", stream.headers.get("content-range") || "(not supplied)");
  if (!stream.ok) throw new Error(`Stream endpoint returned HTTP ${stream.status}`);
  if (!/audio|octet-stream/i.test(contentType)) {
    console.log("WARNING: response content type is not recognisably audio; inspect before firmware integration.");
  }
  if (stream.body) {
    const reader = stream.body.getReader();
    const first = await reader.read();
    console.log("First audio payload bytes:", first.value?.byteLength || 0);
    await reader.cancel();
    if (!first.value?.byteLength) throw new Error("Stream returned no audio payload bytes");
  }
  console.log("PASS: Audius search and stream endpoint responded. This does not yet prove ESP32 decoder compatibility or catalogue rights for other tracks.");
}

main().catch(err => {
  console.error("FAIL:", err.message);
  process.exitCode = 1;
});

// Workflow trigger: harmless comment-only update for the Audius smoke test.
