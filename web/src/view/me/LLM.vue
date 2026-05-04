<!-- components/ChatComponent.vue -->
<template>
  <div class="chat-container">
    <div class="chat-history" ref="chatHistoryRef">
      <div v-for="(message, index) in messages" :key="index" :class="['message', message.role]">
        <div class="message-content">
          <!-- 流式消息显示 -->
          <span v-if="message.isStreaming" class="streaming-text">
            {{ message.content }}
            <span class="cursor">|</span>
          </span>
          <span v-else>{{ message.content }}</span>
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

interface Message {
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}

// 指令列表定义
const COMMANDS = [
  { command: '/rk', description: '重新生成最后一次回答', needsSpace: false },
  { command: '/du', description: '显示系统注入的用户信息', needsSpace: false },
  { command: '/da', description: '显示所有会话信息', needsSpace: false },
  { command: '/rr', description: '切换助理角色 (支持[角色名] [输入消息])', needsSpace: true },
  { command: '/rs', description: '重置会话(支持 [角色名])', needsSpace: true },
  { command: '/rc', description: '替换最后一条用户消息', needsSpace: true },
  { command: '/delete', description: '删除最后一条对话 (同步后端)', needsSpace: false },
]

const inputText = ref('')
const isLoading = ref(false)
const error = ref('')
const messages = reactive<Message[]>([])
let controller: AbortController | null = null

// DOM 引用
const chatHistoryRef = ref<HTMLDivElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const inputAreaRef = ref<HTMLDivElement | null>(null)
const completionPanelRef = ref<HTMLDivElement | null>(null)

// 指令补全状态
const showCompletion = ref(false)
const selectedIndex = ref(0)
let lastFilterWord = '' // 用于过滤时的缓存

// 根据用户输入过滤指令（取 '/' 后面的部分作为过滤词）
const filteredCommands = computed(() => {
  if (!inputText.value.startsWith('/')) return []
  const filterPart = inputText.value.slice(1) // 去掉开头的 '/'
  lastFilterWord = filterPart
  if (!filterPart) return COMMANDS
  return COMMANDS.filter(cmd => 
    cmd.command.slice(1).toLowerCase().startsWith(filterPart.toLowerCase())
  )
})

// 处理输入事件，控制补全面板显示/隐藏
const handleInput = () => {
  if (inputText.value && inputText.value[0] === '/') {
    showCompletion.value = true
    selectedIndex.value = 0
  } else {
    showCompletion.value = false
  }
}

// 选择指令并填入输入框
const selectCommand = (cmd: { command: string; description: string; needsSpace: boolean }) => {
  let newValue = cmd.command
  if (cmd.needsSpace) {
    newValue += ' '
  }
  inputText.value = newValue
  showCompletion.value = false
  // 让 textarea 重新获得焦点
  nextTick(() => {
    textareaRef.value?.focus()
  })
}

// 键盘事件处理（支持补全导航、发送消息、换行）
const handleKeydown = (e: KeyboardEvent) => {
  // 处理补全面板的键盘导航
  if (showCompletion.value && filteredCommands.value.length) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      selectedIndex.value = (selectedIndex.value + 1) % filteredCommands.value.length
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      selectedIndex.value = (selectedIndex.value - 1 + filteredCommands.value.length) % filteredCommands.value.length
    } else if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      // 如果有补全面板，选中当前高亮的指令
      if (showCompletion.value && filteredCommands.value[selectedIndex.value]) {
        selectCommand(filteredCommands.value[selectedIndex.value])
      }
      return
    } else if (e.key === 'Escape') {
      e.preventDefault()
      showCompletion.value = false
      return
    }
  }
  
  // 处理发送消息：Enter (非 Shift 组合) 且没有补全面板激活时
  if (e.key === 'Enter' && !e.shiftKey && !showCompletion.value) {
    e.preventDefault()
    sendMessage()
  }
  // Shift+Enter 让 textarea 默认插入换行，不做额外处理
}

