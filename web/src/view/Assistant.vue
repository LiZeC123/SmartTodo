<!-- components/ChatComponent.vue -->
<template>
  <div class="chat-container">
    <div class="chat-history" ref="chatHistoryRef" @scroll="handleScroll">
      <!-- 顶部：加载更多指示器 -->
      <div v-if="isLoadingMore" class="loading-more">
        <span class="loading-spinner"></span>
        <span>加载中...</span>
      </div>
      <div v-else-if="!hasMore && messages.length > 0" class="no-more">
        —— 没有更多历史记录 ——
      </div>

      <!-- 渲染显示列表（包含日期分割线和后台分割线） -->
      <div v-for="(item, idx) in displayMessages" :key="idx">
        <!-- 普通文本消息 -->
        <div v-if="item.type === 'text'" :class="['message', item.role]">
          <div class="message-content">
            <span v-if="item.isStreaming" class="streaming-text">
              {{ item.content }}
              <span class="cursor">|</span>
            </span>
            <span v-else>{{ item.content }}</span>
          </div>
        </div>

        <!-- 后台主动返回的分割线（中间带文字） -->
        <div v-else-if="item.type === 'divider'" class="divider-wrapper">
          <div class="divider-line"></div>
          <div class="divider-text">{{ item.label }}</div>
          <div class="divider-line"></div>
        </div>

        <!-- 日期分割线（不同天时自动插入） -->
        <div v-else-if="item.type === 'dateDivider'" class="date-divider">
          <div class="date-divider-line"></div>
          <div class="date-divider-text">{{ item.date }}</div>
          <div class="date-divider-line"></div>
        </div>
      </div>
    </div>

    <div class="input-area" ref="inputAreaRef">
      <textarea
        v-model="inputText"
        @keydown="handleKeydown"
        @input="handleInput"
        placeholder="输入消息... (以 / 开头可查看指令补全)"
        :disabled="isLoading"
        ref="textareaRef"
      ></textarea>

      <!-- 指令补全面板 -->
      <div
        v-if="showCompletion && filteredCommands.length"
        class="completion-panel"
        ref="completionPanelRef"
      >
        <div
          v-for="(cmd, idx) in filteredCommands"
          :key="cmd.command"
          :class="['completion-item', { selected: idx === selectedIndex }]"
          @click="selectCommand(cmd)"
          @mouseenter="selectedIndex = idx"
        >
          <span class="cmd-text">{{ cmd.command }}</span>
          <span class="cmd-desc">{{ cmd.description }}</span>
        </div>
      </div>

      <button @click="sendMessage" :disabled="isLoading">
        {{ isLoading ? '生成中...' : '发送' }}
      </button>
    </div>

    <div v-if="error" class="error">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ref, reactive, onMounted, onUnmounted, nextTick, watch, computed } from 'vue'

// ---------- 类型定义 ----------
interface TextMessage {
  type: 'text'
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
  createTime?: string // 格式 '%Y-%m-%d %H:%M:%S'
}

interface DividerMessage {
  type: 'divider'
  label: string
}

// 显示用（日期分割线只出现在展示列表中，不存储在原始消息数组）
interface DateDivider {
  type: 'dateDivider'
  date: string
}

type ChatMessage = TextMessage | DividerMessage
type DisplayItem = ChatMessage | DateDivider

