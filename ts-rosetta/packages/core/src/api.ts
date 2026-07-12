import type { Task } from './types';

/**
 * Tiny REST client shared by every UI implementation.
 * Matches the contract implemented by both server-express and server-nest:
 *   GET    /tasks          -> Task[]
 *   POST   /tasks {title}  -> Task (201)
 *   PATCH  /tasks/:id {done} -> Task
 *   DELETE /tasks/:id      -> 204
 */
export function createTasksApi(baseUrl: string) {
  const url = (path: string) => `${baseUrl.replace(/\/$/, '')}${path}`;

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(url(path), {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    });
    if (!res.ok) throw new Error(`${init?.method ?? 'GET'} ${path} -> ${res.status}`);
    return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
  }

  return {
    list: () => request<Task[]>('/tasks'),
    add: (title: string) =>
      request<Task>('/tasks', { method: 'POST', body: JSON.stringify({ title }) }),
    setDone: (id: string, done: boolean) =>
      request<Task>(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify({ done }) }),
    remove: (id: string) => request<void>(`/tasks/${id}`, { method: 'DELETE' }),
  };
}

export type TasksApi = ReturnType<typeof createTasksApi>;
