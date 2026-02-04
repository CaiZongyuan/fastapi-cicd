import { createFileRoute } from '@tanstack/react-router'
import { useChat } from '@ai-sdk/react'
import { useEffect, useRef, useState } from 'react'
import { ArrowUp, Sparkles } from 'lucide-react'

export const Route = createFileRoute('/chat/chatbot')({
  component: RouteComponent,
})

function RouteComponent() {
  const [input, setInput] = useState('')
  const { messages, sendMessage, status } = useChat()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const isLoading = status === 'submitted' || status === 'streaming'

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      sendMessage({ text: input })
      setInput('')
    }
  }

  return (
    <div className="flex flex-col h-screen bg-[#08090A]">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-white/[0.08]">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-white">AI Assistant</h1>
            <p className="text-xs text-gray-500">Always here to help</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs text-gray-500">Online</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center py-20">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-violet-500/20 to-purple-600/20 flex items-center justify-center mb-6 border border-white/[0.08]">
                <Sparkles className="w-8 h-8 text-violet-400" />
              </div>
              <h2 className="text-xl font-semibold text-white mb-2">
                How can I help you today?
              </h2>
              <p className="text-sm text-gray-500 max-w-sm">
                Start a conversation with the AI assistant. Ask anything you'd like.
              </p>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-4 ${
                message.role === 'user' ? 'justify-end' : 'justify-start'
              }`}
            >
              {message.role === 'assistant' && (
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
              )}

              <div
                className={`max-w-[80%] rounded-2xl ${
                  message.role === 'user'
                    ? 'bg-gradient-to-br from-violet-600 to-purple-700 text-white px-5 py-3'
                    : 'bg-white/[0.04] border border-white/[0.08] px-5 py-4'
                }`}
              >
                {message.parts.map((part, i) => {
                  switch (part.type) {
                    case 'text':
                      return (
                        <p
                          key={`${message.id}-${i}`}
                          className={`text-sm leading-relaxed ${
                            message.role === 'user'
                              ? 'text-white'
                              : 'text-gray-200'
                          }`}
                        >
                          {part.text}
                        </p>
                      )
                    case 'reasoning':
                      return (
                        <div
                          key={`${message.id}-${i}`}
                          className="mt-3 rounded-xl bg-white/[0.04] border border-white/[0.06] p-4"
                        >
                          <div className="flex items-center gap-2 mb-2">
                            <div className="w-5 h-5 rounded bg-amber-500/20 flex items-center justify-center">
                              <span className="text-xs">💭</span>
                            </div>
                            <span className="text-xs font-medium text-amber-300/80 uppercase tracking-wide">
                              Reasoning
                            </span>
                          </div>
                          <p className="text-sm text-gray-400 leading-relaxed whitespace-pre-wrap">
                            {part.text}
                          </p>
                        </div>
                      )
                  }
                })}
              </div>

              {message.role === 'user' && (
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-gray-600 to-gray-700 flex items-center justify-center flex-shrink-0">
                  <svg
                    className="w-4 h-4 text-white"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
                    />
                  </svg>
                </div>
              )}
            </div>
          ))}

          {isLoading && (
            <div className="flex gap-4 justify-start">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div className="bg-white/[0.04] border border-white/[0.08] px-5 py-4 rounded-2xl">
                <div className="flex gap-1">
                  <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce [animation-delay:-0.3s]" />
                  <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce [animation-delay:-0.15s]" />
                  <div className="w-2 h-2 rounded-full bg-gray-500 animate-bounce" />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="border-t border-white/[0.08] bg-[#08090A]/80 backdrop-blur-xl px-4 py-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto">
          <div className="relative">
            <input
              className="w-full bg-white/[0.04] border border-white/[0.08] rounded-2xl pl-5 pr-14 py-4 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-violet-500/50 focus:ring-2 focus:ring-violet-500/20 transition-all duration-200"
              value={input}
              placeholder="Message AI assistant..."
              onChange={(e) => setInput(e.currentTarget.value)}
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className={`absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-200 ${
                input.trim() && !isLoading
                  ? 'bg-gradient-to-br from-violet-600 to-purple-700 text-white shadow-lg shadow-violet-500/20'
                  : 'bg-white/[0.04] text-gray-600 cursor-not-allowed'
              }`}
            >
              <ArrowUp className="w-5 h-5" />
            </button>
          </div>
          <p className="text-xs text-gray-600 text-center mt-3">
            AI can make mistakes. Please verify important information.
          </p>
        </form>
      </div>
    </div>
  )
}