// 指令列表定义
const COMMANDS = [
  { command: '/switch', description: '切换助理 (参数 [角色名])', needsSpace: true },

  { command: '/cost', description: '查看所有角色会话成本', needsSpace: false },
  { command: '/memory', description: '查看当前角色的记忆', needsSpace: false },
  { command: '/info', description: '显示当前状态信息', needsSpace: false },

  { command: '/reason', description: '查看上一次模型思考内容', needsSpace: false },
  { command: '/set_memory', description: '覆盖当前角色的记忆 (参数 [记忆文本])', needsSpace: true },
  { command: '/set_time', description: '修改记忆截止时间 (参数 [月.日:时 格式时间字符串])', needsSpace: true },
  { command: '/rewrite', description: '重写当前角色的记忆 (参数 [重写要求])', needsSpace: true },

  { command: '/rumor', description: '对当前角色注入流言蜚语', needsSpace: false },

  { command: '/inject', description: '注入数据 (参数 [数据名称] [prompt])', needsSpace: true },

  { command: '/change_mode', description: '切换助理模式 (参数 [模式名("助理"或"扮演")])', needsSpace: true },
  { command: '/role_list', description: '显示所有角色信息', needsSpace: false },
  { command: '/da', description: '显示所有会话信息', needsSpace: false },

  { command: '/rk', description: '重新生成最后一次回答', needsSpace: false },
  { command: '/rc', description: '替换最后一条用户消息', needsSpace: true },
  { command: '/delete', description: '删除n轮对话 (参数 [对话轮数])', needsSpace: true },
]

// ---------- 响应式数据 ----------
const inputText = ref('')
const isLoading = ref(false)
const error = ref('')
const messages = reactive<ChatMessage[]>([]) // 存储原始消息（文本 + 后台分割线）
let controller: AbortController | null = null

// 加载更多相关状态
const isLoadingMore = ref(false)
const hasMore = ref(true)
const skipAutoScroll = ref(false)

// DOM 引用
const chatHistoryRef = ref<HTMLDivElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const inputAreaRef = ref<HTMLDivElement | null>(null)
const completionPanelRef = ref<HTMLDivElement | null>(null)

// 指令补全状态
const showCompletion = ref(false)
const selectedIndex = ref(0)
let lastFilterWord = ''

