import { NextRequest, NextResponse } from 'next/server'

const AGENT_ENDPOINT = process.env.AGENT_ENDPOINT!

export async function POST(req: NextRequest) {
  const { message } = await req.json()
  if (!message?.trim()) {
    return NextResponse.json({ error: 'Thiếu nội dung câu hỏi' }, { status: 400 })
  }

  const upstream = await fetch(AGENT_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })

  if (!upstream.ok) {
    const text = await upstream.text()
    return NextResponse.json({ error: `Agent lỗi: ${upstream.status} ${text}` }, { status: 502 })
  }

  const data = await upstream.json()
  return NextResponse.json(data)
}
