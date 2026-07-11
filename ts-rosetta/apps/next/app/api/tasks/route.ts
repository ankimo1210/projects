// Route Handler: Next.js's built-in server API — the same role Express or
// Nest play, but living inside the web app project.
import { NextResponse } from 'next/server';
import { listTasks, createOne } from '../../../lib/store';

export function GET() {
  return NextResponse.json(listTasks());
}

export async function POST(req: Request) {
  const body = (await req.json()) as { title?: unknown };
  const title = typeof body.title === 'string' ? body.title.trim() : '';
  if (!title) {
    return NextResponse.json({ error: 'title is required' }, { status: 400 });
  }
  return NextResponse.json(createOne(title), { status: 201 });
}
