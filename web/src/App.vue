<script setup>
// OceanusPulse 根组件：三模块导航框架
// 视图文件就位后把下面的占位块替换为 <RouterView> 或动态组件
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <h1>OceanusPulse · 潮音脉</h1>
      <p class="subtitle">VAST Challenge 2025 MC1 · 音乐知识图谱可视分析</p>
    </header>
    <nav class="app-nav">
      <span class="nav-item">模块一 · 影响力溯源</span>
      <span class="nav-item">模块二 · 流派传播</span>
      <span class="nav-item">模块三 · 新星预测</span>
    </nav>
    <main class="app-main">
      <p class="placeholder">脚手架就绪。视图开发从 <code>src/views/</code> 开始，数据从 <code>data/processed/</code> 读取。</p>
    </main>
  </div>
</template>

<style scoped>
.app-shell { min-height: 100vh; display: flex; flex-direction: column; }
.app-header { padding: 20px 32px 8px; }
.app-header h1 { font-size: 22px; margin: 0; }
.subtitle { color: #666; font-size: 13px; margin: 4px 0 0; }
.app-nav { display: flex; gap: 24px; padding: 12px 32px; border-bottom: 1px solid #eee; }
.nav-item { font-size: 14px; color: #333; cursor: default; }
.app-main { flex: 1; padding: 32px; }
.placeholder { color: #999; font-size: 14px; }
</style>
