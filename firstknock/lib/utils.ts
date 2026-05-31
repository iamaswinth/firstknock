import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function initials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase()
}

export function formatMonths(months: number | null | undefined): string {
  if (!months) return ""
  const y = Math.floor(months / 12)
  const m = months % 12
  if (y === 0) return `${m}mo`
  if (m === 0) return `${y}yr`
  return `${y}yr ${m}mo`
}

export function formatDate(date: string | null | undefined): string {
  if (!date) return "Present"
  const [year, month] = date.split("-")
  if (!month) return year
  const d = new Date(parseInt(year), parseInt(month) - 1)
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric" })
}