// ---------- 辅助函数 ----------
// 获取当前时间的格式化字符串
const getCurrentTimeStr = () => {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  const hours = String(now.getHours()).padStart(2, '0')
  const minutes = String(now.getMinutes()).padStart(2, '0')
  const seconds = String(now.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

// 添加文本消息
const addTextMessage = (role: 'user' | 'assistant', content: string, isStreaming = false, createTime?: string) => {
  const time = createTime || (role === 'user' ? getCurrentTimeStr() : undefined)
  messages.push({
    type: 'text',
    role,
    content,
    isStreaming,
    createTime: time,
  })
}

// 更新最后一条文本消息的内容（流式场景）
const updateLastTextMessage = (content: string, isStreaming = false) => {
  const lastMsg = messages[messages.length - 1]
  if (lastMsg && lastMsg.type === 'text') {
    lastMsg.content += content
    lastMsg.isStreaming = isStreaming
  }
}

// 设置最后一条文本消息的创建时间（流式完成时）
const setLastTextMessageTime = (createTime: string) => {
  const lastMsg = messages[messages.length - 1]
  if (lastMsg && lastMsg.type === 'text' && lastMsg.role === 'assistant') {
    lastMsg.createTime = createTime
  }
}

// 添加后台分割线消息
const addDividerMessage = (label: string) => {
  messages.push({
    type: 'divider',
    label: label,
  })
}

// ---------- 日期分割线逻辑（生成展示列表） ----------
// 提取日期部分（yyyy-mm-dd）
const getDatePart = (dateTimeStr?: string) => {
  if (!dateTimeStr) return null
  return dateTimeStr.split(' ')[0]
}

// 格式化日期显示（如 "2025年1月15日"）
const formatDisplayDate = (dateStr: string) => {
  const [year, month, day] = dateStr.split('-')
  return `${year}年${parseInt(month)}月${parseInt(day)}日`
}

// 生成最终显示的列表（自动插入日期分割线）
const displayMessages = computed<DisplayItem[]>(() => {
  const result: DisplayItem[] = []
  let lastDate: string | null = null

  for (const msg of messages) {
    // 后台分割线：直接加入，不影响日期比较
    if (msg.type === 'divider') {
      result.push(msg)
      continue
    }

    // 文本消息
    if (msg.type === 'text') {
      const currentDate = getDatePart(msg.createTime)

      // 如果当前消息有创建时间，并且与上一条消息不是同一天，则插入日期分割线
      if (currentDate && lastDate !== currentDate) {
        result.push({
          type: 'dateDivider',
          date: formatDisplayDate(currentDate),
        })
        lastDate = currentDate
      }

      result.push(msg)

      // 对于没有创建时间的消息，不更新 lastDate，避免干扰后续比较
      if (!currentDate) {
        // 保持 lastDate 不变
      }
    }
  }

  return result
})

// ---------- 获取当前第一条有 createTime 的消息时间 ----------
// 用于加载更多时作为入参；如果第一条没有则顺延使用第二条，以此类推
const getFirstMessageTime = (): string | null => {
  for (const msg of messages) {
    if (msg.type === 'text' && msg.createTime) {
      return msg.createTime
    }
  }
  return null
}

// ---------- 加载更多历史记录 ----------
const loadMoreHistory = async () => {
  // 防止重复加载
  if (isLoadingMore.value || !hasMore.value) return

  const beforeTime = getFirstMessageTime()
  if (!beforeTime) return // 没有任何带时间的消息，无法定位

  isLoadingMore.value = true
  skipAutoScroll.value = true

  // 记录加载前滚动容器的 scrollHeight，用于后续恢复位置
  const container = chatHistoryRef.value
  const prevScrollHeight = container?.scrollHeight || 0

  try {
    const res = await axios.post<ChatMessage[]>('assistant/history/more', {
      before_time: beforeTime,
    })
    const newMessages = res.data

    // 如果返回空数组，说明没有更多历史记录了
    if (!newMessages || newMessages.length === 0) {
      hasMore.value = false
      return
    }

    // 将新消息插入到数组前面（保持从旧到新的顺序）
    // 新消息按时间升序排列（最旧的在前），从后往前遍历并用 unshift 插入
    for (let i = newMessages.length - 1; i >= 0; i--) {
      const data = newMessages[i]
      if (data.type === 'divider') {
        messages.unshift({ type: 'divider', label: data.label })
      } else {
        const createTime = (data as TextMessage).createTime || undefined
        messages.unshift({
          type: 'text',
          role: (data as TextMessage).role,
          content: (data as TextMessage).content,
          isStreaming: false,
          createTime: createTime,
        })
      }
    }

    // 恢复滚动位置：新 scrollHeight - 旧 scrollHeight = 新增内容的高度
    await nextTick()
    if (container) {
      const newScrollHeight = container.scrollHeight
      container.scrollTop = newScrollHeight - prevScrollHeight
    }
  } catch (err) {
    console.error('加载更多历史失败:', err)
    // 网络错误不设置 hasMore = false，允许用户重试
  } finally {
    isLoadingMore.value = false
    // 延迟重置 skipAutoScroll，确保 watch 回调在标志有效期内执行
    await nextTick()
    skipAutoScroll.value = false
  }
}

// ---------- 滚动事件处理 ----------
const handleScroll = () => {
  const container = chatHistoryRef.value
  if (!container) return

  // 当滚动到距离顶部 50px 以内时触发加载更多
  if (container.scrollTop <= 50) {
    loadMoreHistory()
  }
}

// ---------- 流式对话核心（支持分隔符和 create_time）----------
const streamChat = async (prompt: string) => {
  controller = new AbortController()

  try {
    const response = await fetch('/api/stream/assistant/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prompt }),
      signal: controller.signal,
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    if (!response.body) {
      throw new Error('No response body')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    // 先添加一个空的助手消息用于流式更新
    addTextMessage('assistant', '', true)

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.substring(6)
          if (dataStr === '[DONE]') continue

          try {
            const data = JSON.parse(dataStr)

            // 处理后台错误
            if (data.error) {
              error.value = data.error
              break
            }

            // 处理分隔符类型消息
            if (data.type === 'divider') {
              const label = data.label || data.text || '分隔线'
              addDividerMessage(label)
              continue
            }

            // 普通文本消息（文本块）
            if (data.text !== undefined) {
              updateLastTextMessage(data.text, !data.done)
            }

            // 流式完成，设置创建时间
            if (data.done) {
              // 从后端返回的 create_time 字段中获取时间（如果没有则使用当前时间）
              const createTime = data.create_time || getCurrentTimeStr()
              setLastTextMessageTime(createTime)
              // 确保消息流式标记关闭
              const lastMsg = messages[messages.length - 1]
              if (lastMsg && lastMsg.type === 'text') {
                lastMsg.isStreaming = false
              }
              return
            }
          } catch (e) {
            console.error('解析SSE数据失败:', e)
          }
        }
      }
    }
  } catch (err: any) {
    if (err.name !== 'AbortError') {
      error.value = '请求失败: ' + err.message
      console.error('Stream error:', err)
    }
  } finally {
    isLoading.value = false
  }
}

function loadHistory() {
  // 重置加载更多状态
  hasMore.value = true

  axios
    .post<ChatMessage[]>('assistant/history', {})
    .then((res) => {
      messages.length = 0 // 清空原有消息
      for (let i = 0; i < res.data.length; i++) {
        const data = res.data[i]
        if (data.type === 'divider') {
          addDividerMessage(data.label)
        } else {
          // 确保时间字段存在，若没有则置为 undefined（不影响日期分割线逻辑）
          const createTime = (data as TextMessage).createTime || undefined
          addTextMessage((data as TextMessage).role, (data as TextMessage).content, false, createTime)
        }
      }
    })
    .catch((err) => {
      console.error('加载历史失败:', err)
      error.value = '加载历史记录失败'
    })
}

// ---------- 删除最后一条对话 ----------
async function deleteLastChat(num: number) {
  await axios.post('assistant/delete', { num: num })
  loadHistory()
  isLoading.value = false
}

// ---------- 发送消息（支持指令）----------
const sendMessage = async () => {
  if (!inputText.value.trim() || isLoading.value) return

  let prompt = inputText.value.trim()
  inputText.value = ''
  error.value = ''
  isLoading.value = true
  showCompletion.value = false

  // 根据指令分支处理
  if (prompt === '/') {
    prompt = ''
    addTextMessage('user', '[用户没有输入]', false, getCurrentTimeStr())
    await streamChat(prompt)
  } else if (prompt.startsWith('/switch ')) {
    addTextMessage('user', '[用户切换了助理角色]', false, getCurrentTimeStr())
    await streamChat(prompt)
    loadHistory() // 切换角色后刷新历史
  } else if (prompt === '/rk') {
    // 修复 /rk 指令：删除最后一条 assistant 类型的文本消息
    // 从后往前找最后一条角色为 assistant 的文本消息
    let lastAssistantIndex = -1
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i]
      if (msg.type === 'text' && msg.role === 'assistant') {
        lastAssistantIndex = i
        break
      }
    }
    if (lastAssistantIndex !== -1) {
      messages.splice(lastAssistantIndex, 1)
    }
    await streamChat(prompt)
  } else if (prompt.startsWith('/rc ')) {
    // 修复 /rc 指令：替换最后一条用户消息（同时删除对应的助手消息）
    // 删除最后一条 user 文本消息
    let lastUserIndex = -1
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i]
      if (msg.type === 'text' && msg.role === 'user') {
        lastUserIndex = i
        break
      }
    }
    if (lastUserIndex !== -1) {
      messages.splice(lastUserIndex, 1)
    }

    // 删除最后一条 assistant 文本消息（可能位于被删除的用户消息之后，但需要重新查找）
    let lastAssistantIndex = -1
    for (let i = messages.length - 1; i >= 0; i--) {
      const msg = messages[i]
      if (msg.type === 'text' && msg.role === 'assistant') {
        lastAssistantIndex = i
        break
      }
    }
    if (lastAssistantIndex !== -1) {
      messages.splice(lastAssistantIndex, 1)
    }

    // 提取新的用户消息内容（去掉 "/rc " 前缀）
    const newUserMsg = prompt.replace(/^\/rc\s*/, '')
    addTextMessage('user', newUserMsg, false, getCurrentTimeStr())
    await streamChat(prompt)
  } else if (prompt.startsWith('/delete')) {
    const num_str = prompt.replace(/^\/delete\s*/, '')
    let num = parseInt(num_str, 10)
    if (isNaN(num)) {
      num = 1
    }

    await deleteLastChat(num)
  } else {
    // 普通消息：添加用户消息（带当前时间），然后发起流式请求
    addTextMessage('user', prompt, false, getCurrentTimeStr())
    await streamChat(prompt)
  }

  // 发送完成后重新聚焦
  await nextTick()
  if (!isMobile()) {
    textareaRef.value?.focus()
  }
}

