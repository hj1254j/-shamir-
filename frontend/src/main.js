import { createApp } from "vue";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";

import App from "./App.vue";
import router from "./router/index.js";
import "./styles/global.css";

console.log("前端启动：准备创建 Vue 应用。");

const app = createApp(App);

app.use(router);
app.use(ElementPlus);
app.mount("#app");

console.log("前端启动：Vue 应用挂载完成。");
