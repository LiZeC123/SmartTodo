import {createRouter, createWebHistory} from 'vue-router'
import Login from "@/view/Login";
import Main from "@/view/Main";
import NotePage from "@/components/NotePage";
import TodoPage from "@/components/TodoPage";
import LogTypeComponent from "@/components/LogTypePage";
import SummaryPage from "@/components/SummaryPage";
import Config from "@/components/Config";

const routes = [
    {path: '/', redirect: '/home/todo'},
    {path: '/login', component: Login},
    {
        path: '/home', component: Main,
        children: [
            {path: 'todo', component: TodoPage},
            {path: 'note/:id', component: NotePage},
            {path: 'log/:type', component: LogTypeComponent},
            {path: 'summary', component: SummaryPage},
            {path: 'config', component: Config}
        ]
    },
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

export default router
