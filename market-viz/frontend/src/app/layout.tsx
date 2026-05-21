import type { Metadata } from 'next'
import { Geist_Mono } from 'next/font/google'
import './globals.css'
import Sidebar from '@/components/layout/Sidebar'
import Providers from '@/components/layout/Providers'

const mono = Geist_Mono({ variable: '--font-mono', subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Market Viz',
  description: 'Personal market visualization & analysis',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja" className={`${mono.variable} h-full`}>
      <body className="min-h-full flex bg-zinc-950 text-zinc-100 font-mono">
        <Providers>
          <Sidebar />
          <main className="flex-1 overflow-auto p-6">{children}</main>
        </Providers>
      </body>
    </html>
  )
}
