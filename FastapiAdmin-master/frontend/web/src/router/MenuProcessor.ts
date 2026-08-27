import type { UserInfo } from "@/api/module_system/user";
import type { MenuTable } from "@/api/module_system/menu";
import type { AppRouteRecord, RouteMeta } from "@/types/router";
import { useUserStore } from "@stores";
import { useAppMode } from "@/hooks/core/useAppMode";

import {
  ROUTE_COMPONENT_LAYOUT,
  ROUTE_COMPONENT_NESTED_PARENT,
} from "./routes";
import { MenuTypeEnum } from "@/enums/system/menu.enum";

/**
 * 菜单 → `AppRouteRecord`：后端 `MenuTable`、前端内置路由、混合模式合并；供守卫注册动态路由。
 * `getMenuList` 依 `useAppMode` 分支；meta 对齐后端 keep_alive、目录占位组件。
 */

/**
 * 胸痛中心业务菜单（前端静态路由，按角色 meta.roles 过滤）。
 * - admin：管理员（首页数据驾驶舱/医院/人员/模板/病例/日志）
 * - auditor：审核员（工作台/待审核/审核/记录）
 * 业务登录用户在守卫中跳过框架 getUserInfo，故后端菜单为空，仅加载本套菜单。
 */
export const builtinFrontendRoutes: AppRouteRecord[] = [
  // ── 首页（智能驾驶舱，顶级菜单，登录后落地）──
  // 说明：顶级容器 path 用 /cpx-dashboard（避开与 /cpx 路由第一段冲突），
  //       真实页面挂在隐藏子路由 /cpx/dashboard 下；activePath 用于侧边栏高亮。
  {
    path: "/cpx-dashboard",
    name: "CpxDashboard",
    component: ROUTE_COMPONENT_LAYOUT,
    meta: { title: "首页", icon: "ri:dashboard-3-line", roles: ["admin"], affix: true, fixedTab: true },
    children: [
      {
        path: "/cpx/dashboard",
        name: "CpxDashboardHome",
        component: "/cpx/dashboard/index",
        meta: {
          title: "首页",
          icon: "ri:dashboard-3-line",
          roles: ["admin"],
          hidden: true,
          isHide: true,
          activePath: "/cpx-dashboard",
        },
      },
    ],
  },
  // ── 医院管理（顶级菜单：医院卡片总览 + 医院人员管理）──
  {
    path: "/cpx-hospital",
    name: "CpxHospitalTop",
    component: ROUTE_COMPONENT_LAYOUT,
    meta: { title: "医院管理", icon: "ri:hospital-line", roles: ["admin"] },
    children: [
      {
        path: "/cpx/hospital",
        name: "CpxHospital",
        component: "/cpx/hospital/index",
        meta: { title: "医院管理", icon: "ri:hospital-line", roles: ["admin"], hidden: true, isHide: true, activePath: "/cpx-hospital" },
      },
    ],
  },
  // ── 模板管理（顶级菜单）──
  {
    path: "/cpx-template",
    name: "CpxTemplateTop",
    component: ROUTE_COMPONENT_LAYOUT,
    meta: { title: "模板管理", icon: "ri:file-list-3-line", roles: ["admin"] },
    children: [
      {
        path: "/cpx/template",
        name: "CpxTemplate",
        component: "/cpx/template/index",
        meta: { title: "模板管理", icon: "ri:file-list-3-line", roles: ["admin"], hidden: true, isHide: true, activePath: "/cpx-template" },
      },
    ],
  },
  // ── 病例管理（顶级菜单）──
  {
    path: "/cpx-case",
    name: "CpxCaseTop",
    component: ROUTE_COMPONENT_LAYOUT,
    meta: { title: "病例管理", icon: "ri:clipboard-line", roles: ["admin"] },
    children: [
      {
        path: "/cpx/case",
        name: "CpxCase",
        component: "/cpx/case/index",
        meta: { title: "病例管理", icon: "ri:clipboard-line", roles: ["admin"], hidden: true, isHide: true, activePath: "/cpx-case" },
      },
    ],
  },
  // ── 胸痛学院（顶级菜单）──
  {
    path: "/cpx-academy",
    name: "CpxAcademyTop",
    component: ROUTE_COMPONENT_LAYOUT,
    meta: { title: "胸痛学院", icon: "ri:graduation-cap-line", roles: ["admin"] },
    children: [
      {
        path: "/cpx/academy",
        name: "CpxAcademy",
        component: "/cpx/academy/index",
        meta: { title: "胸痛学院", icon: "ri:graduation-cap-line", roles: ["admin"], hidden: true, isHide: true, activePath: "/cpx-academy" },
      },
    ],
  },
  // ── 公告管理（顶级菜单）──
  {
    path: "/cpx-announcement",
    name: "CpxAnnouncementTop",
    component: ROUTE_COMPONENT_LAYOUT,
    meta: { title: "公告管理", icon: "ri:megaphone-line", roles: ["admin"] },
    children: [
      {
        path: "/cpx/announcement",
        name: "CpxAnnouncement",
        component: "/cpx/announcement/index",
        meta: { title: "公告管理", icon: "ri:megaphone-line", roles: ["admin"], hidden: true, isHide: true, activePath: "/cpx-announcement" },
      },
    ],
  },
  // ── 增值服务（顶级菜单）──
  {
    path: "/cpx-value-added",
    name: "CpxValueAddedTop",
    component: ROUTE_COMPONENT_LAYOUT,
    meta: { title: "增值服务", icon: "ri:gift-line", roles: ["admin"] },
    children: [
      {
        path: "/cpx/value-added",
        name: "CpxValueAdded",
        component: "/cpx/value_added/index",
        meta: { title: "增值服务", icon: "ri:gift-line", roles: ["admin"], hidden: true, isHide: true, activePath: "/cpx-value-added" },
      },
    ],
  },
  // ── 系统日志（顶级菜单）──
  {
    path: "/cpx-log",
    name: "CpxLogTop",
    component: ROUTE_COMPONENT_LAYOUT,
    meta: { title: "系统日志", icon: "ri:file-user-line", roles: ["admin"] },
    children: [
      {
        path: "/cpx/log",
        name: "CpxLog",
        component: "/cpx/log/index",
        meta: { title: "系统日志", icon: "ri:file-user-line", roles: ["admin"], hidden: true, isHide: true, activePath: "/cpx-log" },
      },
    ],
  },
  // ── 审核员菜单 ──
  {
    path: "/cpx/audit",
    name: "CpxAudit",
    component: ROUTE_COMPONENT_LAYOUT,
    meta: { title: "病例审核", icon: "ri:file-check-line", roles: ["auditor"] },
    children: [
      {
        path: "/cpx/audit/workbench",
        name: "CpxAuditWorkbench",
        component: "/cpx/audit/workbench",
        meta: { title: "审核工作台", icon: "ri:dashboard-line", roles: ["auditor"] },
      },
      {
        path: "/cpx/audit/pending",
        name: "CpxAuditPending",
        component: "/cpx/audit/pending",
        meta: { title: "待审核病例", icon: "ri:inbox-line", roles: ["auditor"] },
      },
      {
        path: "/cpx/audit/audit",
        name: "CpxAuditDetail",
        component: "/cpx/audit/audit",
        meta: { title: "病例审核", icon: "ri:file-search-line", roles: ["auditor"], hidden: true, isHide: true },
      },
      {
        path: "/cpx/audit/history",
        name: "CpxAuditHistory",
        component: "/cpx/audit/history",
        meta: { title: "审核记录", icon: "ri:history-line", roles: ["auditor"] },
      },
    ],
  },
];

