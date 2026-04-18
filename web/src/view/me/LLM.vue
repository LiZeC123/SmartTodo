<!-- components/ChatComponent.vue -->
<template>
  <div class="chat-container">
    <div class="chat-history" ref="chatHistoryRef">
      <div v-for="(message, index) in messages" :key="index" 
           :class="['message', message.role]">
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
    
    <div class="input-area">
      <textarea 
        v-model="inputText" 
        @keydown.enter.prevent="sendMessage"
        placeholder="输入消息..."
        :disabled="isLoading"
      ></textarea>
      <button @click="sendMessage" :disabled="isLoading">
        {{ isLoading ? '生成中...' : '发送' }}
      </button>
    </div>
    
    <div v-if="error" class="error">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import axios from 'axios'
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'

interface Message {
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
}

const inputText = ref('')
const isLoading = ref(false)
const error = ref('')
const messages = reactive<Message[]>([])
let controller: AbortController | null = null

// 滚动容器 DOM 引用
const chatHistoryRef = ref<HTMLDivElement | null>(null)

// 添加消息
const addMessage = (role: 'user' | 'assistant', content: string, isStreaming = false) => {
  messages.push({ role, content, isStreaming })
}

// 更新最后一条消息（用于流式）
const updateLastMessage = (content: string, isStreaming = false) => {
  if (messages.length > 0) {
    const lastMsg = messages[messages.length - 1]
    lastMsg.content += content
    lastMsg.isStreaming = isStreaming
  }
}

// 流式API调用
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
      
      // 解析SSE格式
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || ''  // 保留未完成的数据
      
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

// 发送消息
const sendMessage = async () => {
  if (!inputText.value.trim() || isLoading.value) return
  
  let prompt = inputText.value.trim()
  inputText.value = ''
  error.value = ''
  isLoading.value = true

  if (prompt === '/step') {
    prompt = ''
      // 添加用户消息
    addMessage('user', '[用户没有输入]')
    await streamChat(prompt)
    return
  }

  if (prompt === '/remake') {
    messages.pop()
    await streamChat(prompt)
    return 
  }

  if (prompt === '/reset') {
    messages.length = 0
    resetChat()
    return 
  }

  if (prompt.startsWith("/replace " )) {
    messages.pop()
    messages.pop()
    prompt = prompt.replace(/^\/replace\s*/, '')
    // 添加用户消息
    addMessage('user', prompt)
    await streamChat(prompt)
    return
  }

  if (prompt === '/delete') {
    messages.pop()
    messages.pop()
    deleteLastChat()
    return 
  }
  
  // 添加用户消息
  addMessage('user', prompt)
  await streamChat(prompt)
}

function loadHistory() {
    axios.post<string[]>('assistant/history', {}).then(res => {
      messages.length = 0
      for(let i=0; i < res.data.length; i++) {
        const data = res.data[i]
        if( i % 2== 0)  {
          addMessage("user", data)
        } else {
          addMessage("assistant", data)
        }
      }
  })
}

function deleteLastChat() {
  axios.post('assistant/delete', {}).then(_ => {
    isLoading.value = false
  })
}

function resetChat() {
    axios.post('assistant/reset', {}).then(_ => {
    isLoading.value = false
  })
}

// 停止生成
const stopGeneration = () => {
  if (controller) {
    controller.abort()
    controller = null
  }
  isLoading.value = false
  
  // 标记最后一条消息为非流式
  if (messages.length > 0) {
    const lastMsg = messages[messages.length - 1]
    if (lastMsg.isStreaming) {
      lastMsg.isStreaming = false
    }
  }
}

// 组件卸载时清理
onUnmounted(() => {
  stopGeneration()
})

// 自动滚动到底部
const scrollToBottom = async () => {
  await nextTick() // 等待 DOM 更新完成
  if (chatHistoryRef.value) {
    chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight
  }
}

// 监听 messages 变化 → 自动滚动
watch(messages, () => {
  scrollToBottom()
}, { deep: true })

// 键盘快捷键
onMounted(() => {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && isLoading.value) {
      stopGeneration()
    }
  }
  
  window.addEventListener('keydown', handleKeyDown)
  onUnmounted(() => window.removeEventListener('keydown', handleKeyDown))
  loadHistory()
})
</script>

<style scoped>
.chat-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.chat-history {
  min-height: 400px;
  max-height: 500px;
  overflow-y: auto;
  border: 1px solid #ddd;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 20px;
  background: #f9f9f9;
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

.input-area {
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
}

button {
  padding: 10px 20px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 16px;
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
</style>