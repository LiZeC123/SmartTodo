export function doAction(role: string) {
  const baseAction = ['h1', 'h2', 'p']

  if (baseAction.indexOf(role) !== -1) {
    document.execCommand('formatBlock', false, '<' + role + '>')
  } else {
    document.execCommand(role, false)
  }
}

export function tab(event: KeyboardEvent) {
  insertHTML(event, '&nbsp;&nbsp;&nbsp;&nbsp;')
}

export function line(event: KeyboardEvent) {
  insertHTML(event, '<hr />')
}

export function note(event: KeyboardEvent) {
  insertHTML(event, '<blockquote class="quote"><b>Note</b>:</blockquote>')
}

export function insertHTML(event: KeyboardEvent, content: string) {
  // 阻止默认切换元素的行为
  if (event && event.preventDefault) {
    event.preventDefault()
  }

  const selection = event.view?.getSelection()
  if (selection === null || selection === undefined) {
    return
  }

  // 获取光标的range对象 event.view 是一个window对象
  const range = selection.getRangeAt(0)
  // 光标的偏移位置
  const offset = range.startOffset
  // 新建一个span元素
  const span = document.createElement('span')
  // 插入给定的内容
  span.innerHTML = content
  // 创建一个新的range对象
  const newRange = document.createRange()
  // 设置新的range的位置，也是插入元素的位置
  newRange.setStart(range.startContainer, offset)
  newRange.setEnd(range.startContainer, offset)
  newRange.collapse(true)
  newRange.insertNode(span)
  // 去掉旧的range对象，用新的range对象替换
  selection.removeAllRanges()
  selection.addRange(range)
  // 将光标的位置向后移动一个偏移量，放到加入的四个空格后面
  range.setStart(span, 1)
  range.setEnd(span, 1)
}
