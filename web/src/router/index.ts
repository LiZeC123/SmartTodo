import { createRouter, createWebHistory } from 'vue-router'
import Login from '@/view/LoginPage.vue'
import Todo from '@/view/TodoPage.vue'
import Message from '@/view/MessagePage.vue'
import TomatoPage from '@/view/TomatoPage.vue'
import SummaryPage from '@/view/SummaryPage.vue'
import CreditsPage from '@/view/me/CreditsPage.vue'
import WeightRecord from '@/view/me/WeightRecord.vue'
import PomodoroTimer from '@/view/me/PomodoroTimer.vue'
import WelfarePage from '@/view/me/WelfarePage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/todo' },
    { path: '/login', component: Login },
    { path: '/todo', component: Todo },
    { path: '/note/:id', component: Todo },
    { path: '/log/:type', component: Message },
    { path: '/tomato', component: TomatoPage },
    { path: '/summary', component: SummaryPage },
    { path: '/me/credits', component: CreditsPage },
    { path: '/me/weight', component: WeightRecord },
    { path: '/me/tomato', component: PomodoroTimer },
    { path: '/me/welfare', component: WelfarePage },
  ]
})

export default router
