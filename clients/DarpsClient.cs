// Reference DARPS client for a C# host (Unity, etc.). Not compiled or tested by
// the DARPS repo — it documents the wire contract (SPEC §13–14) in the host's
// language. Drop it into your project and adapt.
//
// DARPS is a conversation layer: YOU own the world (location, presence, items,
// progress flags) and send a small snapshot per call; DARPS owns the narrative
// (what characters know/hide, facts learned, attitudes, history) and returns
// prose + deltas for you to mirror. `deltas.tracks` is
// {track_id:{character_id:new_value}}.
//
// Lifecycle:
//   1. On boot, launch the sidecar:  darps serve <pack> --port 8080
//      (bundle a frozen `darps` binary so players need no Python).
//   2. var darps = new DarpsClient("http://127.0.0.1:8080");
//      await darps.WaitHealthy();
//      var session = await darps.NewSession();          // or NewSession(savedState)
//   3. Per conversation, YOU supply the addressee + your world snapshot:
//      var world = new { present = new[]{"blacksmith","guard"},
//                        location = "forge",
//                        carried = new[]{"coin_purse"},
//                        in_reach = new[]{"anvil","broken_sword"},
//                        flags = new { sword_stolen = true } };
//      var res = await darps.Talk(session, "blacksmith",
//                                 "did you see who took the sword?", world);
//      // res.prose -> show as dialogue; res.deltas -> mirror into YOUR systems
//      // (e.g. a revealed fact advances a quest). Flags are how you signal
//      // progress BACK to DARPS: set one and gated knowledge activates/expires.
//   4. On save, persist await darps.GetState(session); restore via NewSession(state).

using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

public sealed class DarpsClient : IDisposable
{
    private readonly HttpClient _http;
    private readonly string _base;

    public DarpsClient(string baseUrl)
    {
        _base = baseUrl.TrimEnd('/');
        _http = new HttpClient();
    }

    private async Task<JsonElement> PostAsync(string path, object body)
    {
        var json = JsonSerializer.Serialize(body);
        using var content = new StringContent(json, Encoding.UTF8, "application/json");
        using var resp = await _http.PostAsync(_base + path, content);
        var text = await resp.Content.ReadAsStringAsync();
        if (!resp.IsSuccessStatusCode)
            throw new Exception($"DARPS {path} -> {(int)resp.StatusCode}: {text}");
        return JsonDocument.Parse(text).RootElement.Clone();
    }

    public async Task<bool> WaitHealthy(int attempts = 40, int delayMs = 250)
    {
        for (var i = 0; i < attempts; i++)
        {
            try
            {
                using var resp = await _http.GetAsync(_base + "/health");
                if (resp.IsSuccessStatusCode) return true;
            }
            catch { /* sidecar not up yet */ }
            await Task.Delay(delayMs);
        }
        return false;
    }

    /// New session, or restore one from a previously saved state blob.
    public async Task<string> NewSession(object savedState = null)
    {
        var body = savedState == null ? (object)new { } : new { state = savedState };
        var res = await PostAsync("/session", body);
        return res.GetProperty("session").GetString();
    }

    // world: any object matching SPEC §13 — { present, location, carried,
    // in_reach, flags }. All keys optional. tone is optional; pass null to let
    // DARPS read it from the message.
    public Task<JsonElement> Talk(string session, string character, string message,
                                  object world = null, string tone = null)
        => PostAsync("/talk", new { session, character, message, world, tone });

    // target: an item id or a loose noun ("the snifter") — DARPS resolves
    // aliases. Only items your world snapshot declares can be examined.
    public Task<JsonElement> Examine(string session, string target, string message = "",
                                     object world = null, string tone = null)
        => PostAsync("/examine", new { session, target, message, world, tone });

    public Task<JsonElement> ExamineStream(string session, string target,
                                            Action<string> onText, string message = "",
                                            object world = null, string tone = null)
        => ReadStream("/examine/stream", new { session, target, message, world, tone }, onText);

    // Streaming talk: prose arrives chunk-by-chunk (onText fires per chunk —
    // append to your dialogue box), and the returned result dict arrives once
    // the full reply has passed DARPS's validation gate. Only prose streams;
    // learned-fact deltas are ONLY trustworthy from the final result.
    public async Task<JsonElement> TalkStream(string session, string character, string message,
                                              Action<string> onText,
                                              object world = null, string tone = null)
        => await ReadStream("/talk/stream",
                            new { session, character, message, world, tone }, onText);

