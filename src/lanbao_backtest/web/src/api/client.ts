import axios, { AxiosError } from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      const data = error.response.data as any;
      // FastAPI HTTPException 返回 { detail: string }
      // 其他错误可能返回 { error: { message: string } }
      const message = data?.detail || data?.error?.message || `请求失败: ${error.response.status}`;
      return Promise.reject(new Error(message));
    }
    if (error.request) {
      return Promise.reject(new Error('网络错误，请检查后端服务是否运行'));
    }
    return Promise.reject(error);
  }
);