function joinAbsolutePath(parentAbs: string, segmentPath: string): string {
  const seg = segmentPath.replace(/^\/+/, "");
  const base = parentAbs.replace(/\/$/, "");
  if (!seg) return base;
  return `${base}/${seg}`;
}

function toComponentImportPath(componentPath: string): string {
  const t = componentPath.trim().replace(/^\/+/, "");
  return t ? `/${t}` : "";
}

function mapMenuNode(item: MenuTable, depth = 0, parentAbsolutePath = ""): AppRouteRecord {
  const raw = (item.route_path ?? "").trim();
  // 直接在此计算标准化路径，消除 normalizeMenuNestedPaths + normalizeAppRouteChildPaths 两次遍历
  const path = raw.startsWith("/")
    ? raw
    : parentAbsolutePath
      ? joinAbsolutePath(parentAbsolutePath, raw)
      : `/${raw}`;

  const childrenRaw = item.children?.filter((c) => c.type !== MenuTypeEnum.BUTTON) ?? [];
  const children = childrenRaw.length
    ? childrenRaw.map((c) => mapMenuNode(c, depth + 1, path))
    : undefined;

  const name = item.route_name || undefined;
  const redirect = item.redirect?.trim() || undefined;

  const hasKids = !!(children && children.length > 0);
  const isDirectory = item.type === MenuTypeEnum.CATALOG;

  let component: string | undefined;
  if (isDirectory || (hasKids && !(item.component_path ?? "").trim())) {
    component = depth === 0 ? ROUTE_COMPONENT_LAYOUT : ROUTE_COMPONENT_NESTED_PARENT;
  } else if ((item.component_path ?? "").trim()) {
    component = toComponentImportPath(item.component_path!);
  }

  const meta: RouteMeta = {
    title: item.title ?? "",
    icon: item.icon || undefined,
    hidden: !!item.hidden,
    keepAlive: item.keep_alive ?? true,
    affix: !!item.affix,
    fixedTab: !!item.affix,
    alwaysShow: !!item.always_show,
    isHide: !!item.hidden,
    isHideTab: !!item.is_hide_tab,
    link: item.link || undefined,
    isIframe: !!item.is_iframe,
    activePath: item.active_path || undefined,
    showBadge: !!item.show_badge,
    showTextBadge: item.show_text_badge || undefined,
    scope: item.scope,
  };

  return {
    path,
    name,
    component,
    redirect,
    meta,
    children,
  };
}

