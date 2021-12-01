import {createRouter, createWebHistory} from 'vue-router'
import Login from "@/view/Login";
import Main from "@/view/Main";
import NoteComponent from "@/components/NoteComponent";
import TodoComponent from "@/components/TodoComponent";
import LogTypeComponent from "@/components/LogTypeComponent";
import TomatoPage from "@/components/TomatoPage";

const routes = [
    {path: '/', redirect: '/home/todo'},
    {path: '/login', component: Login},
    {
        path: '/home', component: Main,
        children: [
            {path: 'todo', component: TodoComponent},
            {path: 'note/:id', component: NoteComponent},
            {path: 'log/:type', component: LogTypeComponent},
            {path: 'tomato', component: TomatoPage},
        ]
    },
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

export default router
