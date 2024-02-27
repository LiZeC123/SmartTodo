import type {Item} from "@/components/item/types"

export interface SmartAnalysisReport {
    count: number
    groups: ReportGroup[]
}

export interface ReportGroup {
    name: string
    items: Item[]
}