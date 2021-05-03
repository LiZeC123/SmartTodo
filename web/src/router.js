import Vue from "vue";
import VueRouter from "vue-router"
import Login from "@/view/Login";
import Main from "@/view/Main";
import NoteComponent from "@/components/NoteComponent";
import FileComponent from "@/components/FileComponent";
import TodoComponent from "@/components/TodoComponent";
import LogTypeComponent from "@/components/LogTypeComponent";


Vue.use(VueRouter)

export default new VueRouter({
    mode: 'history',
    routes: [
        {path: '/', redirect: '/home/todo'},
        {path: '/login', component: Login},
        {
            path: '/home', component: Main,
            children: [
                {path: 'todo', component: TodoComponent},
                {path: 'note/:id', component: NoteComponent},
                {path: 'log/:type', component: LogTypeComponent},
                {path: 'file', component: FileComponent},
            ]
        },
    ]
})