import type { TimeLineItem } from "./types";

// 将小时:分钟格式的字符串转换为当天经过的分钟数
export function timeStrToMinutes(timeStr: string): number {
    const [hours, minutes] = timeStr.split(':').map(Number);
    return hours * 60 + minutes;
}

// 将当天经过的分钟数转换为小时:分钟格式的字符串
export function minutesToTimeStr(minutes: number): string {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return `${hours.toString().padStart(2, '0')}:${remainingMinutes.toString().padStart(2, '0')}`;
}


const title = "====空闲时间===="

export function fullTimeLine(items: TimeLineItem[]): TimeLineItem[] {
    if (items.length === 0) {
        return items
    }

    let ans: TimeLineItem[] = []
    
    // 判断并插入首节点
    const s0 = items[0]
    if (timeStrToMinutes(s0.start) > timeStrToMinutes("10:00")) {
        ans.push({ start: "10:00", finish: s0.start, title })
    }
    ans.push(s0)


    // 插入任务之间的间隙节点
    let last = s0
    for (let i = 1; i < items.length; i++) {
        const item = items[i]
        if(timeStrToMinutes(last.finish) + 5 < timeStrToMinutes(item.start)) {
            ans.push({start: last.finish, finish: item.start, title})
        }
        ans.push(item)
        last = item
    }

    // 判断并插入尾结点
    if(timeStrToMinutes(last.finish) < timeStrToMinutes("21:00")) {
        ans.push({start: last.finish, finish: "21:00", title})
    }

    return ans;
}