// 点击外部关闭补全面板
const handleClickOutside = (e: MouseEvent) => {
  if (!showCompletion.value) return
  const target = e.target as HTMLElement
  const isClickInside = 
    textareaRef.value?.contains(target) ||
    completionPanelRef.value?.contains(target)
  if (!isClickInside) {
    showCompletion.value = false
  }
}

// 原有功能：添加消息、流式对话等保持不变
const addMessage = (role: 'user' | 'assistant', content: string, isStreaming = false) => {
  messages.push({ role, content, isStreaming })
}

const updateLastMessage = (content: string, isStreaming = false) => {
  if (messages.length > 0) {
    const lastMsg = messages[messages.length - 1]
    lastMsg.content += content
    lastMsg.isStreaming = isStreaming
  }
}

const streamChat = async (prompt: string) => {
  controller = new AbortController()

  try {
    const response = await fetch('/api/stream/assistant/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ prompt }),
      signal: controller.signal
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

    addMessage('assistant', '', true)

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
            if (data.error) {
              error.value = data.error
              break
            }
            if (data.text) {
              updateLastMessage(data.text, !data.done)
            }
            if (data.done) {
              const lastMsg = messages[messages.length - 1]
              if (lastMsg) {
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

const sendMessage = async () => {
  if (!inputText.value.trim() || isLoading.value) return

  let prompt = inputText.value.trim()
  inputText.value = ''
  error.value = ''
  isLoading.value = true
  showCompletion.value = false  // 发送时关闭补全面板

  if (prompt === '/') {
    prompt = ''
    addMessage('user', '[用户没有输入]')
    await streamChat(prompt)
    return
  }

  if (prompt.startsWith('/rr ')) {
    addMessage('user', '[用户切换了助理角色]')
    await streamChat(prompt)
    return
  }

  if (prompt === '/rk') {
    messages.pop()
    await streamChat(prompt)
    return
  }

  if (prompt.startsWith('/rs')) {
    messages.length = 0
    addMessage('user', '[用户重置了会话]')
    await streamChat(prompt)
    return
  }

  if (prompt.startsWith("/rc ")) {
    messages.pop()
    messages.pop()
    addMessage('user', prompt.replace(/^\/replace\s*/, ''))
    await streamChat(prompt)
    return
  }

  if (prompt === '/delete') {
    messages.pop()
    messages.pop()
    deleteLastChat()
    return
  }

  addMessage('user', prompt)
  await streamChat(prompt)
}

interface AssistantMsg {
  role: 'user' | 'assistant'
  msg: string
}

function loadHistory() {
  axios.post<AssistantMsg[]>('assistant/history', {}).then(res => {
    messages.length = 0
    for (let i = 0; i < res.data.length; i++) {
      const data = res.data[i]
      addMessage(data.role, data.msg)
    }
  })
}

function deleteLastChat() {
  axios.post('assistant/delete', {}).then(_ => {
    isLoading.value = false
  })
}

const stopGeneration = () => {
  if (controller) {
    controller.abort()
    controller = null
  }
  isLoading.value = false
  if (messages.length > 0) {
    const lastMsg = messages[messages.length - 1]
    if (lastMsg.isStreaming) {
      lastMsg.isStreaming = false
    }
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (chatHistoryRef.value) {
    chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight
  }
}

watch(messages, () => {
  scrollToBottom()
}, { deep: true })

onMounted(() => {
  document.title = '私人助理'
  
  // 全局点击外部关闭补全
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
  height: 100dvh;           /* 全屏高度 */
  display: flex;
  flex-direction: column;
  padding: 20px;
  box-sizing: border-box;  /* 避免 padding 导致溢出 */
  overflow: hidden;        /* 防止整个页面滚动 */
}

/* 聊天区域自动填充剩余空间 */
.chat-history {
  flex: 1;                 /* 自动占据剩余高度 */
  overflow-y: auto;        /* 内部滚动 */
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
  background: #f9f9f9;
  margin-bottom: 15px;     /* 与输入区留一点空隙 */
  min-height: 0;           /* flex 子项防止溢出关键 */
}

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
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* 输入区域保持自动高度 */
.input-area {
  flex-shrink: 0;          /* 不被压缩 */
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
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
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