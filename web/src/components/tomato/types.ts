export const OneMinuteMS = 60 * 1000

export type TomatoEventType = 'done' | 'undo'

export interface TomatoItem {
  itemId: number // 番茄钟对应的Item的ID
  taskName: string // 此番茄钟的名称
  startTime: string // 番茄钟开始时间的毫秒时间戳
  finished: boolean // 此番茄钟是否已经完成
}

export interface TomatoParam {
  id: number //  番茄钟对应的Item的ID
  reason?: string // 番茄钟取消原因
}
