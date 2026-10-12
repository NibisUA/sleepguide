import { beforeEach, describe, expect, it, vi } from "vitest";
vi.mock("./telegram", () => ({ getInitData: () => "", getTelegramLanguage: () => "en" }));

const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
beforeEach(() => { vi.resetModules(); sessionStorage.clear(); });

describe("account deletion session boundary", () => {
  it("normalizes network failures so mutation cards can show them", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network failed")));
    const module = await import("./api");
    await expect(module.api("/me")).rejects.toMatchObject({ status: 0, code: "network_error" });
    expect(module.isSessionClosed()).toBe(false);
  });
  it("blocks automatic login and survives a page reload after deletion", async () => {
    const fetch = vi.fn().mockResolvedValueOnce(json({ access_token: "jwt" }))
      .mockResolvedValueOnce(json({ id: 1 })).mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetch);
    const module = await import("./api");
    await module.api("/me");
    await module.api("/me", { method: "DELETE", body: '{"confirm":true}' });
    expect(module.isSessionClosed()).toBe(true);
    await expect(module.api("/me")).rejects.toMatchObject({ code: "account_deleted" });
    vi.resetModules();
    const reloaded = await import("./api");
    expect(reloaded.isSessionClosed()).toBe(true);
    await expect(reloaded.api("/insights")).rejects.toMatchObject({ code: "account_deleted" });
    expect(fetch).toHaveBeenCalledTimes(3);
  });

  it("does not let a stale in-flight 401 recreate an erased account", async () => {
    let finish!: (value: Response) => void;
    const pending = new Promise<Response>(resolve => { finish = resolve; });
    const fetch = vi.fn().mockResolvedValueOnce(json({ access_token: "jwt" }))
      .mockResolvedValueOnce(json({ id: 1 })).mockReturnValueOnce(pending)
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetch);
    const module = await import("./api");
    await module.api("/me");
    const read = module.api("/insights");
    const rejection = expect(read).rejects.toMatchObject({ code: "account_deleted" });
    await module.api("/me", { method: "DELETE", body: '{"confirm":true}' });
    finish(json({ detail: { code: "invalid_token" } }, 401));
    await rejection;
    expect(fetch).toHaveBeenCalledTimes(4);
  });

  it("keeps a usable session if deletion fails", async () => {
    const fetch = vi.fn().mockResolvedValueOnce(json({ access_token: "jwt" }))
      .mockResolvedValueOnce(json({ id: 1 })).mockResolvedValueOnce(json({}, 500))
      .mockResolvedValueOnce(json({ id: 1 }));
    vi.stubGlobal("fetch", fetch);
    const module = await import("./api");
    await module.api("/me");
    await expect(module.api("/me", { method: "DELETE" })).rejects.toMatchObject({ status: 500 });
    expect(module.isSessionClosed()).toBe(false);
    expect(await module.api("/me")).toEqual({ id: 1 });
  });

  it("only resumes login after an explicit start-again action", async () => {
    sessionStorage.setItem("sleepguide.deleted", "1");
    const fetch = vi.fn().mockResolvedValueOnce(json({ access_token: "new" })).mockResolvedValueOnce(json({ id: 2 }));
    vi.stubGlobal("fetch", fetch);
    const module = await import("./api");
    module.resumeSession();
    expect(await module.api("/me")).toEqual({ id: 2 });
    expect(fetch).toHaveBeenCalledTimes(2);
  });
});
