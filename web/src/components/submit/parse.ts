import type { TodoType, CreateItem, TodoPriority } from './types'

type OkResult<T> = { ok: true; data: T }
type ErrResult = { ok: false; error: Error }
type Result<T> = OkResult<T> | ErrResult

// 解析输入的待办事项文本, 根据文本内容附带必要的属性
export function parseTitleToData(todoContent: string, priority: TodoPriority): Result<CreateItem> {
  // 分析任务名称
  const values = todoContent.split(' ')
  let name = todoContent
  if (values.length > 1) {
    name = values[0]
  }

  // 分析类型
  const data: CreateItem = {
    name: name,
    itemType: inferType(name),
    priority: priority,
    repeatable: inferRepeatable(name),
    deadline: parsePriority(priority)
  }

  // 逻辑校验
  if (data.repeatable || data.itemType == 'note') {
    // 每日任务没有截止日期, note类型没有截止日期
    data.deadline = undefined
  } else if (!data.priority) {
    // 其他情况下必须指定优先级, 否则无法创建
    return { ok: false, error: new Error(`请先选择优先级`) }
  }

  // 如果只有两个部分, 且第二部分为数字, 则视为该任务的番茄钟数量
  if (values.length == 2) {
    const tc = parseInt(values[1])
    if (!isNaN(tc)) {
      if (tc < 1 || tc > 4) {
        return { ok: false, error: new Error(`单一任务的番茄钟数量取值为[1, 4]`) }
      } else {
        data.tomato_count = tc
        return { ok: true, data }
      }
    }
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
    }
  }

  return { ok: true, data }
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
    // 压缩包
    'zip',
    'rar',
    'tar',
    'gz',
    '7z',
    // 常见图片
    'jpg',
    'png',
    'gif',
    // 安装包
    'exe',
    'msi',
    // 常见文档
    'pdf',
    'xls',
    'xlsx',
    'doc',
    'docx',
    'ppt',
    'txt'
  ]

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
      return confirm('检测到便签类型关键词, 是否按照便签类型进行创建?')
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

function parsePriority(priority: TodoPriority): number {
  const time = new Date()
  // 高优任务当天完成, 非高优任务截止日期相对当前日期推迟一段时间
  switch (priority) {
    case 'p0':
      return getTodayEnd().getTime()
    case 'p1':
      return time.getTime() + 3 * DayMillisecond
    case 'p2':
      return time.getTime() + 7 * DayMillisecond
    case '':
      // 未指定优先级时, 先按照p2返回
      return time.getTime() + 7 * DayMillisecond
    default:
      throw new Error('未知的优先级类型')
  }
}

function getEndOfDay(date: Date): Date {
  const result = new Date(date)
  result.setHours(23, 59, 59, 999)
  return result
}

function getTodayEnd(): Date {
  const today = new Date()
  return getEndOfDay(today)
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

function parseDate(
  tMonth: string,
  tDay: string,
  tHour: string,
  tMin: string,
  tSec: string
): number {
  const nowTime = new Date()
  const nowYear = nowTime.getFullYear()
  let ans = new Date(nowYear + '-' + tMonth + '-' + tDay + ' ' + tHour + ':' + tMin + ':' + tSec)
  if (ans < nowTime) {
    const nextYear = nowYear + 1
    ans = new Date(nextYear + '-' + tMonth + '-' + tDay + ' ' + tHour + ':' + tMin + ':' + tSec)
  }
  return ans.getTime()
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
