<script setup>
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import http, { getErrorMessage } from "../api/http.js";

const FIELD_PRIME = "2305843009213693951";
const LAST_SHARE_KEY = "traceable-secret-sharing:last-share";
const LAST_TRACE_KEY = "traceable-secret-sharing:last-trace";

const verifyKeyText = ref("");
const loading = ref(false);
const verifyResponse = ref(null);

const verifyForm = reactive({
  suspect_participant_id: 1,
  proof_x: ""
});

function isDecimalInteger(text) {
  return /^\d+$/.test(String(text).trim());
}

function loadLatestVerifyKey(silent = false) {
  console.log("点击载入最近一次验证密钥按钮：准备读取浏览器缓存。");

  const cachedText = localStorage.getItem(LAST_SHARE_KEY);
  if (!cachedText) {
    if (!silent) {
      ElMessage.warning("还没有最近一次秘密分发结果，请先去“秘密分发”页面生成份额。");
    }
    return;
  }

  try {
    const cachedResult = JSON.parse(cachedText);
    verifyKeyText.value = JSON.stringify(cachedResult.verify_key ?? {}, null, 2);
    console.log("验证密钥已成功载入。", verifyKeyText.value);
    if (!silent) {
      ElMessage.success("已载入最近一次分发结果中的验证密钥。");
    }
  } catch (error) {
    console.log("读取最近一次分发缓存失败。", error);
    if (!silent) {
      ElMessage.error("最近一次分发缓存损坏，请重新生成一次份额。");
    }
  }
}

function loadLatestTraceProof(silent = false) {
  console.log("点击载入最近一次追踪证据按钮：准备读取追踪缓存。");

  const cachedText = localStorage.getItem(LAST_TRACE_KEY);
  if (!cachedText) {
    if (!silent) {
      ElMessage.warning("还没有最近一次叛徒追踪结果，请先去“叛徒追踪”页面执行追踪。");
    }
    return;
  }

  try {
    const cachedTrace = JSON.parse(cachedText);
    const response = cachedTrace.response ?? {};
    const proofItem = (response.evidence ?? []).find((item) => item.proof_x);

    if (response.traitor_id) {
      verifyForm.suspect_participant_id = response.traitor_id;
    }

    if (proofItem?.proof_x) {
      verifyForm.proof_x = proofItem.proof_x;
    }

    console.log("最近一次追踪证据已成功载入。", {
      suspect_participant_id: verifyForm.suspect_participant_id,
      proof_x: verifyForm.proof_x
    });

    if (!silent) {
      ElMessage.success("已载入最近一次追踪得到的嫌疑人和 proof_x。");
    }
  } catch (error) {
    console.log("读取最近一次追踪缓存失败。", error);
    if (!silent) {
      ElMessage.error("最近一次追踪缓存损坏，请重新执行叛徒追踪。");
    }
  }
}

function parseVerifyKeyText() {
  const cleanedText = verifyKeyText.value.trim();

  if (cleanedText === "") {
    throw new Error("verify_key 不能为空。");
  }

  const parsedVerifyKey = JSON.parse(cleanedText);

  if (!parsedVerifyKey || typeof parsedVerifyKey !== "object") {
    throw new Error("verify_key 必须是 JSON 对象。");
  }

  return parsedVerifyKey;
}

function validateVerifyForm() {
  if (!Number.isInteger(verifyForm.suspect_participant_id) || verifyForm.suspect_participant_id <= 0) {
    return "嫌疑人 ID 必须是正整数。";
  }

  if (!isDecimalInteger(verifyForm.proof_x)) {
    return "proof_x 必须是十进制正整数。";
  }

  const proofXValue = BigInt(String(verifyForm.proof_x).trim());
  if (proofXValue === 0n) {
    return "proof_x 必须是十进制正整数。";
  }

  if (proofXValue >= BigInt(FIELD_PRIME)) {
    return `proof_x 必须满足 0 < proof_x < p，当前 p = ${FIELD_PRIME}。`;
  }

  try {
    parseVerifyKeyText();
  } catch (error) {
    return error.message || "verify_key 解析失败。";
  }

  return "";
}

