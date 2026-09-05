"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/Card"
import { Badge } from "@/components/Badge"
import { Divider } from "@/components/Divider"
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from "@/components/Table"

interface DashboardData {
  metrics: {
    total_at_risk: number
    total_recovered: number
    recovery_rate: number
  }
  events: any[]
}

export default function WorkflowPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  
  const fetchDashboardData = async () => {
    try {
      const res = await fetch("http://127.0.0.1:8000/admin/dashboard-data")
      if (res.ok) {
        setData(await res.json())
      }
    } catch (e) {
      console.error(e)
    }
  }

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const evaluatedEvents = data?.events.filter(e => e.policy) || []
  const totalEvaluated = evaluatedEvents.length
  const totalApproved = evaluatedEvents.filter(e => e.policy.action_approved).length
  const totalRejected = totalEvaluated - totalApproved

  const ruleCounts = evaluatedEvents.reduce((acc, curr) => {
    const rule = curr.policy.rule_triggered
    acc[rule] = (acc[rule] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  return (
    <main>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">
            Workflow: Policy Gate Analytics
          </h1>
          <p className="text-gray-500 sm:text-sm/6 dark:text-gray-500">
            Insights into how the deterministic rules engine is filtering AI actions
          </p>
        </div>
      </div>
      
      <Divider className="my-6" />
      
      {data ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 mt-6">
            <Card>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Actions Evaluated</p>
              <p className="text-3xl font-semibold text-gray-900 dark:text-gray-50">
                {totalEvaluated}
              </p>
            </Card>
            <Card>
              <p className="text-sm text-gray-500 dark:text-gray-400">Actions Approved</p>
              <p className="text-3xl font-semibold text-emerald-600 dark:text-emerald-500">
                {totalApproved}
              </p>
            </Card>
            <Card>
              <p className="text-sm text-gray-500 dark:text-gray-400">Actions Blocked (Escalated)</p>
              <p className="text-3xl font-semibold text-red-600 dark:text-red-500">
                {totalRejected}
              </p>
            </Card>
          </div>

          <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-50">Rules Triggered Breakdown</h2>
          <Card className="p-0 overflow-hidden mb-8">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Rule Name</TableHeaderCell>
                  <TableHeaderCell>Hit Count</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {Object.entries(ruleCounts).map(([rule, count]) => (
                  <TableRow key={rule}>
                    <TableCell className="font-medium text-gray-900 dark:text-gray-100">{rule}</TableCell>
                    <TableCell>{count}</TableCell>
                  </TableRow>
                ))}
                {Object.keys(ruleCounts).length === 0 && (
                  <TableRow>
                    <TableCell colSpan={2} className="text-center text-gray-500 py-8">
                      No policy evaluations yet.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>

          <h2 className="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-50">Recent Policy Decisions</h2>
          <Card className="p-0 overflow-hidden">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>Event ID</TableHeaderCell>
                  <TableHeaderCell>Action Proposed</TableHeaderCell>
                  <TableHeaderCell>Decision</TableHeaderCell>
                  <TableHeaderCell>Rule Triggered</TableHeaderCell>
                  <TableHeaderCell>Rationale</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {evaluatedEvents.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell className="font-mono text-xs">{event.id}</TableCell>
                    <TableCell>{event.diagnosis?.recommended_action || "Unknown"}</TableCell>
                    <TableCell>
                      <Badge variant={event.policy.action_approved ? "success" : "error"}>
                        {event.policy.action_approved ? "Approved" : "Rejected"}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-medium">{event.policy.rule_triggered}</TableCell>
                    <TableCell className="max-w-xs truncate text-xs" title={event.policy.rationale}>{event.policy.rationale}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Card>
        </>
      ) : (
        <div className="flex justify-center items-center py-20 text-gray-500">
          Loading workflow data...
        </div>
      )}
    </main>
  )
}
