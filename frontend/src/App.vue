<script setup>
import { computed } from "vue";
import { RouterView, useRoute, useRouter } from "vue-router";

const router = useRouter();
const route = useRoute();

const navigationItems = [
  {
    index: "01",
    path: "/share",
    title: "秘密分发",
    eyebrow: "Step 01",
    description: "输入秘密、份额数量和门限，生成份额与密钥。"
  },
  {
    index: "02",
    path: "/reconstruct",
    title: "秘密重构",
    eyebrow: "Step 02",
    description: "把足够的份额重新拼回 q(0)，验证 Shamir 重构流程。"
  },
  {
    index: "03",
    path: "/trace",
    title: "叛徒追踪",
    eyebrow: "Step 03",
    description: "用参考份额恢复多项式，再从泄露 y 中找出真正的 x。"
  },
  {
    index: "04",
    path: "/verify",
    title: "防诬陷验证",
    eyebrow: "Step 04",
    description: "把 proof_x 再次做哈希比对，确认最终证据是否成立。"
  }
];

const currentNavigationItem = computed(() => {
  return navigationItems.find((item) => item.path === route.path) ?? navigationItems[0];
});

function handleMenuSelect(path) {
  console.log("左侧导航点击：准备切换到页面", path);
  router.push(path);
}
</script>

<template>
  <div class="app-shell">
    <aside class="nav-panel">
      <div class="brand-block">
        <p class="eyebrow-text">教学版密码学演示</p>
        <h1>可追踪秘密共享教学台</h1>
        <p class="brand-copy">
          从分发、重构、追踪到验证，沿着一条清晰的中文学习路径，把
          <code>Shamir + Hash(x)</code> 跑通并看见每一步日志。
        </p>
      </div>

      <el-menu
        :default-active="route.path"
        class="nav-menu"
        @select="handleMenuSelect"
      >
        <el-menu-item
          v-for="item in navigationItems"
          :key="item.path"
          :index="item.path"
        >
          <span class="nav-index">{{ item.index }}</span>
          <span class="nav-copy">
            <strong>{{ item.title }}</strong>
            <small>{{ item.description }}</small>
          </span>
        </el-menu-item>
      </el-menu>

      <div class="nav-note">
        <p class="note-label">固定有限域</p>
        <strong>GF(2305843009213693951)</strong>
        <p class="note-copy">
          所有有限域大整数在前后端之间统一按十进制字符串传输，避免浏览器数值精度丢失。
        </p>
      </div>
    </aside>

    <main class="content-panel">
      <header class="hero-panel">
        <div class="hero-copy">
          <p class="eyebrow-text">{{ currentNavigationItem.eyebrow }}</p>
          <h2>{{ currentNavigationItem.title }}</h2>
          <p>{{ currentNavigationItem.description }}</p>
        </div>

        <div class="hero-tags">
          <span class="hero-tag">教学版</span>
          <span class="hero-tag alt">完美黑盒</span>
        </div>
      </header>

      <section class="view-panel">
        <RouterView />
      </section>
    </main>
  </div>
</template>