// ---------- 停止生成 ----------
const stopGeneration = () => {
  if (controller) {
    controller.abort()
    controller = null
  }
  isLoading.value = false
  const lastMsg = messages[messages.length - 1]
  if (lastMsg && lastMsg.type === 'text' && lastMsg.isStreaming) {
    lastMsg.isStreaming = false
    // 若停止时没有时间，补充一个当前时间
    if (!lastMsg.createTime) {
      lastMsg.createTime = getCurrentTimeStr()
    }
  }
}

// ---------- 指令补全相关逻辑 ----------
const filteredCommands = computed(() => {
  if (!inputText.value.startsWith('/')) return []
  const filterPart = inputText.value.slice(1)
  lastFilterWord = filterPart
  if (!filterPart) return COMMANDS
  return COMMANDS.filter((cmd) => cmd.command.slice(1).toLowerCase().startsWith(filterPart.toLowerCase()))
})

const handleInput = () => {
  if (inputText.value && inputText.value[0] === '/') {
    showCompletion.value = true
    selectedIndex.value = 0
  } else {
    showCompletion.value = false
  }
}

const selectCommand = (cmd: { command: string; description: string; needsSpace: boolean }) => {
  let newValue = cmd.command
  if (cmd.needsSpace) {
    newValue += ' '
  }
  inputText.value = newValue
  showCompletion.value = false
  nextTick(() => {
    textareaRef.value?.focus()
  })
}

