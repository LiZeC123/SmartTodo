import type { Item } from "./types";

// 按照指定的顺序添加标记
export function mapName(item: Item) {
    const tags = [
        getTomatoCountTag(item),
        getDLCounterDownTag(item),
        getDeadlineTag(item),
        getSpTag(item),
        getTypeTag(item),
    ]

    return renderTag(tags) + item.name
}


type Tag = string | undefined

function getTomatoCountTag(item: Item): Tag {
    if (item.expected_tomato && item.expected_tomato !== 1) {
        return item.used_tomato + '/' + item.expected_tomato
    }
}

function getDeadlineTag(item: Item): Tag {
    if (item.deadline) {
        // 先获取年月日部分
        const dateString = item.deadline.split(' ')[0]

        // 再截取月和日
        const [year, month, day] = dateString.split('-');        
        return `${month}-${day}`
    }
}

function getDLCounterDownTag(item: Item): Tag {
    if (item.deadline) {
        const dd = new Date(item.deadline).getTime() - new Date().getTime()
        const hour = parseFloat((dd / (1000 * 60 * 60)).toFixed(1))

        // 非常接近的任务则显示具体的剩余时间
        if (hour < 50) {
            return '剩余' + hour + '小时'
        }
    }
}

function getSpTag(item:Item): Tag {
    if (item.specific > 0) {
        return "周期"
    }
}

function getTypeTag(item: Item): Tag {
    if (item.item_type === 'note') {
        return '便签'
    } else if (item.item_type === 'file') {
        return '文件'
    } else if (item.url) {
        return '链接'
    }
}

function renderTag(tags: Tag[]): string {
    let ans = ""
    for (let tag of tags) {
        if (tag) {
            ans += '【' + tag + '】'
        }
    }

    return ans
}