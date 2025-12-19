import './globals.css'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Chat UI',
  description: 'A simple chat interface for interacting with the RAG backend',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}