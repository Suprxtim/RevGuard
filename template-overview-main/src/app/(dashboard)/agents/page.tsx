"use client"

import { useState } from "react"
import { Card } from "@/components/Card"
import { Button } from "@/components/Button"
import { Input } from "@/components/Input"
import { Divider } from "@/components/Divider"
import { Badge } from "@/components/Badge"
import { toast } from "sonner"

interface Message {
  role: "user" | "copilot"
  content: string
}

export default function AgentsPage() {
  const [query, setQuery] = useState("")
  const [messages, setMessages] = useState<Message[]>([
    { role: "copilot", content: "Hello! I am your RevGuard LLM Copilot. You can ask me questions about your revenue recovery metrics, such as 'How much money is at risk?' or 'What is our current recovery rate?'." }
  ])
  const [isLoading, setIsLoading] = useState(false)

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || isLoading) return

    const userMessage: Message = { role: "user", content: query }
    setMessages(prev => [...prev, userMessage])
    setQuery("")
    setIsLoading(true)

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/admin/copilot`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMessage.content })
      })
      
      if (res.ok) {
        const data = await res.json()
        setMessages(prev => [...prev, { role: "copilot", content: data.answer }])
      } else {
        setMessages(prev => [...prev, { role: "copilot", content: "Sorry, I encountered an error while processing your request." }])
        toast.error("Failed to get response from copilot")
      }
    } catch (e) {
      console.error(e)
      setMessages(prev => [...prev, { role: "copilot", content: "Sorry, I couldn't reach the backend server." }])
      toast.error("Network error: Could not reach backend")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="max-w-4xl mx-auto">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50 flex items-center gap-2">
            AI Copilot <Badge variant="success">Online</Badge>
          </h1>
          <p className="text-gray-500 sm:text-sm/6 dark:text-gray-500">
            Query your recovery metrics using natural language
          </p>
        </div>
      </div>
      
      <Divider className="my-6" />
      
      <Card className="flex flex-col h-[600px] p-0 overflow-hidden bg-gray-50 dark:bg-gray-900/50">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-lg px-4 py-3 ${
                msg.role === 'user' 
                  ? 'bg-blue-600 text-white rounded-br-none' 
                  : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100 rounded-bl-none shadow-sm'
              }`}>
                {msg.content}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-500 rounded-lg px-4 py-3 rounded-bl-none shadow-sm">
                Thinking...
              </div>
            </div>
          )}
        </div>
        
        <div className="p-4 bg-white dark:bg-gray-950 border-t border-gray-200 dark:border-gray-800">
          <form onSubmit={handleSend} className="flex gap-2">
            <Input 
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask about your metrics..." 
              className="flex-1"
              disabled={isLoading}
            />
            <Button type="submit" disabled={isLoading || !query.trim()}>
              Send
            </Button>
          </form>
        </div>
      </Card>
    </main>
  )
}
