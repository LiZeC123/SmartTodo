import { OneMinuteMS } from './types'

export function playNotifacationAudio() {
  const audio = document.getElementById('notificationAudio') as HTMLAudioElement
  if (audio) {
    audio.loop = true
    audio.play()
    setTimeout(() => audio.pause(), OneMinuteMS)
  }
}

export function sendNotification(title: string, body: string) {
  new Notification(title, { body })
}

export function sendTomatoNotification(taskName: string) {
  sendNotification('完成一个番茄钟了, 休息一下吧~', '任务: ' + taskName)
}
