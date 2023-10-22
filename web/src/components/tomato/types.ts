export const OneMinuteMS = 60 * 1000

export type TomatoEventType = 'done' | 'undo'

export interface TomatoItem {
  taskId: number // 番茄钟任务的ID, 用于防止多页面情况下启用多个番茄钟导致的并发提交问题
  itemId: number // 番茄钟对应的Item的ID
  taskName: string // 此番茄钟的名称
  startTime: number // 番茄钟开始时间的毫秒时间戳
  finished: boolean // 此番茄钟是否已经完成
}

export interface TomatoParam {
  taskId: number // 番茄钟任务的ID
  id: number //  番茄钟对应的Item的ID
}