function backendMenusToAppRoutes(menus: MenuTable[]): AppRouteRecord[] {
  const roots = menus.filter((m) => m.type !== MenuTypeEnum.BUTTON);
  return roots.map((m) => mapMenuNode(m, 0, ""));
}

export class MenuProcessor {
  async getMenuList(): Promise<AppRouteRecord[]> {
    const { isFrontendMode, isMixedMenuMode } = useAppMode();

    let menuList: AppRouteRecord[];
    if (isMixedMenuMode.value) {
      menuList = await this.processMixedMenu();
    } else if (isFrontendMode.value) {
      menuList = await this.processFrontendMenu();
    } else {
      menuList = await this.processBackendMenu();
    }

    // 统一过滤空菜单，避免各分支重复调用
    menuList = this.filterEmptyMenus(menuList);

    return this.normalizeMenuPaths(menuList);
  }

  private async processFrontendMenu(): Promise<AppRouteRecord[]> {
    const userStore = useUserStore();
    let menuList = [...builtinFrontendRoutes];

    if (!userStore.info?.is_superuser) {
      const roles = userStore.info?.roles;

      if (roles && roles.length > 0) {
        const roleCodes = this.extractRoleCodesFromUserRoles(roles);
        if (roleCodes.length > 0) {
          menuList = this.filterMenuByRoles(menuList, roleCodes);
        }
      }
    }

    return menuList;
  }

  private extractRoleCodesFromUserRoles(roles: NonNullable<UserInfo["roles"]>): string[] {
    const codes = new Set<string>();
    for (const role of roles) {
      const r = role as { code?: string; name?: string };
      const c = r.code?.trim();
      if (c) codes.add(c);
      const n = r.name?.trim();
      if (n && /^R_[A-Z0-9_]+$/i.test(n)) codes.add(n);
    }
    return Array.from(codes);
  }

  private async processMixedMenu(): Promise<AppRouteRecord[]> {
    let backend: AppRouteRecord[] = [];
    try {
      backend = await this.processBackendMenu();
    } catch (e) {
      console.warn("[MenuProcessor] mixed：后端菜单获取失败，本次仅挂载前端路由", e);
    }
    const frontend = await this.processFrontendMenu();
    const merged = mergeAppRouteRecords(backend, frontend);
    return merged;
  }

  /** 优先用用户信息里附带的 `menus`，与守卫拉用户信息顺序一致，避免重复打菜单树接口 */
  private async processBackendMenu(): Promise<AppRouteRecord[]> {
    const userStore = useUserStore();
    const fromUser = userStore.routeList;
    if (Array.isArray(fromUser) && fromUser.length > 0) {
      return backendMenusToAppRoutes(fromUser);
    }
    return [];
  }