    private async Task<JsonElement> ReadStream(string path, object body, Action<string> onText)
    {
        var json = JsonSerializer.Serialize(body);
        using var req = new HttpRequestMessage(HttpMethod.Post, _base + path)
        { Content = new StringContent(json, Encoding.UTF8, "application/json") };
        using var resp = await _http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead);
        if (!resp.IsSuccessStatusCode)
            throw new Exception($"DARPS {path} -> {(int)resp.StatusCode}: "
                                + await resp.Content.ReadAsStringAsync());
        using var reader = new System.IO.StreamReader(await resp.Content.ReadAsStreamAsync());
        string eventName = null;
        string line;
        while ((line = await reader.ReadLineAsync()) != null)
        {
            if (line.StartsWith("event: ")) { eventName = line.Substring(7); continue; }
            if (!line.StartsWith("data: ")) continue;
            var payload = JsonDocument.Parse(line.Substring(6)).RootElement.Clone();
            if (eventName == "done") return payload;           // the §12 result dict
            if (eventName == "error")
                throw new Exception("DARPS stream error: " + payload.ToString());
            onText(payload.GetProperty("text").GetString());    // a prose chunk
            eventName = null;
        }
        throw new Exception($"DARPS {path} ended without a done frame");
    }

    // Host-authority writes (no LLM call). Push GAME events into DARPS's
    // narrative memory: a gift shifts an attitude; a cutscene teaches a fact.
    public Task<JsonElement> AdjustTrack(string session, string character,
                                         double change, string track = null)
        => PostAsync("/adjust_track", new { session, character, change, track });

    public Task<JsonElement> SetTrack(string session, string character,
                                      double value, string track = null)
        => PostAsync("/adjust_track", new { session, character, value, track });

    public Task<JsonElement> GrantFact(string session, string fact)
        => PostAsync("/grant_fact", new { session, fact });

    public Task<JsonElement> AddCanon(string session, string text)
        => PostAsync("/add_canon", new { session, text });

    public async Task<JsonElement> GetPack()
        => await GetProperty("/pack", null);

    public async Task<JsonElement> GetTracks(string session)
        => await GetProperty("/tracks?session=" + Uri.EscapeDataString(session), "tracks");

    public async Task<JsonElement> GetJournal(string session)
        => await GetProperty("/journal?session=" + Uri.EscapeDataString(session), "journal");

    private async Task<JsonElement> GetProperty(string path, string property)
    {
        using var resp = await _http.GetAsync(_base + path);
        var text = await resp.Content.ReadAsStringAsync();
        if (!resp.IsSuccessStatusCode)
            throw new Exception($"DARPS {path} -> {(int)resp.StatusCode}: {text}");
        var root = JsonDocument.Parse(text).RootElement;
        return (property == null ? root : root.GetProperty(property)).Clone();
    }

    /// The versioned, pack-bound narrative save blob DARPS owns. Persist it
    /// unchanged; restore via NewSession(state).
    public async Task<JsonElement> GetState(string session)
    {
        using var resp = await _http.GetAsync($"{_base}/state?session={Uri.EscapeDataString(session)}");
        var text = await resp.Content.ReadAsStringAsync();
        if (!resp.IsSuccessStatusCode)
            throw new Exception($"DARPS /state -> {(int)resp.StatusCode}: {text}");
        return JsonDocument.Parse(text).RootElement.GetProperty("state").Clone();
    }

    // Session-wide player-centric judgments. These are intentionally separate
    // from character attitude tracks and never enter response prompts.
    public async Task<JsonElement> GetPersona(string session)
    {
        using var resp = await _http.GetAsync(_base + "/persona?session=" +
                                               Uri.EscapeDataString(session));
        var text = await resp.Content.ReadAsStringAsync();
        if (!resp.IsSuccessStatusCode)
            throw new Exception($"DARPS /persona -> {(int)resp.StatusCode}: {text}");
        return JsonDocument.Parse(text).RootElement.GetProperty("persona").Clone();
    }

    public void Dispose() => _http.Dispose();
}