async function submitVerify() {
  console.log("点击防诬陷验证按钮：准备提交 /api/verify。");

  const validationMessage = validateVerifyForm();
  if (validationMessage) {
    ElMessage.error(validationMessage);
    return;
  }

  let parsedVerifyKey;

  try {
    parsedVerifyKey = parseVerifyKeyText();
  } catch (error) {
    ElMessage.error(error.message || "verify_key 解析失败。");
    return;
  }

  const payload = {
    verify_key: parsedVerifyKey,
    suspect_participant_id: verifyForm.suspect_participant_id,
    proof_x: String(verifyForm.proof_x).trim()
  };

  loading.value = true;

  try {
    console.log("开始调用防诬陷验证接口，请求体如下：", payload);
    const response = await http.post("/verify", payload);
    console.log("防诬陷验证接口调用成功，响应如下：", response.data);
    verifyResponse.value = response.data;
    ElMessage.success("防诬陷验证执行完成。");
  } catch (error) {
    console.log("防诬陷验证接口调用失败。", error);
    ElMessage.error(getErrorMessage(error));
  } finally {
    loading.value = false;
  }
}

loadLatestVerifyKey(true);
loadLatestTraceProof(true);
</script>

<template>
  <div class="page-stack">
    <div class="page-grid two-up">
      <section class="page-card">
        <div class="section-header">
          <div>
            <h3>验证输入区</h3>
            <p>这里要输入验证密钥、嫌疑人 ID 和 `proof_x`，后端会重新计算 `Hash(proof_x)` 做最终比对。</p>
          </div>

          <div class="inline-actions">
            <el-button plain @click="loadLatestVerifyKey">载入最近一次验证密钥</el-button>
            <el-button plain @click="loadLatestTraceProof">载入最近一次追踪证据</el-button>
          </div>
        </div>

        <div class="double-grid">
          <div>
            <label class="input-label">嫌疑人 ID</label>
            <el-input-number
              v-model="verifyForm.suspect_participant_id"
              :min="1"
              :step="1"
              controls-position="right"
            />
          </div>

          <div>
            <label class="input-label">proof_x</label>
            <el-input
              v-model="verifyForm.proof_x"
              placeholder="请输入十进制字符串 proof_x"
            />
          </div>
        </div>

        <div style="margin-top: 18px">
          <label class="input-label">verify_key JSON</label>
          <el-input
            v-model="verifyKeyText"
            class="editor-box"
            type="textarea"
            :rows="14"
            placeholder="请输入 verify_key 的 JSON 对象"
          />
        </div>

        <div class="stack-actions">
          <el-button type="primary" :loading="loading" @click="submitVerify">
            执行防诬陷验证
          </el-button>
        </div>
      </section>

      <section class="page-card">
        <div class="section-header">
          <div>
            <h3>验证规则提醒</h3>
            <p>这一页只做一件事：确认 `proof_x` 的哈希是否真的命中嫌疑人的验证密钥。</p>
          </div>
        </div>

        <pre class="data-pre">1. 从 verify_key 中找到 suspect_participant_id 对应的 trace_hash
2. 计算 provided_hash = SHA-256(str(proof_x))
3. 比较 expected_hash 与 provided_hash
4. 相同则通过，不同则拒绝</pre>

        <p class="helper-text">
          当前固定要求：
          <span class="mono-text">0 &lt; proof_x &lt; {{ FIELD_PRIME }}</span>
        </p>
      </section>
    </div>

    <section
      v-if="verifyResponse"
      :class="['status-panel', verifyResponse.verified ? 'success' : 'failure']"
    >
      <p class="eyebrow-text">Verify Result</p>
      <h3>{{ verifyResponse.verified ? "验证通过" : "验证拒绝" }}</h3>
      <p>{{ verifyResponse.message }}</p>

      <div class="status-grid">
        <div class="status-item">
          <small>expected_hash</small>
          <strong class="mono-text">{{ verifyResponse.expected_hash }}</strong>
        </div>

        <div class="status-item">
          <small>provided_hash</small>
          <strong class="mono-text">{{ verifyResponse.provided_hash }}</strong>
        </div>
      </div>
    </section>

    <section class="page-card">
      <div class="section-header">
        <div>
          <h3>结果解读</h3>
          <p>绿色表示证据和验证密钥一致，红色表示哈希对不上，因而不能指控这个嫌疑人。</p>
        </div>
      </div>

      <div class="tag-row">
        <el-tag type="success">绿色：验证通过</el-tag>
        <el-tag type="danger">红色：验证拒绝</el-tag>
      </div>
    </section>
  </div>
</template>
