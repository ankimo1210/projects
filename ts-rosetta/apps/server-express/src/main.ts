// Express: the whole API fits in one procedural file. No structure is
// imposed — routes, state, and wiring live wherever you put them.
// Contrast with server-nest, which spreads the same API across
// module / controller / service / DTO classes.
import express from 'express';
import cors from 'cors';
import {
  type Task,
  createTask,
  addTask,
  deleteTask,
  computeStats,
} from '@rosetta/core';

const PORT = 4000;
const app = express();
app.use(cors());
app.use(express.json());

// In-memory store: a plain mutable variable in module scope.
let tasks: Task[] = [];

app.get('/tasks', (_req, res) => {
  res.json(tasks);
});

app.get('/stats', (_req, res) => {
  res.json(computeStats(tasks));
});

app.post('/tasks', (req, res) => {
  const title = typeof req.body?.title === 'string' ? req.body.title.trim() : '';
  if (!title) {
    res.status(400).json({ error: 'title is required' });
    return;
  }
  const task = createTask(title);
  tasks = addTask(tasks, task);
  res.status(201).json(task);
});

app.patch('/tasks/:id', (req, res) => {
  const task = tasks.find((t) => t.id === req.params.id);
  if (!task) {
    res.status(404).json({ error: 'not found' });
    return;
  }
  if (typeof req.body?.done !== 'boolean') {
    res.status(400).json({ error: 'done (boolean) is required' });
    return;
  }
  task.done = req.body.done;
  res.json(task);
});

app.delete('/tasks/:id', (req, res) => {
  if (!tasks.some((t) => t.id === req.params.id)) {
    res.status(404).json({ error: 'not found' });
    return;
  }
  tasks = deleteTask(tasks, req.params.id);
  res.status(204).end();
});

app.listen(PORT, () => {
  console.log(`[express] listening on http://localhost:${PORT}`);
});
