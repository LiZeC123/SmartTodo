export interface TimeLineItem {
    start: string
    finish: string
    title: string
}

export interface CountInfo {
    tomatoCounts: number
    totalMinutes: number
}

export interface Report {
    counter: CountInfo
    items: TimeLineItem[]
}