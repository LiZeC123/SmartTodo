import type { TodoType, CreateItem, TodoPriority } from './types'

// 解析输入的代办事项文本, 根据文本内容附带必要的属性
export function parseTitleToData(todoContent: string, priority: TodoPriority) {
  const values = todoContent.split(' ')

  // 分析任务名称
  let name = todoContent
  if (values.length > 1) {
    name = values[0]
  }

  // 分析类型
  let data: CreateItem = {
    name: name,
    itemType: inferType(name),
    priority: priority,
    repeatable: inferRepeatable(name),
    deadline: parsePriority(priority),
    tags: [],
  }

  // 解决一些冲突情况
  // 每日任务没有截止日期
  if (data.repeatable) {
    data.deadline = undefined
  }


  // 分析参数
  for (let i = 1; i < values.length; i++) {
    if (values[i].charAt(0) !== '-') {
      data.name += ' ' + values[i]
    } else if (values[i] === '-dl' && i + 1 < values.length) {
      data.deadline = parseDeadline(values[i + 1])
      i++
    } else if (values[i] === '-sp' && i + 1 < values.length) {
      data.specific = values[i + 1]
      i++
    } else if (values[i] === '-tag' && i + 1 < values.length) {
      data.tags.push(values[i + 1])
      i++
    }
  }

  return data
}

function inferType(name: string): TodoType {
  if (inferFileType(name)) {
    return 'file'
  }

  if (inferNoteType(name)) {
    return 'note'
  }

  return 'single'
}

function inferFileType(name: string): boolean {
  const dot = name.lastIndexOf('.')
  const fileType = name.substring(dot + 1)

    const knowTypes = [
        "zip", "rar", "tar", "gz", "7z",
        "jpg", "png", "gif",
        "exe", "msi",
        "pdf", "xls", "xlsx", "doc", "docx", "ppt", "txt"
    ];

  if (knowTypes.indexOf(fileType) !== -1 && name.indexOf('http') !== -1) {
    return confirm('检测到链接类型为文件, 是否按照文件类型进行下载?')
  }

  return false
}

function inferNoteType(name: string): boolean {
  const knowType = ['计划', '规划', '事项', '分析', '笔记']

  for (const type of knowType) {
    // 当前的关键词有可能在标题中作为动词使用, 此时大概率并不期望创建Note
    // 因此调整为关键词必须结尾出现, 此时相关词汇更大概率为名词
    if (name.endsWith(type)) {
      return confirm('检测到代办类型包含关键词, 是否按照便签类型进行创建?')
    }
  }

  return false
}

function inferRepeatable(name: string): boolean {
  const knowType = ['每日']

  for (const type of knowType) {
    if (name.indexOf(type) !== -1) {
      return confirm('检测到关键词, 是否添加可重复属性?')
    }
  }

  return false
}

const DayMillisecond = 24 * 60 * 60 * 1000

function parsePriority(priority: TodoPriority) {
  const time = new Date()
  switch (priority) {
    case 'p0':
      return getTodayEndTime()
    case 'p1':
      return time.getTime() + Math.floor(2.5 * DayMillisecond)
    case 'p2':
      return time.getTime() + Math.floor(7 * DayMillisecond) 
  }
}

function getTodayEndTime(): number {
  const time = new Date()
  time.setHours(24, 0, 0, 0)
  return time.getTime()
}

function parseDeadline(deadline: string) {
  let data = /(\d+)\.(\d+)(:(\d+))?/.exec(deadline)
  if (data) {
    const month = data[1]
    const day = data[2]
    const hour = data[4] === undefined ? '10' : data[4]
    return parseDate(month, day, hour, '0', '0')
  }

  data = /[Ww](\d+)/.exec(deadline)
  if (data) {
    return parseWeek(parseInt(data[1], 10))
  }

  confirm(`截止日期解析异常: ${deadline}`)
}

function parseDate(tMonth: string, tDay: string, tHour: string, tMin: string, tSec: string): number {
    const nowTime = new Date();
    const nowYear = nowTime.getFullYear();
    let ans = new Date(nowYear + "-" + tMonth + "-" + tDay + " " + tHour + ":" + tMin + ":" + tSec);
    if (ans < nowTime) {
        const nextYear = nowYear + 1;
        ans = new Date(nextYear + "-" + tMonth + "-" + tDay + " " + tHour + ":" + tMin + ":" + tSec);
    }
    return ans.getTime();
}

function parseWeek(weekDay: number) {
  const time = new Date()
  const today = time.getDay()
  weekDay = weekDay % 7
  let diffDay = weekDay - today
  if (diffDay <= 0) {
    diffDay = 7 + diffDay
  }
  const diffTime = diffDay * DayMillisecond
  const curTime = time.getTime()
  return curTime + diffTime
}
