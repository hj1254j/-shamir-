<script setup>
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";

import http, { getErrorMessage } from "../api/http.js";

const LAST_SHARE_KEY = "traceable-secret-sharing:last-share";
const LAST_TRACE_KEY = "traceable-secret-sharing:last-trace";

function createReferenceShareRow(participantId) {
  return {
    participant_id: participantId,
    x: "",
    y: ""
  };
}

function createLeakedOutputRow() {
  return {
    leaked_y: ""
  };
}

const referenceShares = ref([
  createReferenceShareRow(1),
  createReferenceShareRow(2),
  createReferenceShareRow(3)
]);

const leakedOutputs = ref([createLeakedOutputRow()]);
const traceKeyText = ref("");
const loading = ref(false);
const traceResponse = ref(null);

const highlightedProofX = computed(() => {
  if (!traceResponse.value?.evidence) {
    return "";
  }

  const matchedEvidence = traceResponse.value.evidence.find((item) => item.proof_x);
  return matchedEvidence?.proof_x ?? "";
});

const resultTone = computed(() => {
  if (!traceResponse.value) {
    return "neutral";
  }

  if (traceResponse.value.trace_result === "success") {
    return "success";
  }

  if (traceResponse.value.trace_result === "ambiguous") {
    return "warning";
  }

  return "neutral";
});

const traceResultLabel = computed(() => {
  if (!traceResponse.value) {
    return "";
  }

  if (traceResponse.value.trace_result === "success") {
    return "已找到唯一叛徒";
  }

  if (traceResponse.value.trace_result === "ambiguous") {
    return "证据不唯一";
  }

  return "未找到有效匹配";
});

function isDecimalInteger(text) {
  return /^\d+$/.test(String(text).trim());
}

function addReferenceShareRow() {
  console.log("点击新增参考份额按钮：准备添加一行输入。");
  referenceShares.value.push(createReferenceShareRow(referenceShares.value.length + 1));
}

function removeReferenceShareRow(index) {
  console.log("点击删除参考份额按钮：准备删除索引为", index, "的输入行。");
  referenceShares.value.splice(index, 1);
}

function addLeakedOutputRow() {
  console.log("点击新增泄露输出按钮：准备添加一行输入。");
  leakedOutputs.value.push(createLeakedOutputRow());
}

function removeLeakedOutputRow(index) {
  console.log("点击删除泄露输出按钮：准备删除索引为", index, "的输入行。");
  leakedOutputs.value.splice(index, 1);
}

function loadLatestTraceMaterial() {
  console.log("点击载入最近一次分发按钮：准备读取追踪所需材料。");

  const cachedText = localStorage.getItem(LAST_SHARE_KEY);
  if (!cachedText) {
    ElMessage.warning("还没有最近一次秘密分发结果，请先去“秘密分发”页面生成份额。");
    return;
  }

  try {
    const cachedResult = JSON.parse(cachedText);
    const threshold = cachedResult.threshold ?? 3;
    const selectedShares = (cachedResult.shares ?? []).slice(0, threshold);

    referenceShares.value = selectedShares.map((item) => ({
      participant_id: item.participant_id,
      x: item.x,
      y: item.y
    }));

    leakedOutputs.value = cachedResult.shares?.length
      ? [{ leaked_y: cachedResult.shares[0].y }]
      : [createLeakedOutputRow()];

    traceKeyText.value = JSON.stringify(cachedResult.trace_key ?? [], null, 2);

    console.log("追踪页面所需材料已经载入。", {
      referenceShares: referenceShares.value,
      leakedOutputs: leakedOutputs.value,
      traceKey: traceKeyText.value
    });

    ElMessage.success("已载入最近一次分发结果作为追踪示例。");
  } catch (error) {
    console.log("读取最近一次分发缓存失败。", error);
    ElMessage.error("最近一次分发缓存损坏，请重新生成一次份额。");
  }
}

