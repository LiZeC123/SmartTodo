import type { Item } from "./types";

// 按照指定的顺序添加标记
// 【番茄量计数】【特定任务提示】【截止时间倒计时】【截止时间】【类型标记】
export function mapName(item: Item) {
    const tags = [
        getTomatoCountTag(item),
        getDLCounterDownTag(item),
        getDeadlineTag(item),
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
        // 截止日期只展示日期部分
        return item.deadline.split(' ')[0]
    }
}

function getDLCounterDownTag(item: Item): Tag {
    if (item.deadline) {
        const dd = new Date(item.deadline).getTime() - new Date().getTime()
        const hour = parseFloat((dd / (1000 * 60 * 60)).toFixed(1))

        // 非常接近的任务则显示具体的剩余时间
        if (hour < 100) {
            return '剩余' + hour + '小时'
        }
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