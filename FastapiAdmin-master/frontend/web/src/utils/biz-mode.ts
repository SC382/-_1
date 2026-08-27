/**
 * 业务登录模式标记（胸痛中心 Web 端）。
 *
 * 独立的小文件，避免 user.store ↔ http 拦截器之间产生循环依赖。
 * 业务登录成功后置为 true；登出/会话失效置为 false。
 * 拦截器据此决定：业务模式下，非 /cpx/ 接口（如框架的公告/聊天）401 时
 * 不触发刷新与强制登出，仅静默拒绝，避免把登录中的业务用户踢回登录页。
 */

let bizMode = false;

export function setBizMode(value: boolean): void {
  bizMode = value;
}

export function isBizMode(): boolean {
  return bizMode;
}