function parseTraceKeyText() {
  const cleanedText = traceKeyText.value.trim();

  if (cleanedText === "") {
    throw new Error("trace_key 不能为空。");
  }

  const parsedTraceKey = JSON.parse(cleanedText);

  if (!Array.isArray(parsedTraceKey) || parsedTraceKey.length === 0) {
    throw new Error("trace_key 必须是非空数组。");
  }

  return parsedTraceKey;
}

function validateTraceForm() {
  if (referenceShares.value.length === 0) {
    return "至少需要输入一个参考份额。";
  }

  for (let index = 0; index < referenceShares.value.length; index += 1) {
    const row = referenceShares.value[index];

    if (!Number.isInteger(row.participant_id) || row.participant_id <= 0) {
      return `第 ${index + 1} 行参考份额的 participant_id 必须是正整数。`;
    }

    if (!isDecimalInteger(row.x)) {
      return `第 ${index + 1} 行参考份额的 x 必须是十进制正整数。`;
    }

    if (BigInt(String(row.x).trim()) === 0n) {
      return `第 ${index + 1} 行参考份额的 x 不能为 0。`;
    }

    if (!isDecimalInteger(row.y)) {
      return `第 ${index + 1} 行参考份额的 y 必须是十进制非负整数。`;
    }
  }

  if (leakedOutputs.value.length === 0) {
    return "至少需要输入一个泄露输出。";
  }

  for (let index = 0; index < leakedOutputs.value.length; index += 1) {
    const row = leakedOutputs.value[index];

    if (!isDecimalInteger(row.leaked_y)) {
      return `第 ${index + 1} 行泄露输出的 leaked_y 必须是十进制非负整数。`;
    }
  }

  try {
    parseTraceKeyText();
  } catch (error) {
    return error.message || "trace_key 解析失败。";
  }

  return "";
}

function cacheTraceResult(requestPayload, responseData) {
  localStorage.setItem(
    LAST_TRACE_KEY,
    JSON.stringify({
      request: requestPayload,
      response: responseData
    })
  );
  console.log("叛徒追踪结果已写入浏览器本地缓存。");
}

