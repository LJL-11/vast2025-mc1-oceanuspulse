import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import "./styles/main.css";
import "./styles/network.css";
import "./styles/navigation.css";

createApp(App).use(createPinia()).mount("#app");
