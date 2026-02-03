import { Link } from '@tanstack/react-router'

import { useState } from 'react'
import {
  ChevronDown,
  ChevronRight,
  Home,
  Menu,
  Network,
  SquareFunction,
  StickyNote,
  X,
} from 'lucide-react'

export default function Header() {
  const [isOpen, setIsOpen] = useState(false)
  const [groupedExpanded, setGroupedExpanded] = useState<
    Record<string, boolean>
  >({})

  return (
    <>
      <header className="p-4 flex items-center bg-[#0A0B0C] border-b border-white/[0.08]">
        <button
          onClick={() => setIsOpen(true)}
          className="p-2 hover:bg-white/[0.04] rounded-lg transition-colors text-gray-400 hover:text-gray-200"
          aria-label="Open menu"
        >
          <Menu size={20} />
        </button>
        <h1 className="ml-4 text-lg font-medium">
          <Link to="/" className="text-gray-100 hover:text-white transition-colors">
            AI Chat
          </Link>
        </h1>
      </header>

      <aside
        className={`fixed top-0 left-0 h-full w-72 bg-[#0A0B0C] border-r border-white/[0.08] z-50 transform transition-transform duration-200 ease-in-out flex flex-col ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center justify-between p-4 border-b border-white/[0.08]">
          <h2 className="text-sm font-semibold text-gray-100 uppercase tracking-wide">
            Navigation
          </h2>
          <button
            onClick={() => setIsOpen(false)}
            className="p-2 hover:bg-white/[0.04] rounded-lg transition-colors text-gray-400 hover:text-gray-200"
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>

        <nav className="flex-1 p-3 overflow-y-auto">
          <Link
            to="/"
            onClick={() => setIsOpen(false)}
            className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-white/[0.04] text-gray-400 hover:text-gray-200 transition-all mb-1 text-sm"
            activeProps={{
              className:
                'flex items-center gap-3 p-2.5 rounded-lg bg-violet-500/10 text-violet-300 hover:text-violet-200 transition-all mb-1 text-sm',
            }}
          >
            <Home size={16} />
            <span className="font-medium">Home</span>
          </Link>

          {/* Demo Links Start */}

          <Link
            to="/chat/chatbot"
            onClick={() => setIsOpen(false)}
            className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-white/[0.04] text-gray-400 hover:text-gray-200 transition-all mb-1 text-sm"
            activeProps={{
              className:
                'flex items-center gap-3 p-2.5 rounded-lg bg-violet-500/10 text-violet-300 hover:text-violet-200 transition-all mb-1 text-sm',
            }}
          >
            <Network size={16} />
            <span className="font-medium">Chat - chatbot</span>
          </Link>

          <Link
            to="/demo/start/server-funcs"
            onClick={() => setIsOpen(false)}
            className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-white/[0.04] text-gray-400 hover:text-gray-200 transition-all mb-1 text-sm"
            activeProps={{
              className:
                'flex items-center gap-3 p-2.5 rounded-lg bg-violet-500/10 text-violet-300 hover:text-violet-200 transition-all mb-1 text-sm',
            }}
          >
            <SquareFunction size={16} />
            <span className="font-medium">Start - Server Functions</span>
          </Link>



          <Link
            to="/demo/start/api-request"
            onClick={() => setIsOpen(false)}
            className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-white/[0.04] text-gray-400 hover:text-gray-200 transition-all mb-1 text-sm"
            activeProps={{
              className:
                'flex items-center gap-3 p-2.5 rounded-lg bg-violet-500/10 text-violet-300 hover:text-violet-200 transition-all mb-1 text-sm',
            }}
          >
            <Network size={16} />
            <span className="font-medium">Start - API Request</span>
          </Link>

          <div className="flex flex-row justify-between">
            <Link
              to="/demo/start/ssr"
              onClick={() => setIsOpen(false)}
              className="flex-1 flex items-center gap-3 p-2.5 rounded-lg hover:bg-white/[0.04] text-gray-400 hover:text-gray-200 transition-all mb-1 text-sm"
              activeProps={{
                className:
                  'flex-1 flex items-center gap-3 p-2.5 rounded-lg bg-violet-500/10 text-violet-300 hover:text-violet-200 transition-all mb-1 text-sm',
              }}
            >
              <StickyNote size={16} />
              <span className="font-medium">Start - SSR Demos</span>
            </Link>
            <button
              className="p-2 hover:bg-white/[0.04] rounded-lg transition-colors text-gray-500 hover:text-gray-300"
              onClick={() =>
                setGroupedExpanded((prev) => ({
                  ...prev,
                  StartSSRDemo: !prev.StartSSRDemo,
                }))
              }
            >
              {groupedExpanded.StartSSRDemo ? (
                <ChevronDown size={16} />
              ) : (
                <ChevronRight size={16} />
              )}
            </button>
          </div>
          {groupedExpanded.StartSSRDemo && (
            <div className="flex flex-col ml-4">
              <Link
                to="/demo/start/ssr/spa-mode"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-white/[0.04] text-gray-400 hover:text-gray-200 transition-all mb-1 text-sm"
                activeProps={{
                  className:
                    'flex items-center gap-3 p-2.5 rounded-lg bg-violet-500/10 text-violet-300 hover:text-violet-200 transition-all mb-1 text-sm',
                }}
              >
                <StickyNote size={16} />
                <span className="font-medium">SPA Mode</span>
              </Link>

              <Link
                to="/demo/start/ssr/full-ssr"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-white/[0.04] text-gray-400 hover:text-gray-200 transition-all mb-1 text-sm"
                activeProps={{
                  className:
                    'flex items-center gap-3 p-2.5 rounded-lg bg-violet-500/10 text-violet-300 hover:text-violet-200 transition-all mb-1 text-sm',
                }}
              >
                <StickyNote size={16} />
                <span className="font-medium">Full SSR</span>
              </Link>

              <Link
                to="/demo/start/ssr/data-only"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-3 p-2.5 rounded-lg hover:bg-white/[0.04] text-gray-400 hover:text-gray-200 transition-all mb-1 text-sm"
                activeProps={{
                  className:
                    'flex items-center gap-3 p-2.5 rounded-lg bg-violet-500/10 text-violet-300 hover:text-violet-200 transition-all mb-1 text-sm',
                }}
              >
                <StickyNote size={16} />
                <span className="font-medium">Data Only</span>
              </Link>
            </div>
          )}

          {/* Demo Links End */}
        </nav>
      </aside>

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  )
}
