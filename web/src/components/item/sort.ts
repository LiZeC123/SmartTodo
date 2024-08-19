import type { Item } from "./types";

// 排序比较函数, 此函数期望在返回a<b, 并且按照升序排列数据
// Item需要按照从大到小的顺序排列, 因此这里对结果取反
export function compareItem(a: Item, b: Item): number {
    const va = calcValue(a)
    const vb = calcValue(b)

    return vb - va
}


const dayMs = 24 * 60 * 60 * 1000

function calcValue(item: Item): number {
    let base = new Date(item.create_time).getTime()

    if (item.deadline) {
        base = new Date().getTime()
        const dl = new Date(item.deadline).getTime()

        // 如果距离DL还有7天, 则不提升, 否则距离越近提升越多
        const plus = 7 * dayMs - (dl - base)

        // 加上一定的分数, 分数越大排序越靠前
        base += plus
    }

    if (item.expected_tomato === item.used_tomato) {
        base -= 100 * dayMs
    }

    return base
}
