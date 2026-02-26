'use client'
import { useState, useEffect } from 'react'
import { Search, Bell, User, Settings, Globe, Command, Sun, Moon } from 'lucide-react'

export default function TopBar() {
    const [scrolled, setScrolled] = useState(false)
    const [time, setTime] = useState(new Date())

    useEffect(() => {
        const handleScroll = () => setScrolled(window.scrollY > 20)
        window.addEventListener('scroll', handleScroll)
        const timer = setInterval(() => setTime(new Date()), 1000)
        return () => {
            window.removeEventListener('scroll', handleScroll)
            clearInterval(timer)
        }
    }, [])

    return (
        <header className={`sticky top-0 z-40 w-full transition-all duration-300 px-8 py-5 flex items-center justify-between ${scrolled ? 'bg-[#020617]/80 backdrop-blur-xl border-b border-white/5 shadow-2xl shadow-black/50' : 'bg-transparent'
            }`}>
            {/* Search Block */}
            <div className="flex-1 max-w-xl">
                <div className="relative group">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500 group-focus-within:text-green-500 transition-colors" />
                    <input
                        type="text"
                        placeholder="Search environmental datasets, predictions, or compliance reports..."
                        className="w-full bg-white/5 border border-white/5 rounded-2xl py-2.5 pl-12 pr-12 text-sm text-gray-300 focus:outline-none focus:ring-2 focus:ring-green-500/20 focus:border-green-500/40 focus:bg-white/10 transition-all placeholder:text-gray-600 font-medium"
                    />
                    <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1.5 bg-black/40 px-2 py-1 rounded-lg border border-white/10 px-2">
                        <Command className="w-3 h-3 text-gray-500" />
                        <span className="text-[10px] font-black text-gray-500 uppercase">K</span>
                    </div>
                </div>
            </div>

            {/* Right Group */}
            <div className="flex items-center gap-6">
                {/* Time & Region */}
                <div className="hidden xl:flex flex-col items-end">
                    <div className="flex items-center gap-2 text-white font-black text-sm tabular-nums tracking-tight">
                        {time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true })}
                        <span className="text-[10px] text-gray-500 font-bold uppercase ml-1">IST</span>
                    </div>
                    <div className="flex items-center gap-1.5 text-[10px] font-bold text-gray-500 uppercase tracking-widest mt-1">
                        <Globe className="w-3 h-3 text-green-500" />
                        EMEA Region <span className="text-gray-700">/</span> Node-04
                    </div>
                </div>

                <div className="w-px h-8 bg-white/10 mx-2" />

                {/* Direct Actions */}
                <div className="flex items-center gap-2">
                    <button className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 text-gray-400 hover:text-white transition-all">
                        <Moon className="w-4.5 h-4.5" />
                    </button>
                    <button className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 text-gray-400 hover:text-white transition-all relative">
                        <Bell className="w-4.5 h-4.5" />
                        <span className="absolute top-2.5 right-2.5 w-1.5 h-1.5 bg-red-500 rounded-full border border-[#020617]" />
                    </button>
                    <button className="p-2.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 text-gray-400 hover:text-white transition-all">
                        <Settings className="w-4.5 h-4.5" />
                    </button>
                </div>

                {/* User Profile */}
                <button className="flex items-center gap-3 pl-2 pr-4 py-1.5 rounded-2xl bg-gradient-to-br from-green-500/10 to-emerald-500/5 border border-green-500/20 hover:border-green-500/40 transition-all group">
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-green-400 to-emerald-600 flex items-center justify-center shadow-lg shadow-green-500/20">
                        <User className="w-5 h-5 text-white" />
                    </div>
                    <div className="text-left">
                        <p className="text-xs font-black text-white leading-none">D. Hindoliya</p>
                        <p className="text-[10px] font-bold text-green-500/80 uppercase tracking-widest mt-1 group-hover:text-green-400">Chief Analyt.</p>
                    </div>
                </button>
            </div>
        </header>
    )
}
