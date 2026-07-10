import { createRouter, createWebHistory } from 'vue-router'
import Login from '@/view/LoginPage.vue'
import Todo from '@/view/TodoPage.vue'
import Message from '@/view/MessagePage.vue'
import TomatoPage from '@/view/TomatoPage.vue'
import WeightRecordPage from '@/view/WeightRecordPage.vue'
import Checkin from '@/view/CheckinPage.vue'
import Assistant from '@/view/AssistantPage.vue'
import Index from '@/view/IndexPage.vue'
import ExercisePage from '@/view/ExercisePage.vue'

const WeightPlanPage = () => import('@/view/WeightPlanPage.vue')
const TodaySummaryPage = () => import('@/view/TodaySummaryPage.vue')
const LongSummaryPage = () => import('@/view/LongSummaryPage.vue')

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
    { path: '/summary/today', component: TodaySummaryPage },
    { path: '/summary/longterm', component: LongSummaryPage },
    { path: '/weight/plan', component: WeightPlanPage },
    { path: '/weight/record', component: WeightRecordPage },
    { path: '/exercise', component: ExercisePage }
  ]
})

export default router
