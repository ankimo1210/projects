// Server Component: this runs on the server for every request. The task
// list below is already HTML when it reaches the browser — check with
//   curl -s localhost:3000 | grep 'Learn Next.js'
// A plain Vite+React app serves an empty <div id="root"> instead.
import { listTasks } from '../lib/store';
import TaskApp from './TaskApp';

export const dynamic = 'force-dynamic';

export default function Page() {
  const initialTasks = listTasks();
  return <TaskApp initialTasks={initialTasks} />;
}
