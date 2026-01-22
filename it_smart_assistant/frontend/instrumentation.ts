
import { registerOTel } from "@vercel/otel";

export function register() {
  registerOTel({
    serviceName: "it_smart_assistant-frontend",
  });
}
