import { Injectable, NotFoundException } from '@nestjs/common';
import {
  type Task,
  type Stats,
  createTask,
  addTask,
  deleteTask,
  computeStats,
} from '@rosetta/core';

/**
 * The in-memory store, isolated behind an injectable class.
 * Compare with server-express, where this is a module-scope variable.
 */
@Injectable()
export class TasksService {
  private tasks: Task[] = [];

  findAll(): Task[] {
    return this.tasks;
  }

  stats(): Stats {
    return computeStats(this.tasks);
  }

  create(title: string): Task {
    const task = createTask(title.trim());
    this.tasks = addTask(this.tasks, task);
    return task;
  }

  setDone(id: string, done: boolean): Task {
    const task = this.tasks.find((t) => t.id === id);
    if (!task) throw new NotFoundException();
    task.done = done;
    return task;
  }

  remove(id: string): void {
    if (!this.tasks.some((t) => t.id === id)) throw new NotFoundException();
    this.tasks = deleteTask(this.tasks, id);
  }
}
