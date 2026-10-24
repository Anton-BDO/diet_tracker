import { api } from "./api.js";

export function createAuthStore({ client = api, storage = globalThis.localStorage } = {}) {
  let state = Object.freeze({ profile: null, pending: false, error: null, daySummary: null });
  const listeners = new Set();
  const tokenKey = client.tokenKey ?? "token";

  function update(changes) {
    state = Object.freeze({ ...state, ...changes });
    listeners.forEach(listener => listener(state));
  }

  function clearSession() {
    storage?.removeItem(tokenKey);
    update({ profile: null, pending: false, error: null, daySummary: null });
  }

  async function authenticate(method, data) {
    if (state.pending) throw new Error("Дождитесь завершения запроса");
    update({ pending: true, error: null });
    try {
      const result = await client[method](data);
      if (typeof result?.token !== "string" || !result.token) {
        throw new Error("Сервер не вернул токен. Попробуйте ещё раз");
      }
      storage.setItem(tokenKey, result.token);
      const profile = result.profile ?? await client.profile();
      if (!profile?.id || !profile.norm) {
        throw new Error("Не удалось получить профиль. Попробуйте ещё раз");
      }
      update({ profile });
      return profile;
    } catch (error) {
      storage?.removeItem(tokenKey);
      update({ profile: null, pending: false, error });
      throw error;
    } finally {
      if (state.pending) update({ pending: false });
    }
  }

  return {
    getState: () => state,
    isAuthenticated: () => Boolean(state.profile && storage?.getItem(tokenKey)),
    subscribe(listener) {
      listeners.add(listener);
      listener(state);
      return () => listeners.delete(listener);
    },
    dismissError: () => update({ error: null }),
    clearSession,
    login: data => authenticate("login", data),
    register: data => authenticate("register", data),
    
    // ВОТ НАШ НОВЫЙ МЕТОД:
    async loadDashboard() {
      update({ pending: true, error: null });
      try {
        const data = await client.daySummary();
        update({ daySummary: data });
      } catch (error) {
        update({ error });
      } finally {
        update({ pending: false });
      }
    },

    async restore() {
      if (!storage?.getItem(tokenKey)) return null;
      update({ pending: true, error: null });
      try {
        const profile = await client.profile();
        if (!profile?.id || !profile.norm) throw new Error("Не удалось получить профиль");
        update({ profile });
        return profile;
      } catch (error) {
        if (error.status === 401) storage?.removeItem(tokenKey);
        update({ profile: null, error });
        return null;
      } finally {
        update({ pending: false });
      }
    },
    async logout() {
      try {
        await client.logout();
      } finally {
        clearSession();
      }
    },
  };
}

export const store = createAuthStore();
