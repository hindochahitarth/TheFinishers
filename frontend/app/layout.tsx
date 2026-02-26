import type { Metadata } from 'next'
import './globals.css'
import Sidebar from '@/components/Sidebar'
import TopBar from '@/components/TopBar'

export const metadata: Metadata = {
    title: 'GreenPulse AI — Environmental Intelligence Platform',
    description: 'Real-time AI-driven environmental monitoring: AQI, weather, traffic, forecasting, compliance, and AI-powered insights.',
    keywords: ['air quality', 'AQI', 'environmental monitoring', 'pollution', 'WHO', 'CPCB'],
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="en">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
            </head>
            <body className="flex h-screen overflow-hidden">
                <Sidebar />
                <div className="flex flex-col flex-1 min-w-0">
                    <TopBar />
                    <main className="flex-1 overflow-y-auto p-6 scroll-smooth custom-scrollbar">
                        {children}
                    </main>
                </div>
            </body>
        </html>
    )
}
