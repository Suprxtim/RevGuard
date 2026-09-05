"use client"

import { useEffect, useState, useRef } from "react"
import { Card } from "@/components/Card"
import { Button } from "@/components/Button"
import { Badge } from "@/components/Badge"
import { Divider } from "@/components/Divider"
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from "@/components/Table"
import {
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
} from "@/components/Drawer"
import { Switch } from "@/components/Switch"
import { toast } from "sonner"

interface DashboardData {
  metrics: {
    total_at_risk: number
    total_recovered: number
    recovery_rate: number
  }
  events: any[]
}

interface AgentLogEntry {
  step: string
  message: string
  icon: string
  event_id?: number
  timestamp: Date
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  const [selectedEvent, setSelectedEvent] = useState<any | null>(null)
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [agentActive, setAgentActive] = useState(false)
  const [agentLogs, setAgentLogs] = useState<AgentLogEntry[]>([])
  const [agentToggling, setAgentToggling] = useState(false)
  const logContainerRef = useRef<HTMLDivElement>(null)
  
  const fetchDashboardData = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/admin/dashboard-data`)
      if (res.ok) {
        setData(await res.json())
      }
    } catch (e) {
      console.error(e)
    }
  }

  // Check initial agent status
  useEffect(() => {
    fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/admin/agent/status`)
      .then(r => r.json())
      .then(d => setAgentActive(d.active))
      .catch(() => {})
  }, [])

  useEffect(() => {
    fetchDashboardData()

    // Listen to SSE
    const eventSource = new EventSource(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/admin/stream`)
    eventSource.onmessage = (e) => {
      if (e.data.startsWith("agent:log:")) {
        try {
          const logData = JSON.parse(e.data.substring("agent:log:".length))
          setAgentLogs(prev => [...prev.slice(-100), { ...logData, timestamp: new Date() }])
        } catch {}
      }
      if (e.data === "reload" || e.data.startsWith("processed:")) {
        fetchDashboardData()
      }
    }
    return () => eventSource.close()
  }, [])

  // Auto-scroll agent log
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTo({
        top: logContainerRef.current.scrollHeight,
        behavior: "smooth"
      })
    }
  }, [agentLogs])

  const handleAgentToggle = async (checked: boolean) => {
    setAgentToggling(true)
    try {
      const endpoint = checked ? "/admin/agent/start" : "/admin/agent/stop"
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}${endpoint}`, { method: "POST" })
      if (res.ok) {
        setAgentActive(checked)
        if (checked) {
          toast.success("🤖 Agent Activated — autonomous recovery started")
          setAgentLogs([])
        } else {
          toast.info("⏹️ Agent Deactivated")
        }
      }
    } catch (e) {
      toast.error("Failed to toggle agent")
    } finally {
      setAgentToggling(false)
    }
  }

  const handleAction = async (endpoint: string) => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}${endpoint}`, { method: "POST" })
      if (res.ok) {
        if (endpoint.includes("simulate")) {
          toast.success("Batch simulation started")
        } else if (endpoint.includes("retry-storm")) {
          toast.success("Retry storm triggered")
        } else if (endpoint.includes("process")) {
          toast.success("Processing pending events")
        } else if (endpoint.includes("reset")) {
          toast.success("Demo reset successfully")
          setAgentLogs([])
        } else {
          toast.success("Action completed")
        }
        fetchDashboardData()
      } else {
        toast.error("Action failed")
      }
    } catch (e) {
      console.error(e)
      toast.error("Error connecting to server")
    }
  }

  const getStepColor = (step: string) => {
    switch (step) {
      case "activated": return "text-blue-500"
      case "sweep": return "text-gray-500"
      case "detect": return "text-indigo-500"
      case "diagnose": case "diagnose_done": return "text-purple-500"
      case "policy": return "text-amber-500"
      case "policy_pass": return "text-emerald-500"
      case "policy_block": return "text-red-500"
      case "recovered": return "text-emerald-600 font-semibold"
      case "failed": return "text-red-600"
      case "escalated": return "text-amber-600"
      case "deactivated": return "text-gray-400"
      case "cycle_done": return "text-gray-400"
      case "skip": return "text-gray-400"
      default: return "text-gray-500"
    }
  }

  const getStepBg = (step: string) => {
    switch (step) {
      case "recovered": return "bg-emerald-50 dark:bg-emerald-950/30"
      case "policy_block": case "failed": return "bg-red-50 dark:bg-red-950/20"
      case "escalated": return "bg-amber-50 dark:bg-amber-950/20"
      default: return ""
    }
  }

  return (
    <main>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">
            Revenue Recovery Audit
          </h1>
          <p className="text-gray-500 sm:text-sm/6 dark:text-gray-500">
            Monitor and process failed payments in real-time
          </p>
        </div>
        <div className="flex gap-2 flex-wrap items-center">
          {/* Agent Toggle */}
          <div className="flex items-center gap-2.5 rounded-lg border border-gray-200 dark:border-gray-800 px-3 py-1.5 mr-2">
            <div className="flex items-center gap-2">
              {agentActive && (
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                </span>
              )}
              <span className={`text-sm font-medium ${agentActive ? "text-emerald-600 dark:text-emerald-400" : "text-gray-500"}`}>
                Agent {agentActive ? "ACTIVE" : "OFF"}
              </span>
            </div>
            <Switch 
              checked={agentActive} 
              onCheckedChange={handleAgentToggle}
              disabled={agentToggling}
            />
          </div>
          <Button variant="secondary" onClick={() => handleAction("/admin/simulate/batch")}>
            Simulate Batch
          </Button>
          <Button variant="secondary" onClick={() => handleAction("/admin/trigger-retry-storm")}>
            Retry Storm
          </Button>
          <Button variant="primary" onClick={() => handleAction("/admin/process")} disabled={agentActive}>
            Process Pending
          </Button>
          <Button variant="destructive" onClick={() => handleAction("/admin/reset-demo")}>
            Reset
          </Button>
        </div>
      </div>
      
      <Divider className="my-6" />
      
      {data ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 mt-6">
            <Card>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total At Risk</p>
              <p className="text-3xl font-semibold text-gray-900 dark:text-gray-50">
                ₹{data.metrics.total_at_risk.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </Card>
            <Card>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Recovered</p>
              <p className="text-3xl font-semibold text-emerald-600 dark:text-emerald-400">
                ₹{data.metrics.total_recovered.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </Card>
            <Card>
              <p className="text-sm text-gray-500 dark:text-gray-400">Recovery Rate</p>
              <p className="text-3xl font-semibold text-gray-900 dark:text-gray-50">
                {data.metrics.recovery_rate.toFixed(1)}%
              </p>
            </Card>
          </div>

          {/* Agent Activity Feed */}
          {agentLogs.length > 0 && (
            <div className="mb-8">
              <div className="flex items-center gap-2 mb-3">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-50">Agent Activity</h2>
                {agentActive && <Badge variant="success">Live</Badge>}
                <button 
                  onClick={() => setAgentLogs([])}
                  className="ml-auto text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                >
                  Clear Log
                </button>
              </div>
              <Card className="p-0 overflow-hidden">
                <div ref={logContainerRef} className="max-h-64 overflow-y-auto bg-gray-950 dark:bg-black font-mono text-xs">
                  <div className="p-3 space-y-0.5">
                    {agentLogs.map((log, idx) => (
                      <div key={idx} className={`flex items-start gap-2 py-0.5 px-1 rounded ${getStepBg(log.step)}`}>
                        <span className="text-gray-600 dark:text-gray-500 shrink-0 tabular-nums">
                          {log.timestamp.toLocaleTimeString('en-US', { hour12: false })}
                        </span>
                        <span className="shrink-0">{log.icon}</span>
                        <span className={getStepColor(log.step)}>{log.message}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            </div>
          )}
          
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-50 mb-4">Recent Events</h2>
          <Card className="p-0 overflow-hidden">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>ID</TableHeaderCell>
                  <TableHeaderCell>Type</TableHeaderCell>
                  <TableHeaderCell>User ID</TableHeaderCell>
                  <TableHeaderCell>Amount</TableHeaderCell>
                  <TableHeaderCell>Status</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.events.map((event) => (
                  <TableRow 
                    key={event.id}
                    onClick={() => { setSelectedEvent(event); setIsDrawerOpen(true); }}
                    className="cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-900/50"
                  >
                    <TableCell className="font-mono text-xs">{event.id}</TableCell>
                    <TableCell>{event.type}</TableCell>
                    <TableCell className="font-medium text-gray-900 dark:text-gray-100">{event.user_id}</TableCell>
                    <TableCell>₹{event.amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                    <TableCell>
                      <Badge variant={
                        event.status === "recovered" ? "success" : 
                        event.status === "unrecovered" ? "error" : 
                        event.status === "escalated" ? "warning" : "default"
                      }>
                        {event.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
                {data.events.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-gray-500 py-8">
                      No events found. Click &quot;Simulate Batch&quot; to generate data.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </>
      ) : (
        <div className="flex justify-center items-center py-20 text-gray-500">
          Loading dashboard data... (Make sure backend is running on port 8000)
        </div>
      )}

      {/* Event Details Drawer with Agent Chain-of-Thought Timeline */}
      <Drawer open={isDrawerOpen} onOpenChange={setIsDrawerOpen}>
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>Event #{selectedEvent?.id} — Agent Audit Trail</DrawerTitle>
            <DrawerDescription>Full chain-of-thought for this event</DrawerDescription>
          </DrawerHeader>
          <DrawerBody>
            {selectedEvent && (
              <div className="space-y-6">
                {/* Event Summary Card */}
                <div className="bg-gray-50 dark:bg-gray-900/50 p-4 rounded-lg border border-gray-200 dark:border-gray-800">
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <span className="text-gray-500 dark:text-gray-400 text-xs uppercase tracking-wider">Type</span>
                      <p className="font-medium text-gray-900 dark:text-gray-100 mt-0.5">{selectedEvent.type}</p>
                    </div>
                    <div>
                      <span className="text-gray-500 dark:text-gray-400 text-xs uppercase tracking-wider">Amount</span>
                      <p className="font-medium text-gray-900 dark:text-gray-100 mt-0.5">₹{selectedEvent.amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
                    </div>
                    <div>
                      <span className="text-gray-500 dark:text-gray-400 text-xs uppercase tracking-wider">User</span>
                      <p className="font-medium text-gray-900 dark:text-gray-100 mt-0.5">{selectedEvent.user_id}</p>
                    </div>
                    <div>
                      <span className="text-gray-500 dark:text-gray-400 text-xs uppercase tracking-wider">Status</span>
                      <div className="mt-0.5">
                        <Badge variant={
                          selectedEvent.status === "recovered" ? "success" : 
                          selectedEvent.status === "unrecovered" ? "error" : 
                          selectedEvent.status === "escalated" ? "warning" : "default"
                        }>{selectedEvent.status}</Badge>
                      </div>
                    </div>
                    {selectedEvent.decline_code && selectedEvent.decline_code !== "N/A" && (
                      <div>
                        <span className="text-gray-500 dark:text-gray-400 text-xs uppercase tracking-wider">Decline Code</span>
                        <p className="font-mono font-medium text-gray-900 dark:text-gray-100 mt-0.5">{selectedEvent.decline_code}</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Agent Chain-of-Thought Timeline */}
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-4 uppercase tracking-wider">Agent Chain of Thought</h3>
                  <div className="relative">
                    {/* Timeline line */}
                    <div className="absolute left-4 top-0 bottom-0 w-px bg-gray-200 dark:bg-gray-700" />
                    
                    <div className="space-y-0">
                      {/* Step 1: Detection */}
                      <TimelineStep
                        icon="🎯"
                        title="Detection"
                        active={true}
                        color="indigo"
                      >
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          Detected <span className="font-medium text-gray-900 dark:text-gray-200">{selectedEvent.type}</span> event
                          for ₹{selectedEvent.amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </p>
                      </TimelineStep>

                      {/* Step 2: Diagnosis */}
                      {selectedEvent.diagnosis ? (
                        <TimelineStep
                          icon="🧠"
                          title="AI Diagnosis"
                          subtitle={`Model: llama-3.1-8b-instant`}
                          active={true}
                          color="purple"
                        >
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-gray-500 dark:text-gray-400">Root Cause:</span>
                              <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{selectedEvent.diagnosis.root_cause}</span>
                            </div>
                            <div className="bg-purple-50 dark:bg-purple-950/30 border border-purple-100 dark:border-purple-900/50 rounded-md p-3">
                              <p className="text-xs text-purple-800 dark:text-purple-300 italic">&quot;{selectedEvent.diagnosis.rationale}&quot;</p>
                            </div>
                          </div>
                        </TimelineStep>
                      ) : (
                        <TimelineStep icon="🧠" title="AI Diagnosis" active={false} color="gray">
                          <p className="text-sm text-gray-400 italic">Not yet diagnosed</p>
                        </TimelineStep>
                      )}

                      {/* Step 3: Policy Gate */}
                      {selectedEvent.policy ? (
                        <TimelineStep
                          icon={selectedEvent.policy.action_approved ? "✅" : "🚫"}
                          title="Policy Gate"
                          subtitle={`Rule: ${selectedEvent.policy.rule_triggered}`}
                          active={true}
                          color={selectedEvent.policy.action_approved ? "emerald" : "red"}
                        >
                          <div className="space-y-2">
                            <Badge variant={selectedEvent.policy.action_approved ? "success" : "error"}>
                              {selectedEvent.policy.action_approved ? "APPROVED" : "BLOCKED"}
                            </Badge>
                            <p className="text-xs text-gray-600 dark:text-gray-400">{selectedEvent.policy.rationale}</p>
                          </div>
                        </TimelineStep>
                      ) : (
                        <TimelineStep icon="🛡️" title="Policy Gate" active={false} color="gray">
                          <p className="text-sm text-gray-400 italic">Awaiting policy evaluation</p>
                        </TimelineStep>
                      )}

                      {/* Step 4: Execution */}
                      {selectedEvent.actions && selectedEvent.actions.length > 0 ? (
                        selectedEvent.actions.map((action: any, idx: number) => (
                          <TimelineStep
                            key={idx}
                            icon={action.outcome === "success" ? "💰" : action.outcome === "failure" ? "❌" : "⏳"}
                            title={`Execution: ${action.type}`}
                            subtitle={`Outcome: ${action.outcome}`}
                            active={true}
                            color={action.outcome === "success" ? "emerald" : action.outcome === "failure" ? "red" : "amber"}
                            isLast={idx === selectedEvent.actions.length - 1}
                          >
                            <div className="space-y-2">
                              {action.generated_message && (
                                <div className="bg-blue-50 dark:bg-blue-950/30 border border-blue-100 dark:border-blue-900/50 rounded-md p-3">
                                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                                    Generated {action.channel || "Message"}:
                                  </p>
                                  <p className="text-sm text-blue-800 dark:text-blue-300">&quot;{action.generated_message}&quot;</p>
                                </div>
                              )}
                              {action.outcome === "success" && action.type === "retry" && (
                                <p className="text-sm text-emerald-600 dark:text-emerald-400 font-medium">
                                  ₹{selectedEvent.amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} recovered successfully!
                                </p>
                              )}
                            </div>
                          </TimelineStep>
                        ))
                      ) : (
                        <TimelineStep icon="⚡" title="Execution" active={false} color="gray" isLast={true}>
                          <p className="text-sm text-gray-400 italic">No actions executed yet</p>
                        </TimelineStep>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </DrawerBody>
          <DrawerFooter>
            <Button variant="secondary" onClick={() => setIsDrawerOpen(false)}>Close</Button>
          </DrawerFooter>
        </DrawerContent>
      </Drawer>
    </main>
  )
}

/* Timeline Step Component */
function TimelineStep({ 
  icon, title, subtitle, children, active, color, isLast 
}: { 
  icon: string
  title: string
  subtitle?: string
  children: React.ReactNode
  active: boolean
  color: string
  isLast?: boolean
}) {
  const dotColors: Record<string, string> = {
    indigo: "bg-indigo-500 ring-indigo-100 dark:ring-indigo-900",
    purple: "bg-purple-500 ring-purple-100 dark:ring-purple-900",
    emerald: "bg-emerald-500 ring-emerald-100 dark:ring-emerald-900",
    red: "bg-red-500 ring-red-100 dark:ring-red-900",
    amber: "bg-amber-500 ring-amber-100 dark:ring-amber-900",
    gray: "bg-gray-300 ring-gray-100 dark:bg-gray-600 dark:ring-gray-800",
  }

  return (
    <div className={`relative flex gap-4 ${isLast ? "" : "pb-6"}`}>
      {/* Timeline dot */}
      <div className="relative z-10 flex items-center justify-center">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center ring-4 ${active ? dotColors[color] || dotColors.gray : dotColors.gray}`}>
          <span className="text-sm">{icon}</span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0 pt-0.5">
        <div className="flex items-center gap-2">
          <h4 className={`text-sm font-semibold ${active ? "text-gray-900 dark:text-gray-100" : "text-gray-400 dark:text-gray-500"}`}>
            {title}
          </h4>
          {subtitle && (
            <span className="text-xs text-gray-400 dark:text-gray-500">{subtitle}</span>
          )}
        </div>
        <div className="mt-1">
          {children}
        </div>
      </div>
    </div>
  )
}
