import type { Item } from './types'

// 按照指定的顺序添加标记
export function mapName(item: Item) {
  let remainHour = undefined
  if (item.deadline) {
    const dd = new Date(item.deadline).getTime() - new Date().getTime()
    remainHour = parseFloat((dd / (1000 * 60 * 60)).toFixed(1))
  }

  const tags = [
    getTomatoCountTag(item),
    getDLCounterDownTag(remainHour),
    getDeadlineTag(item, remainHour),
    getSpTag(item),
    getTypeTag(item)
  ]

  return renderTag(tags) + item.name
}

type Tag = string | undefined

function getTomatoCountTag(item: Item): Tag {
  if (item.expected_tomato && item.expected_tomato !== 1) {
    return item.used_tomato + '/' + item.expected_tomato
  }
}

function getDeadlineTag(item: Item, hour: number | undefined): Tag {
  if (item.deadline) {
    // 如果截止时间就是今天了, 那么不显示日期格式的截止时间
    // 仅展示倒计时小时格式的时间
    if (hour && hour > 0 && hour < 18) {
      return
    }

    // 先获取年月日部分
    const dateString = item.deadline.split(' ')[0]

    // 再截取月和日
    const [, month, day] = dateString.split('-')
    return `${month}-${day}`
  }
}

function getDLCounterDownTag(hour: number | undefined): Tag {
  if (hour) {
    // 非常接近的任务显示具体的剩余时间
    if (hour < 48 && hour > -48) {
      return '剩余' + hour + '小时'
    }

    // 已逾期较长时间的任务仅标记已逾期, 而不展示具体的时间
    if (hour <= -48) {
      return '已逾期'
    }
  }
}

function getSpTag(item: Item): Tag {
  if (item.specific > 0) {
    return '周期'
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
  let ans = ''
  for (const tag of tags) {
    if (tag) {
      ans += '【' + tag + '】'
    }
  }

  return ans
}
