import { OneMinuteMS } from './types'

let fadeInterval: number

export function playNotifacationAudio() {
  const audio = document.getElementById('notificationAudioBase') as HTMLAudioElement
  if (audio) {
    audio.loop = true
    doFadeIn(audio)
    audio.play()
    setTimeout(() => audio.pause(), (OneMinuteMS / 60) * 99)
  }
}

export function playNotifacationAudioShort() {
  const audio = document.getElementById('notificationAudioShort') as HTMLAudioElement
  if (audio) {
    doFadeIn(audio)
    audio.play()
  }
}

function doFadeIn(audio: HTMLAudioElement) {
  audio.volume = 0
  // 设置淡入效果
  if (fadeInterval) clearInterval(fadeInterval)
  fadeInterval = setInterval(() => {
    if (audio.volume < 0.95) {
      audio.volume += 0.05
    } else {
      audio.volume = 1
      clearInterval(fadeInterval)
    }
  }, 250)
}
