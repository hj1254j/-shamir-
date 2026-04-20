import { createRouter, createWebHistory } from "vue-router";

import ShareView from "../views/ShareView.vue";
import ReconstructView from "../views/ReconstructView.vue";
import TraceView from "../views/TraceView.vue";
import VerifyView from "../views/VerifyView.vue";

console.log("路由初始化：准备创建四个教学页面。");

const routes = [
  {
    path: "/",
    redirect: "/share"
  },
  {
    path: "/share",
    name: "share",
    component: ShareView,
    meta: {
      title: "秘密分发",
      eyebrow: "Step 01",
      description: "生成带有追踪标签的 Shamir 份额，并同步给出追踪密钥与验证密钥。"
    }
  },
  {
    path: "/reconstruct",
    name: "reconstruct",
    component: ReconstructView,
    meta: {
      title: "秘密重构",
      eyebrow: "Step 02",
      description: "输入若干份额，做拉格朗日插值恢复 q(0)，观察秘密如何被重构出来。"
    }
  },
  {
    path: "/trace",
    name: "trace",
    component: TraceView,
    meta: {
      title: "叛徒追踪",
      eyebrow: "Step 03",
      description: "先用参考份额恢复 q(x)，再对 q(x)=y 求根，最后结合 trace_key 找回真实 x。"
    }
  },
  {
    path: "/verify",
    name: "verify",
    component: VerifyView,
    meta: {
      title: "防诬陷验证",
      eyebrow: "Step 04",
      description: "把 proof_x 再走一遍哈希比对，验证证据是否真的命中嫌疑人的验证密钥。"
    }
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

router.afterEach((to) => {
  console.log("路由切换完成：当前页面是", to.path);
  document.title = `${to.meta.title ?? "可追踪秘密共享"} - 可追踪秘密共享教学台`;
});

export default router;
