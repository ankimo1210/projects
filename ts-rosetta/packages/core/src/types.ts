/** A single task item. Shared by every UI and server implementation. */
export interface Task {
  id: string;
  title: string;
  done: boolean;
  createdAt: number; // epoch ms
}

/** Visibility filter applied to the task list. */
export type Filter = 'all' | 'active' | 'done';

/** Aggregate counts displayed by every implementation. */
export interface Stats {
  total: number;
  active: number;
  done: number;
}