  private filterMenuByRoles(menu: AppRouteRecord[], roleCodes: string[]): AppRouteRecord[] {
    return menu.reduce((acc: AppRouteRecord[], item) => {
      const itemRoles = item.meta?.roles;
      const hasPermission = !itemRoles || itemRoles.some((role) => roleCodes?.includes(role));

      if (hasPermission) {
        const filteredItem = { ...item };
        if (filteredItem.children?.length) {
          filteredItem.children = this.filterMenuByRoles(filteredItem.children, roleCodes);
        }
        acc.push(filteredItem);
      }

      return acc;
    }, []);
  }

  private filterEmptyMenus(menuList: AppRouteRecord[]): AppRouteRecord[] {
    return menuList
      .map((item) => {
        if (!item.children?.length) return item;
        return { ...item, children: this.filterEmptyMenus(item.children) };
      })
      .filter((item) => this.isMenuNodeVisible(item));
  }

  /** 菜单节点在侧栏中是否可见（有子菜单 / iframe / 外链 / 有实际组件） */
  private isMenuNodeVisible(item: AppRouteRecord): boolean {
    if (item.children?.length) return true;
    if (item.meta?.isIframe || item.meta?.link) return true;
    return !!(item.component && item.component !== "" && item.component !== ROUTE_COMPONENT_LAYOUT);
  }

  validateMenuList(menuList: AppRouteRecord[]): boolean {
    return Array.isArray(menuList) && menuList.length > 0;
  }

  private normalizeMenuPaths(menuList: AppRouteRecord[], parentPath = ""): AppRouteRecord[] {
    return menuList.map((item) => {
      const fullPath = this.buildFullPath(item.path || "", parentPath);

      const children = item.children?.length
        ? this.normalizeMenuPaths(item.children, fullPath)
        : item.children;

      const redirect = item.redirect || this.resolveDefaultRedirect(children);

      return {
        ...item,
        path: fullPath,
        redirect,
        children,
      };
    });
  }

  private resolveDefaultRedirect(children?: AppRouteRecord[]): string | undefined {
    if (!children?.length) {
      return undefined;
    }

    for (const child of children) {
      if (this.isNavigableRoute(child)) {
        return child.path;
      }

      const nestedRedirect = this.resolveDefaultRedirect(child.children);
      if (nestedRedirect) {
        return nestedRedirect;
      }
    }

    return undefined;
  }

  private isNavigableRoute(route: AppRouteRecord): boolean {
    return Boolean(
      route.path &&
      route.path !== "/" &&
      !route.meta?.link &&
      route.meta?.isIframe !== true &&
      route.component &&
      route.component !== ""
    );
  }

  private buildFullPath(path: string, parentPath: string): string {
    if (!path) return "";

    if (path.startsWith("http://") || path.startsWith("https://")) {
      return path;
    }

    if (path.startsWith("/")) {
      return path;
    }

    if (parentPath) {
      const cleanParent = parentPath.replace(/\/$/, "");
      const cleanChild = path.replace(/^\//, "");
      return `${cleanParent}/${cleanChild}`;
    }

    return `/${path}`;
  }
}

// ──────── 壳层路由补全 ────────

/**
 * 将壳层路由（/home、/dashboard）合并到菜单列表。
 *
 * 已停用：业务侧边栏不再展示「首页」「仪表盘」菜单项，
 * 菜单完全由后端菜单 / builtinFrontendRoutes 决定。
 */
export function mergeShellRoutesIntoMenu(menuList: AppRouteRecord[]): AppRouteRecord[] {
  return menuList;
}

/** 按 name 去重合并两套菜单记录 */
export function mergeAppRouteRecords(
  primary: AppRouteRecord[],
  secondary: AppRouteRecord[]
): AppRouteRecord[] {
  const usedNames = new Set<string>();

  const collectNames = (routes: AppRouteRecord[]) => {
    for (const r of routes) {
      if (r.name) usedNames.add(String(r.name));
      if (r.children?.length) collectNames(r.children);
    }
  };
  collectNames(primary);

  const pickFresh = (routes: AppRouteRecord[]): AppRouteRecord[] => {
    const out: AppRouteRecord[] = [];
    for (const r of routes) {
      const n = r.name ? String(r.name) : "";
      if (n && usedNames.has(n)) continue;
      const next: AppRouteRecord = { ...r };
      if (r.children?.length) next.children = pickFresh(r.children);
      if (n) usedNames.add(n);
      out.push(next);
    }
    return out;
  };

  return [...primary, ...pickFresh(secondary)];
}
