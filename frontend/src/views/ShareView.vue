<script setup>
import { computed, reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import http, { getErrorMessage } from "../api/http.js";

const FIELD_PRIME = "2305843009213693951";
const LAST_SHARE_KEY = "traceable-secret-sharing:last-share";

const shareForm = reactive({
  secret: "1234",
  share_count: 5,
  threshold: 3
});

const loading = ref(false);
const shareResult = ref(null);

const verifyParticipants = computed(() => {
  return shareResult.value?.verify_key?.participants ?? [];
});

function isDecimalInteger(text) {
  return /^\d+$/.test(String(text).trim());
}

function resetDemoValues() {
  console.log("点击示例参数按钮：准备恢复默认教学参数。");
  shareForm.secret = "1234";
  shareForm.share_count = 5;
  shareForm.threshold = 3;
}

function validateShareForm() {
  const secretText = String(shareForm.secret ?? "").trim();

  if (!isDecimalInteger(secretText)) {
    return "秘密必须是十进制非负整数。";
  }

  const secretValue = BigInt(secretText);
  const fieldPrimeValue = BigInt(FIELD_PRIME);

  if (secretValue >= fieldPrimeValue) {
    return `秘密必须满足 0 <= secret < p，当前 p = ${FIELD_PRIME}。`;
  }

  if (!Number.isInteger(shareForm.share_count) || shareForm.share_count <= 0) {
    return "份额数量必须是正整数。";
  }

  if (!Number.isInteger(shareForm.threshold) || shareForm.threshold <= 0) {
    return "门限必须是正整数。";
  }

  if (shareForm.threshold > shareForm.share_count) {
    return "门限不能大于份额数量。";
  }

  return "";
}

function cacheShareResult(data) {
  localStorage.setItem(LAST_SHARE_KEY, JSON.stringify(data));
  console.log("秘密分发结果已写入浏览器本地缓存，供其他页面直接复用。");
}

async function submitShare() {
  console.log("点击秘密分发按钮：准备提交 /api/share。");

  const validationMessage = validateShareForm();
  if (validationMessage) {
    ElMessage.error(validationMessage);
    return;
  }

  const payload = {
    secret: String(shareForm.secret).trim(),
    share_count: shareForm.share_count,
    threshold: shareForm.threshold
  };

  loading.value = true;

  try {
    console.log("开始调用秘密分发接口，请求体如下：", payload);
    const response = await http.post("/share", payload);
    console.log("秘密分发接口调用成功，响应如下：", response.data);
    shareResult.value = response.data;
    cacheShareResult(response.data);
    ElMessage.success("秘密分发成功，结果已经更新。");
  } catch (error) {
    console.log("秘密分发接口调用失败。", error);
    ElMessage.error(getErrorMessage(error));
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="page-stack">
    <div class="page-grid two-up">
      <section class="page-card">
        <div class="section-header">
          <div>
            <h3>输入分发参数</h3>
            <p>这里输入秘密、份额数量和门限，后端会生成 Shamir 份额与追踪标签。</p>
          </div>
          <div class="inline-actions">
            <el-button plain @click="resetDemoValues">恢复示例参数</el-button>
          </div>
        </div>

        <div class="form-grid">
          <div>
            <label class="input-label">秘密 `secret`</label>
            <el-input
              v-model="shareForm.secret"
              placeholder="请输入十进制秘密，例如 1234"
            />
          </div>

          <div>
            <label class="input-label">份额数量 `share_count`</label>
            <el-input-number
              v-model="shareForm.share_count"
              :min="1"
              :step="1"
              controls-position="right"
            />
          </div>

          <div>
            <label class="input-label">门限 `threshold`</label>
            <el-input-number
              v-model="shareForm.threshold"
              :min="1"
              :step="1"
              controls-position="right"
            />
          </div>
        </div>

        <p class="helper-text">
          教学默认值推荐使用 `secret = "1234"`、`share_count = 5`、`threshold = 3`。
        </p>

        <div class="stack-actions">
          <el-button type="primary" :loading="loading" @click="submitShare">
            开始秘密分发
          </el-button>
        </div>
      </section>

      <section class="page-card">
        <div class="section-header">
          <div>
            <h3>规则提示</h3>
            <p>这张卡片帮助你在提交前确认教学版的固定规则。</p>
          </div>
        </div>

        <div class="tag-row">
          <el-tag effect="dark">有限域 GF(p)</el-tag>
          <el-tag type="success">Hash(x) = SHA-256(str(x))</el-tag>
          <el-tag type="warning">大整数按字符串传输</el-tag>
        </div>

        <p class="helper-text">
          当前固定素数：
          <span class="mono-text">{{ FIELD_PRIME }}</span>
        </p>

        <pre class="data-pre">0 &lt;= secret &lt; p
threshold &lt;= share_count
shares[i] = (x, y = q(x))
trace_hash = SHA-256(str(x).encode("utf-8"))</pre>
      </section>
    </div>

    <section
      v-if="shareResult"
      class="result-banner success"
    >
      <div>
        <p class="eyebrow-text">Share Ready</p>
        <h3>秘密分发完成</h3>
        <p>份额、追踪密钥和验证密钥都已经生成，你可以直接去后续页面继续做重构、追踪和验证。</p>
      </div>

      <div class="result-metrics">
        <div class="result-metric">
          <small>秘密</small>
          <strong class="mono-text">{{ shareResult.secret }}</strong>
        </div>
        <div class="result-metric">
          <small>门限 / 份额数量</small>
          <strong>{{ shareResult.threshold }} / {{ shareResult.share_count }}</strong>
        </div>
      </div>
    </section>

    <div class="page-grid two-up">
      <section class="page-card">
        <div class="section-header">
          <div>
            <h3>份额表</h3>
            <p>每个参与者都会拿到一个 `(x, y)`，并附带对应的追踪哈希。</p>
          </div>
        </div>

        <template v-if="shareResult">
          <p class="table-caption">字段中的 `x` 和 `y` 都是十进制字符串。</p>
          <el-table :data="shareResult.shares" stripe>
            <el-table-column prop="participant_id" label="参与者 ID" min-width="110" />
            <el-table-column prop="x" label="x" min-width="180" />
            <el-table-column prop="y" label="y" min-width="180" />
            <el-table-column prop="trace_hash" label="trace_hash" min-width="260" />
          </el-table>
        </template>
        <div v-else class="empty-hint">
          还没有分发结果。先点击“开始秘密分发”，这里会显示完整的份额表。
        </div>
      </section>

      <section class="page-card">
        <div class="section-header">
          <div>
            <h3>追踪密钥</h3>
            <p>追踪时不会直接看到参与者的真实 `x`，而是通过 `trace_hash` 来匹配候选根。</p>
          </div>
        </div>

        <template v-if="shareResult">
          <el-table :data="shareResult.trace_key" stripe>
            <el-table-column prop="participant_id" label="参与者 ID" min-width="110" />
            <el-table-column prop="trace_hash" label="trace_hash" min-width="300" />
          </el-table>
        </template>
        <div v-else class="empty-hint">
          还没有追踪密钥。生成份额后，这里会同步出现对应的 `trace_key`。
        </div>
      </section>
    </div>

    <section class="page-card">
      <div class="section-header">
        <div>
          <h3>验证密钥</h3>
          <p>防诬陷验证阶段会再次使用这里的哈希信息，确认 `proof_x` 是否真的属于嫌疑人。</p>
        </div>
      </div>

      <template v-if="shareResult">
        <div class="tag-row">
          <el-tag type="success">hash_algorithm = {{ shareResult.verify_key.hash_algorithm }}</el-tag>
        </div>
        <el-table :data="verifyParticipants" stripe style="margin-top: 16px">
          <el-table-column prop="participant_id" label="参与者 ID" min-width="110" />
          <el-table-column prop="trace_hash" label="trace_hash" min-width="320" />
        </el-table>
      </template>
      <div v-else class="empty-hint">
        还没有验证密钥。生成份额后，这里会展示 `verify_key` 对应的参与者哈希列表。
      </div>
    </section>
  </div>
</template>
