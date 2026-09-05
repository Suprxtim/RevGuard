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

export default function SupportPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  
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

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const escalatedEvents = data?.events.filter(e => e.status === "escalated") || []

  return (
    <main>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">
            Support Escalations
          </h1>
          <p className="text-gray-500 sm:text-sm/6 dark:text-gray-500">
            Cases flagged by the Policy Gate that require human review
          </p>
        </div>
      </div>
      
      <Divider className="my-6" />
      
      {data ? (
        <>
          <Card className="p-0 overflow-hidden">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>ID</TableHeaderCell>
                  <TableHeaderCell>Type</TableHeaderCell>
                  <TableHeaderCell>User ID</TableHeaderCell>
                  <TableHeaderCell>Amount</TableHeaderCell>
                  <TableHeaderCell>Policy Triggered</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {escalatedEvents.map((event) => (
                  <TableRow key={event.id}>
                    <TableCell className="font-mono text-xs">{event.id}</TableCell>
                    <TableCell>{event.type}</TableCell>
                    <TableCell className="font-medium text-gray-900 dark:text-gray-100">{event.user_id}</TableCell>
                    <TableCell>₹{event.amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                    <TableCell>
                      <Badge variant="warning">
                        {event.policy?.rule_triggered || "Unknown Rule"}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))}
                {escalatedEvents.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-gray-500 py-8">
                      No escalated cases. You're all caught up!
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </>
      ) : (
        <div className="flex justify-center items-center py-20 text-gray-500">
          Loading support queue...
        </div>
      )}
    </main>
  )
}
