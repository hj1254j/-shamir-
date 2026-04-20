import axios from "axios";

console.log("HTTP 模块初始化：准备创建 Axios 客户端。");

const http = axios.create({
  baseURL: "/api",
  timeout: 15000
});

http.interceptors.request.use(
  (config) => {
    console.log("接口请求即将发出：", {
      method: config.method,
      url: config.url,
      data: config.data,
      params: config.params
    });
    return config;
  },
  (error) => {
    console.log("接口请求在发送前失败：", error);
    return Promise.reject(error);
  }
);

http.interceptors.response.use(
  (response) => {
    console.log("接口响应已收到：", {
      url: response.config.url,
      status: response.status,
      data: response.data
    });
    return response;
  },
  (error) => {
    console.log("接口响应失败：", {
      url: error.config?.url,
      status: error.response?.status,
      detail: error.response?.data,
      message: error.message
    });
    return Promise.reject(error);
  }
);

export function getErrorMessage(error) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string" && detail.trim() !== "") {
    return detail;
  }

  if (typeof error?.message === "string" && error.message.trim() !== "") {
    return error.message;
  }

  return "请求失败，请稍后重试。";
}

export default http;
