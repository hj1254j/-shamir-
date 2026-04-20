<script setup>
import { ref } from "vue";
import { ElMessage } from "element-plus";

import http, { getErrorMessage } from "../api/http.js";

const LAST_SHARE_KEY = "traceable-secret-sharing:last-share";

function createShareRow(participantId) {
  return {
    participant_id: participantId,
    x: "",
    y: ""
  };
}

const shareRows = ref([
  createShareRow(1),
  createShareRow(2),
  createShareRow(3)
]);

const loading = ref(false);
const reconstructResult = ref("");

function isDecimalInteger(text) {
  return /^\d+$/.test(String(text).trim());
}

function addShareRow() {
  console.log("点击新增份额按钮：准备添加一行输入。");
  shareRows.value.push(createShareRow(shareRows.value.length + 1));
}

function removeShareRow(index) {
  console.log("点击删除份额按钮：准备删除索引为", index, "的输入行。");
  shareRows.value.splice(index, 1);
}

function loadLatestShareRows() {
  console.log("点击载入最近分发结果按钮：准备读取浏览器缓存中的份额。");

  const cachedText = localStorage.getItem(LAST_SHARE_KEY);
  if (!cachedText) {
    ElMessage.warning("还没有最近一次秘密分发结果，请先去“秘密分发”页面生成份额。");
    return;
  }

  try {
    const cachedResult = JSON.parse(cachedText);
    const recommendedCount = Math.max(3, cachedResult.threshold ?? 3);
    const selectedShares = (cachedResult.shares ?? []).slice(0, recommendedCount);

    if (selectedShares.length === 0) {
      ElMessage.warning("缓存里没有可用份额，请重新生成一次。");
      return;
    }

    shareRows.value = selectedShares.map((item) => ({
      participant_id: item.participant_id,
      x: item.x,
      y: item.y
    }));

    console.log("最近一次分发结果已成功载入到重构页面。", shareRows.value);
    ElMessage.success("已载入最近一次分发结果中的参考份额。");
  } catch (error) {
    console.log("读取最近一次分发缓存失败。", error);
    ElMessage.error("最近一次分发缓存损坏，请重新生成一次份额。");
  }
}

function validateRows() {
  if (shareRows.value.length === 0) {
    return "至少需要输入一行份额。";
  }

  for (let index = 0; index < shareRows.value.length; index += 1) {
    const row = shareRows.value[index];

    if (!Number.isInteger(row.participant_id) || row.participant_id <= 0) {
      return `第 ${index + 1} 行的 participant_id 必须是正整数。`;
    }

    if (!isDecimalInteger(row.x)) {
      return `第 ${index + 1} 行的 x 必须是十进制正整数。`;
    }

    if (BigInt(String(row.x).trim()) === 0n) {
      return `第 ${index + 1} 行的 x 不能为 0。`;
    }

    if (!isDecimalInteger(row.y)) {
      return `第 ${index + 1} 行的 y 必须是十进制非负整数。`;
    }
  }

  return "";
}

async function submitReconstruct() {
  console.log("点击秘密重构按钮：准备提交 /api/rec。");

  const validationMessage = validateRows();
  if (validationMessage) {
    ElMessage.error(validationMessage);
    return;
  }

  const payload = {
    shares: shareRows.value.map((row) => ({
      participant_id: row.participant_id,
      x: String(row.x).trim(),
      y: String(row.y).trim()
    }))
  };

  loading.value = true;

  try {
    console.log("开始调用秘密重构接口，请求体如下：", payload);
    const response = await http.post("/rec", payload);
    console.log("秘密重构接口调用成功，响应如下：", response.data);
    reconstructResult.value = response.data.recovered_secret;
    ElMessage.success("秘密重构成功。");
  } catch (error) {
    console.log("秘密重构接口调用失败。", error);
    ElMessage.error(getErrorMessage(error));
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="page-stack">
    <section class="page-card">
      <div class="section-header">
        <div>
          <h3>份额输入区</h3>
          <p>这里输入要参与重构的份额。你可以手动填写，也可以直接载入最近一次分发结果。</p>
        </div>

        <div class="inline-actions">
          <el-button plain @click="loadLatestShareRows">载入最近一次分发结果</el-button>
          <el-button type="primary" plain @click="addShareRow">新增一行份额</el-button>
        </div>
      </div>

      <div class="dynamic-list">
        <div
          v-for="(row, index) in shareRows"
          :key="`${index}-${row.participant_id}`"
          class="dynamic-row"
        >
          <div>
            <label class="input-label">参与者 ID</label>
            <el-input-number
              v-model="row.participant_id"
              :min="1"
              :step="1"
              controls-position="right"
            />
          </div>

          <div>
            <label class="input-label">x</label>
            <el-input
              v-model="row.x"
              placeholder="请输入十进制字符串 x"
            />
          </div>

          <div>
            <label class="input-label">y</label>
            <el-input
              v-model="row.y"
              placeholder="请输入十进制字符串 y"
            />
          </div>

          <div class="row-actions">
            <el-button
              type="danger"
              plain
              :disabled="shareRows.length === 1"
              @click="removeShareRow(index)"
            >
              删除
            </el-button>
          </div>
        </div>
      </div>

      <p class="helper-text">
        如果这些份额来自最近一次分发结果，后端会根据缓存到的门限提示你是否“份额数量不足”。
      </p>

      <div class="stack-actions">
        <el-button type="primary" :loading="loading" @click="submitReconstruct">
          执行秘密重构
        </el-button>
      </div>
    </section>

    <section
      v-if="reconstructResult"
      class="result-banner success"
    >
      <div>
        <p class="eyebrow-text">Reconstruction Result</p>
        <h3>秘密重构完成</h3>
        <p>后端已经完成拉格朗日插值，下面这个值就是恢复出来的 `q(0)`。</p>
      </div>

      <div class="result-metrics">
        <div class="result-metric">
          <small>恢复出的秘密</small>
          <strong class="mono-text">{{ reconstructResult }}</strong>
        </div>
      </div>
    </section>

    <section class="page-card">
      <div class="section-header">
        <div>
          <h3>观察重点</h3>
          <p>重构页面最适合对照浏览器和后端日志一起看。</p>
        </div>
      </div>

      <pre class="data-pre">1. 浏览器先把字符串份额送到 /api/rec
2. 后端把 x、y 放回 GF(p)
3. 对所有输入点做拉格朗日插值
4. 取恢复出的多项式常数项 q(0)
5. 返回 recovered_secret</pre>
    </section>
  </div>
</template>
