import Vue from "vue";
import VueRouter from "vue-router"
import Login from "@/view/Login";
import Main from "@/view/Main";
import NoteComponent from "@/components/NoteComponent";
import FileComponent from "@/components/FileComponent";
import TodoComponent from "@/components/TodoComponent";


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
                {path: 'note', component: NoteComponent},
                {path: 'file', component: FileComponent},
            ]
        },

    ]
})