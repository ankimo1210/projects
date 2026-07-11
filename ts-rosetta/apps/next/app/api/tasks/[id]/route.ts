import { NextResponse } from 'next/server';
import { setDone, removeOne } from '../../../../lib/store';

type Params = { params: Promise<{ id: string }> };

export async function PATCH(req: Request, { params }: Params) {
  const { id } = await params;
  const body = (await req.json()) as { done?: unknown };
  if (typeof body.done !== 'boolean') {
    return NextResponse.json({ error: 'done (boolean) is required' }, { status: 400 });
  }
  const task = setDone(id, body.done);
  if (!task) return NextResponse.json({ error: 'not found' }, { status: 404 });
  return NextResponse.json(task);
}

export async function DELETE(_req: Request, { params }: Params) {
  const { id } = await params;
  if (!removeOne(id)) return NextResponse.json({ error: 'not found' }, { status: 404 });
  return new Response(null, { status: 204 });
}
