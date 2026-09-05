"use client"

import { useEffect, useState } from "react"
import { Card } from "@/components/Card"
import { Badge } from "@/components/Badge"
import { Divider } from "@/components/Divider"
import { Table, TableBody, TableCell, TableHead, TableHeaderCell, TableRow } from "@/components/Table"
import { toast } from "sonner"

interface DashboardData {
  metrics: {
    total_at_risk: number
    total_recovered: number
    recovery_rate: number
  }
  events: any[]
}

export default function RetentionPage() {
  const [data, setData] = useState<DashboardData | null>(null)
  
  const fetchDashboardData = async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000'}/admin/dashboard-data`)
      if (res.ok) {
        setData(await res.json())
      }
    } catch (e) {
      console.error(e)
      toast.error("Failed to fetch retention data")
    }
  }

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const abandonmentEvents = data?.events.filter(e => e.type === "checkout_abandonment") || []
  
  const totalAbandonedAmount = abandonmentEvents.reduce((acc, curr) => acc + curr.amount, 0)
  const totalRecoveredAmount = abandonmentEvents.filter(e => e.status === "recovered").reduce((acc, curr) => acc + curr.amount, 0)
  const retentionRate = totalAbandonedAmount > 0 ? (totalRecoveredAmount / totalAbandonedAmount) * 100 : 0

  return (
    <main>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 dark:text-gray-50">
            Retention: Checkout Abandonment
          </h1>
          <p className="text-gray-500 sm:text-sm/6 dark:text-gray-500">
            Focus specifically on recovering lost carts before they expire
          </p>
        </div>
      </div>
      
      <Divider className="my-6" />
      
      {data ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 mt-6">
            <Card>
              <p className="text-sm text-gray-500 dark:text-gray-400">Total Cart Value Lost</p>
              <p className="text-3xl font-semibold text-gray-900 dark:text-gray-50">
                ₹{totalAbandonedAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </Card>
            <Card>
              <p className="text-sm text-gray-500 dark:text-gray-400">Cart Value Recovered</p>
              <p className="text-3xl font-semibold text-gray-900 dark:text-gray-50">
                ₹{totalRecoveredAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </p>
            </Card>
            <Card>
              <p className="text-sm text-gray-500 dark:text-gray-400">Cart Recovery Rate</p>
              <p className="text-3xl font-semibold text-gray-900 dark:text-gray-50">
                {retentionRate.toFixed(1)}%
              </p>
            </Card>
          </div>

          <Card className="p-0 overflow-hidden">
            <Table>
              <TableHead>
                <TableRow>
                  <TableHeaderCell>ID</TableHeaderCell>
                  <TableHeaderCell>User ID</TableHeaderCell>
                  <TableHeaderCell>Cart Amount</TableHeaderCell>
                  <TableHeaderCell>Time Since Abandonment</TableHeaderCell>
                  <TableHeaderCell>Status</TableHeaderCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {abandonmentEvents.map((event) => {
                  const hours = event.context?.hours_since_abandonment || 0
                  return (
                    <TableRow key={event.id}>
                      <TableCell className="font-mono text-xs">{event.id}</TableCell>
                      <TableCell className="font-medium text-gray-900 dark:text-gray-100">{event.user_id}</TableCell>
                      <TableCell>₹{event.amount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</TableCell>
                      <TableCell>{hours} hours ago</TableCell>
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
                  )
                })}
                {abandonmentEvents.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center text-gray-500 py-8">
                      No checkout abandonment events detected.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </>
      ) : (
        <div className="flex justify-center items-center py-20 text-gray-500">
          Loading retention data...
        </div>
      )}
    </main>
  )
}