const handleKeydown = (e: KeyboardEvent) => {
  if (showCompletion.value && filteredCommands.value.length) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      selectedIndex.value = (selectedIndex.value + 1) % filteredCommands.value.length
      return
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      selectedIndex.value =
        (selectedIndex.value - 1 + filteredCommands.value.length) % filteredCommands.value.length
      return
    } else if (e.key === 'Escape') {
      e.preventDefault()
      showCompletion.value = false
      return
    }
  }

  if (e.key === 'Enter') {
    if (e.shiftKey) return
    e.preventDefault()
    if (
      showCompletion.value &&
      filteredCommands.value.length &&
      filteredCommands.value[selectedIndex.value]
    ) {
      selectCommand(filteredCommands.value[selectedIndex.value])
      return
    }
    sendMessage()
  }
}

const handleClickOutside = (e: MouseEvent) => {
  if (!showCompletion.value) return
  const target = e.target as HTMLElement
  const isClickInside =
    textareaRef.value?.contains(target) || completionPanelRef.value?.contains(target)
  if (!isClickInside) {
    showCompletion.value = false
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatHistoryRef.value) {
    chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight
  }
}

// 监听消息变化，滚动到底部（加载更多时跳过）
watch(
  () => messages.length,
  () => {
    if (skipAutoScroll.value) return
    scrollToBottom()
  },
  { deep: true }
)

watch(
  displayMessages,
  () => {
    if (skipAutoScroll.value) return
    scrollToBottom()
  },
  { deep: true }
)

const isMobile = () => {
  return (
    /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
    ('ontouchstart' in window)
  )
}

