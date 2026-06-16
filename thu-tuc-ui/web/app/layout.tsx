import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Trợ lý Thủ tục Hành chính',
  description: 'Tra cứu thủ tục hành chính Việt Nam: giấy tờ, địa điểm, thời gian, lệ phí',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi">
      <body className="bg-gray-50 h-full">{children}</body>
    </html>
  )
}