async function submitTrace() {
  console.log("点击叛徒追踪按钮：准备提交 /api/trace。");

  const validationMessage = validateTraceForm();
  if (validationMessage) {
    ElMessage.error(validationMessage);
    return;
  }

  let parsedTraceKey;

  try {
    parsedTraceKey = parseTraceKeyText();
  } catch (error) {
    ElMessage.error(error.message || "trace_key 解析失败。");
    return;
  }

  const payload = {
    reference_shares: referenceShares.value.map((row) => ({
      participant_id: row.participant_id,
      x: String(row.x).trim(),
      y: String(row.y).trim()
    })),
    leaked_outputs: leakedOutputs.value.map((row) => ({
      leaked_y: String(row.leaked_y).trim()
    })),
    trace_key: parsedTraceKey
  };

  loading.value = true;

  try {
    console.log("开始调用叛徒追踪接口，请求体如下：", payload);
    const response = await http.post("/trace", payload);
    console.log("叛徒追踪接口调用成功，响应如下：", response.data);
    traceResponse.value = response.data;
    cacheTraceResult(payload, response.data);
    ElMessage.success("叛徒追踪执行完成。");
  } catch (error) {
    console.log("叛徒追踪接口调用失败。", error);
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
            <h3>参考份额输入区</h3>
            <p>这些份额会先参与拉格朗日插值，恢复出参考多项式 `q(x)`。</p>
          </div>

          <div class="inline-actions">
            <el-button plain @click="loadLatestTraceMaterial">载入最近一次分发结果</el-button>
            <el-button type="primary" plain @click="addReferenceShareRow">新增参考份额</el-button>
          </div>
        </div>

        <div class="dynamic-list">
          <div
            v-for="(row, index) in referenceShares"
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
              <el-input v-model="row.x" placeholder="请输入十进制字符串 x" />
            </div>

            <div>
              <label class="input-label">y</label>
              <el-input v-model="row.y" placeholder="请输入十进制字符串 y" />
            </div>

            <div class="row-actions">
              <el-button
                type="danger"
                plain
                :disabled="referenceShares.length === 1"
                @click="removeReferenceShareRow(index)"
              >
                删除
              </el-button>
            </div>
          </div>
        </div>
      </section>

      <section class="page-card">
        <div class="section-header">
          <div>
            <h3>泄露输出输入区</h3>
            <p>这里输入黑盒泄露出来的 `y`，后端会构造 `q(x) - y` 并在有限域中求根。</p>
          </div>

          <div class="inline-actions">
            <el-button type="primary" plain @click="addLeakedOutputRow">新增泄露输出</el-button>
          </div>
        </div>

        <div class="dynamic-list">
          <div
            v-for="(row, index) in leakedOutputs"
            :key="`leaked-${index}`"
            class="dynamic-row two-columns"
          >
            <div>
              <label class="input-label">leaked_y</label>
              <el-input
                v-model="row.leaked_y"
                placeholder="请输入泄露的 y 值"
              />
            </div>

            <div class="row-actions">
              <el-button
                type="danger"
                plain
                :disabled="leakedOutputs.length === 1"
                @click="removeLeakedOutputRow(index)"
              >
                删除
              </el-button>
            </div>
          </div>
        </div>

        <div style="margin-top: 18px">
          <label class="input-label">trace_key JSON</label>
          <el-input
            v-model="traceKeyText"
            class="editor-box"
            type="textarea"
            :rows="11"
            placeholder="请输入 trace_key 的 JSON 数组"
          />
        </div>

        <div class="stack-actions">
          <el-button type="primary" :loading="loading" @click="submitTrace">
            执行叛徒追踪
          </el-button>
        </div>
      </section>
    </div>

    <section
      v-if="traceResponse"
      :class="['result-banner', resultTone]"
    >
      <div>
        <p class="eyebrow-text">Trace Result</p>
        <h3>{{ traceResultLabel }}</h3>
        <p>
          `trace_result = {{ traceResponse.trace_result }}`。如果结果是 `ambiguous`，
          说明当前证据无法唯一锁定某个参与者。
        </p>
      </div>

      <div class="result-metrics">
        <div class="result-metric">
          <small>叛徒 ID</small>
          <strong>{{ traceResponse.traitor_id ?? "未确定" }}</strong>
        </div>
        <div class="result-metric">
          <small>proof_x</small>
          <strong class="mono-text">{{ highlightedProofX || "暂无" }}</strong>
        </div>
      </div>
    </section>

    <section class="page-card">
      <div class="section-header">
        <div>
          <h3>追踪证据表</h3>
          <p>每一行都展示一个 `leaked_y` 的求根结果、哈希匹配结果和可用于验证的 `proof_x`。</p>
        </div>
      </div>

      <template v-if="traceResponse">
        <el-table :data="traceResponse.evidence" stripe>
          <el-table-column prop="leaked_y" label="leaked_y" min-width="180" />
          <el-table-column label="candidate_x_values" min-width="260">
            <template #default="{ row }">
              <span class="mono-text">{{ row.candidate_x_values.join(", ") || "无" }}</span>
            </template>
          </el-table-column>
          <el-table-column label="matched_participant_ids" min-width="200">
            <template #default="{ row }">
              {{ row.matched_participant_ids.join(", ") || "无" }}
            </template>
          </el-table-column>
          <el-table-column prop="proof_x" label="proof_x" min-width="220" />
        </el-table>
      </template>
      <div v-else class="empty-hint">
        还没有追踪结果。建议先载入最近一次分发结果，再用其中一个份额的 `y` 做演示。
      </div>
    </section>
  </div>
</template>
