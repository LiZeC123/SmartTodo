export interface ButtonConfig {
  name: string
  desc: string
  f: (idx: number, id: string) => void
}

export interface Item {
  id: string
  name: string
  item_type: string
  create_time: string
  update_time: string
  repeatable: boolean
  specific: number
  deadline?: string
  url?: string
  expected_tomato: number
  used_tomato: number
}

export interface GroupedItem {
  self: Item
  children: Item[]
}
