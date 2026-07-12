import type { Metadata } from 'next';
import type { ReactNode } from 'react';
import '@rosetta/core/styles.css';

export const metadata: Metadata = {
  title: 'Tasks — Next.js',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