// ---------- 生命周期 ----------
onMounted(() => {
  document.title = '私人助理'
  document.addEventListener('click', handleClickOutside)

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && isLoading.value) {
      stopGeneration()
    }
  }
  window.addEventListener('keydown', handleKeyDown)

  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyDown)
    document.removeEventListener('click', handleClickOutside)
  })

  loadHistory()
})

onUnmounted(() => {
  stopGeneration()
})
</script>

<style scoped>
/* 让整个容器占满视口高度 */
.chat-container {
  max-width: 800px;
  margin: 0 auto;
  height: 100dvh; /* 全屏高度 */
  display: flex;
  flex-direction: column;
  padding: 20px;
  box-sizing: border-box; /* 避免 padding 导致溢出 */
  overflow: hidden; /* 防止整个页面滚动 */
}

/* 聊天区域自动填充剩余空间 */
.chat-history {
  flex: 1; /* 自动占据剩余高度 */
  overflow-y: auto; /* 内部滚动 */
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
  background: #f9f9f9;
  margin-bottom: 15px; /* 与输入区留一点空隙 */
  min-height: 0; /* flex 子项防止溢出关键 */
}

/* 加载更多指示器样式 */
.loading-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 0;
  margin-bottom: 8px;
  color: #888;
  font-size: 13px;
}

.loading-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid #ddd;
  border-top-color: #888;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.no-more {
  text-align: center;
  padding: 12px 0;
  margin-bottom: 8px;
  color: #aaa;
  font-size: 13px;
}

/* 普通消息样式 */
.message {
  margin-bottom: 15px;
  padding: 10px;
  border-radius: 8px;
  white-space: pre-line;
}

.message.user {
  background: #e3f2fd;
  text-align: right;
}

.message.assistant {
  background: #f5f5f5;
  text-align: left;
}

.streaming-text {
  display: inline-block;
}

.cursor {
  animation: blink 1s infinite;
  color: #666;
}

@keyframes blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
}

/* 后台主动分割线样式（中间带文字） */
.divider-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 16px 0;
  gap: 12px;
}

.divider-line {
  flex: 1;
  height: 1px;
  background: #ddd;
}

.divider-text {
  font-size: 13px;
  color: #888;
  background: #f9f9f9;
  padding: 0 12px;
  white-space: nowrap;
}

/* 日期分割线样式（不同天自动插入） */
.date-divider {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 40px 0;
  gap: 12px;
}

.date-divider-line {
  flex: 1;
  height: 1px;
  background: #ccc;
}

.date-divider-text {
  font-size: 14px;
  color: #666;
  background: #f9f9f9;
  padding: 0 12px;
  white-space: nowrap;
  font-weight: 500;
}

/* 输入区域样式 */
.input-area {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

textarea {
  min-height: 100px;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 14px;
  resize: vertical;
  font-family: inherit;
}

button {
  padding: 10px 20px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
  transition: background 0.2s;
}

button:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.error {
  color: #d32f2f;
  padding: 10px;
  background: #ffebee;
  border-radius: 4px;
  margin-top: 10px;
}

/* 指令补全面板样式 */
.completion-panel {
  background: white;
  border: 1px solid #ddd;
  border-radius: 6px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  max-height: 200px;
  overflow-y: auto;
  z-index: 10;
  margin-top: 2px;
}

.completion-item {
  padding: 8px 12px;
  display: flex;
  align-items: baseline;
  gap: 12px;
  cursor: pointer;
  transition: background 0.15s;
  border-bottom: 1px solid #f0f0f0;
}

.completion-item:last-child {
  border-bottom: none;
}

.completion-item.selected,
.completion-item:hover {
  background: #e8f0fe;
}

.cmd-text {
  font-weight: 600;
  color: #1a73e8;
  font-family: monospace;
  font-size: 14px;
  min-width: 70px;
}

.cmd-desc {
  font-size: 13px;
  color: #555;
  flex: 1;
}
</style>