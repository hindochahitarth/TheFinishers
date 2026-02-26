'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
    Activity, BarChart3, ShieldCheck, Bell, Bot, AlertCircle, ChevronRight, Zap, Leaf, Layers
} from 'lucide-react'

const navItems = [
    { href: '/', icon: Activity, label: 'Dashboard', desc: 'Real-time intelligence' },
    { href: '/forecast', icon: BarChart3, label: 'Predictive', desc: 'AI-driven forecasting' },
    { href: '/compliance', icon: ShieldCheck, label: 'Regulatory', desc: 'Global standards' },
    { href: '/alerts', icon: Bell, label: 'Incidents', desc: 'Active notifications' },
    { href: '/anomalies', icon: AlertCircle, label: 'Detections', desc: 'Pattern analysis' },
    { href: '/agent', icon: Bot, label: 'GreenPulse AI', desc: 'Cognitive assistant' },
]

export default function Sidebar() {
    const pathname = usePathname()

    return (
        <aside className="w-72 flex-shrink-0 flex flex-col h-screen border-r border-white/5 relative z-50 overflow-hidden"
            style={{ background: 'linear-gradient(180deg, #020617 0%, #01040f 100%)' }}>

            {/* Glossy overlay */}
            <div className="absolute top-0 left-0 w-full h-64 bg-gradient-to-b from-green-500/5 to-transparent pointer-events-none" />

            {/* Logo Section */}
            <div className="relative px-8 py-10">
                <div className="flex items-center gap-4">
                    <div className="relative group">
                        <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-green-400 to-emerald-600 flex items-center justify-center shadow-xl shadow-green-500/20 group-hover:scale-105 transition-transform duration-500">
                            <Leaf className="w-6 h-6 text-white" />
                        </div>
                        <div className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-green-500 border-2 border-[#020617] shadow-lg shadow-green-500/30">
                            <div className="w-full h-full rounded-full bg-green-400 animate-ping opacity-75" />
                        </div>
                    </div>
                    <div>
                        <h1 className="text-lg font-black text-white tracking-tight leading-none">GreenPulse <span className="text-green-500">AI</span></h1>
                        <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mt-1.5 opacity-60">Environmental Intel</p>
                    </div>
                </div>
            </div>

            {/* Navigation */}
            <nav className="flex-1 px-4 space-y-1 overflow-y-auto custom-scrollbar">
                <div className="px-4 mb-4">
                    <span className="text-[10px] font-black text-gray-600 uppercase tracking-[0.2em]">Navigation</span>
                </div>
                {navItems.map(({ href, icon: Icon, label, desc }) => {
                    const active = pathname === href
                    return (
                        <Link key={href} href={href}
                            className={`group relative flex items-center gap-4 px-4 py-4 rounded-2xl transition-all duration-300 ${active
                                ? 'bg-green-500/10 text-white'
                                : 'text-gray-500 hover:text-gray-200'
                                }`}>
                            {active && (
                                <div className="absolute left-0 top-3 bottom-3 w-1 bg-green-500 rounded-full shadow-[0_0_12px_rgba(34,197,94,0.6)]" />
                            )}
                            <div className={`p-2 rounded-xl transition-colors ${active ? 'bg-green-500/10' : 'group-hover:bg-white/5'}`}>
                                <Icon className={`w-4.5 h-4.5 transition-transform group-hover:scale-110 ${active ? 'text-green-400' : 'text-gray-400 group-hover:text-gray-200'}`} />
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className={`text-sm font-bold tracking-tight ${active ? 'text-white' : ''}`}>{label}</div>
                                <div className="text-[10px] font-medium opacity-50 truncate">{desc}</div>
                            </div>
                            {active && (
                                <div className="p-1 rounded-full bg-green-500/10">
                                    <ChevronRight className="w-3 h-3 text-green-500" />
                                </div>
                            )}
                        </Link>
                    )
                })}
            </nav>

            {/* Bottom Status Panel */}
            <div className="p-6 border-t border-white/5 bg-black/20">
                <div className="glass-card p-4 bg-white/[0.02] border-white/5 relative overflow-hidden group">
                    <div className="absolute top-0 right-0 p-4 transform translate-x-1/2 -translate-y-1/2 opacity-20 group-hover:opacity-40 transition-opacity">
                        <Layers className="w-16 h-16 text-green-500" />
                    </div>
                    <div className="flex items-center gap-2.5 mb-3">
                        <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)] animate-pulse" />
                        <span className="text-[10px] font-black text-white uppercase tracking-widest">Global Status</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                        {['API', 'INF', 'SEC'].map(s => (
                            <div key={s} className="flex flex-col items-center py-2 bg-black/40 rounded-lg border border-white/5">
                                <span className="text-[8px] font-black text-gray-600 mb-1">{s}</span>
                                <div className="w-1.5 h-1.5 rounded-full bg-green-500/80" />
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </aside>
    )
}
