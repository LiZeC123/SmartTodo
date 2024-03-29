export interface FuncData {
    cmd: string
    data: string
    parent?: string
}

export type TodoType = "single" | "file" | "note"

export interface CreateItem {
    itemType: TodoType
    name: string
    repeatable?: boolean
    parent?: string
    deadline?: number
    specific?: string
}

export type CreateType = "func" | 'file' | 'create'