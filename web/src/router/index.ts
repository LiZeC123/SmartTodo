import { createRouter, createWebHistory } from 'vue-router'
import Login from '@/view/LoginPage.vue'
import Todo from '@/view/TodoPage.vue'
import Message from '@/view/MessagePage.vue'
import TomatoPage from '@/view/TomatoPage.vue'
import SummaryPage from '@/view/SummaryPage.vue'
import WeightRecordPage from '@/view/WeightRecordPage.vue'
import PomodoroTimer from '@/view/me/PomodoroTimer.vue'
import Checkin from '@/view/CheckinPage.vue'
import Assistant from '@/view/AssistantPage.vue'
import Index from '@/view/IndexPage.vue'
import WeightPlanPage from '@/view/WeightPlanPage.vue'
import ExercisePage from '@/view/ExercisePage.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/index' },
    { path: '/index', component: Index },
    { path: '/login', component: Login },
    { path: '/todo', component: Todo },
    { path: '/note/:id', component: Todo },
    { path: '/log/', component: Message },
    { path: '/tomato', component: TomatoPage },
    { path: '/assistant', component: Assistant },
    { path: '/checkin', component: Checkin },
    { path: '/summary', component: SummaryPage },
    { path: '/weight/plan', component: WeightPlanPage },
    { path: '/weight/record', component: WeightRecordPage },
    { path: '/exercise', component: ExercisePage },
    { path: '/me/tomato', component: PomodoroTimer }
  ]
})

export default router
