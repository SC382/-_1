export interface TabbarItem {
  name: string
  value?: number
  active: boolean
  titleKey: string
  icon: string
}

const tabbarItems = ref<TabbarItem[]>([
  { name: 'home', active: true, titleKey: 'common.tab.home', icon: '/static/tab/home_gray.svg' },
  { name: 'ai', active: false, titleKey: 'common.tab.ai', icon: '/static/tab/chat_gray.svg' },
  { name: 'mine', active: false, titleKey: 'common.tab.mine', icon: '/static/tab/user_gray.svg' },
])

const tabbarIconsActive = {
  home: '/static/tab/home_active.svg',
  ai: '/static/tab/chat_active.svg',
  mine: '/static/tab/user_active.svg',
}

export function useTabbar() {
  const tabbarList = computed(() =>
    tabbarItems.value.map(item => ({
      ...item,
      icon: item.active ? tabbarIconsActive[item.name as keyof typeof tabbarIconsActive] : item.icon,
    })),
  )

  const activeTabbar = computed(() => {
    const item = tabbarItems.value.find(item => item.active)
    return item || tabbarItems.value[0]
  })

  const getTabbarItemValue = (name: string) => {
    const item = tabbarItems.value.find(item => item.name === name)
    return item?.value
  }

  const setTabbarItem = (name: string, value: number) => {
    const tabbarItem = tabbarItems.value.find(item => item.name === name)
    if (tabbarItem) {
      tabbarItem.value = value
    }
  }

  const setTabbarItemActive = (name: string) => {
    tabbarItems.value.forEach((item) => {
      if (item.name === name) {
        item.active = true
      }
      else {
        item.active = false
      }
    })
  }

  return {
    tabbarList,
    activeTabbar,
    getTabbarItemValue,
    setTabbarItem,
    setTabbarItemActive,
  }
}
