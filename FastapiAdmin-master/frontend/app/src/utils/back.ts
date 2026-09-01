/**
 * 安全返回（解决 H5 上"退不出去、反复刷新"问题）：
 *
 * 根因：H5 路由基于浏览器 history。页面被刷新（F5/重载）后 history 栈被清空，
 * 此时 uni.navigateBack() 内部执行 $router.go(-1) → history.back()，没有可退的历史，
 * 浏览器会刷新当前页面 → 再次加载同一页 → 再次返回又刷新 → 死循环（表现为"退不出去、重复刷新"）。
 *
 * 策略：
 * - uni 页面栈 > 1 层（有上一页）→ 正常 navigateBack
 * - uni 页面栈仅 1 层（刷新后/深链直接打开）→ reLaunch 回 fallback 首页，退出当前页
 */
export function safeBack(fallback = '/pages/index/index') {
  // 防御：@click="safeBack" 这类绑定会把事件对象当作第一个参数传进来，必须校验
  if (typeof fallback !== 'string' || !fallback.startsWith('/')) {
    fallback = '/pages/index/index'
  }
  const pages = getCurrentPages()
  if (pages.length > 1) {
    uni.navigateBack()
  }
  else {
    uni.reLaunch({ url: fallback })
  }
}
