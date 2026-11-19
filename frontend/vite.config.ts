import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const target = env.FLASHBID_API_PROXY_TARGET;
  return {
    plugins: [react()],
    server: target ? {
      proxy: {
        "^/api(?:/|$)": {
          target,
          changeOrigin: true,
          ws: true,
          rewrite: (path) => path.replace(/^\/api(?=\/|$)/, ""),
          configure: (proxy) => {
            proxy.on("proxyReq", (proxyReq) => proxyReq.removeHeader("origin"));
          },
        },
      },
    } : undefined,
  };
});
