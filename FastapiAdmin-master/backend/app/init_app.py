from collections.abc import AsyncGenerator
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import asynccontextmanager
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html, get_swagger_ui_oauth2_redirect_html
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .common.enums import EnvironmentEnum
from .config import path_conf
from .config.setting import settings
from .core.exceptions import handle_exception
from .core.logger import logger
from .core.signed_url import normalize_static_path, verify_static_signature
from .utils.common_util import import_module
from .utils.console import console_end, console_start


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[Any, Any]:
    from app.api.v1.module_system.dict.service import DictDataService
    from app.api.v1.module_system.params.service import ParamsService
    from app.core.ap_scheduler import SchedulerUtil
    from app.core.database import async_engine, redis_connect
    from app.scripts.initialize import InitializeData

    await InitializeData().init_db()
    logger.info("✅ {}数据库初始化完成", settings.DATABASE_TYPE)
    await redis_connect(app, status=True)
    logger.info("✅ Redis 连接初始化完成")
    await ParamsService.init_cache(redis=app.state.redis)
    logger.info("✅ Redis系统参数初始化完成")
    await DictDataService.init_cache(redis=app.state.redis)
    logger.info("✅ Redis数据字典初始化完成")
    await SchedulerUtil.init_scheduler(redis=app.state.redis)
    logger.info("✅ 定时任务调度器初始化完成")

    console_start(
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
        database_type=settings.DATABASE_TYPE,
        database_ready=True,
        redis_ready=True,
        scheduler_ready=SchedulerUtil.is_running(),
    )

    yield

    try:
        SchedulerUtil.shutdown(wait=True)
        logger.info("✅ 定时任务调度器已关闭")
        await redis_connect(app, status=False)
        logger.info("✅ Redis 连接已关闭")
        await async_engine.dispose()
        logger.info("✅ 数据库引擎连接池已释放")
        console_end()
    except Exception as e:
        logger.error("❌ 应用关闭过程中发生错误: {}", e)
        raise SystemExit(1)


def register_middlewares(app: FastAPI) -> None:
    for middleware in settings.MIDDLEWARE_LIST[::-1]:
        if not middleware:
            continue
        middleware = import_module(middleware, desc="中间件")
        app.add_middleware(middleware)


def register_exceptions(app: FastAPI) -> None:
    handle_exception(app)


def register_routers(app: FastAPI) -> None:
    from app.api.v1.module_ai import ai_router
    from app.api.v1.module_common import common_router
    from app.api.v1.module_generator import generator_router
    from app.api.v1.module_monitor import monitor_router
    from app.api.v1.module_system import system_router
    from app.api.v1.module_task import task_router
    from app.api.v1.module_storage import storage_router

    app.include_router(common_router)
    app.include_router(monitor_router)
    app.include_router(system_router)
    app.include_router(ai_router)
    app.include_router(generator_router)
    app.include_router(task_router)
    app.include_router(storage_router)

    from app.core.discover import dynamic_router
    dynamic_router.init_app(app)


def register_static(app: FastAPI) -> None:
    """注册静态文件路由（签名鉴权版）。

    安全加固：/static 目录下存放患者照片、心电图、病历 PDF 等隐私文件，
    不再使用无鉴权的 StaticFiles 挂载（任何人拿到 URL 即可下载），
    改为校验 URL 签名（exp + sign），校验通过才返回文件，否则 403。
    """
    path_conf.STATIC_DIR.mkdir(parents=True, exist_ok=True)

    @app.get(f"{settings.STATIC_URL}/{{file_path:path}}", include_in_schema=False)
    async def signed_static_file(file_path: str, exp: int = 0, sign: str = ""):
        rel_path = normalize_static_path(file_path)
        if not verify_static_signature(rel_path, exp, sign):
            logger.warning("静态资源签名校验失败（无权限或链接已过期）: {}", rel_path)
            raise HTTPException(status_code=403, detail="无访问权限或链接已过期")
        # 目录穿越防护：解析后的真实路径必须仍在 STATIC_DIR 之内
        try:
            target = (path_conf.STATIC_DIR / rel_path).resolve()
        except Exception:
            raise HTTPException(status_code=404, detail="文件不存在")
        if not str(target).startswith(str(path_conf.STATIC_DIR.resolve())) or not target.is_file():
            raise HTTPException(status_code=404, detail="文件不存在")
        return FileResponse(target)


def register_docs(app: FastAPI) -> None:
    """注册文档路由（生产环境关闭，避免暴露全部 API 结构）。"""
    if settings.ENVIRONMENT == EnvironmentEnum.PROD:
        return

    swagger_ui_redirect_url = str(app.swagger_ui_oauth2_redirect_url)
    root_openapi_url = str(app.root_path) + str(app.openapi_url)

    @app.get(swagger_ui_redirect_url, include_in_schema=False)
    async def swagger_ui_redirect():
        return get_swagger_ui_oauth2_redirect_html()

    @app.get(settings.DOCS_URL, include_in_schema=False)
    async def custom_swagger_ui_html() -> HTMLResponse:
        return get_swagger_ui_html(
            openapi_url=root_openapi_url,
            title=app.title + " - Swagger UI",
            oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
            swagger_js_url=settings.SWAGGER_JS_URL,
            swagger_css_url=settings.SWAGGER_CSS_URL,
            swagger_favicon_url=settings.FAVICON_URL,
        )

    @app.get(settings.REDOC_URL, include_in_schema=False)
    async def custom_redoc_html():
        return get_redoc_html(
            openapi_url=root_openapi_url,
            title=app.title + " - ReDoc",
            redoc_js_url=settings.REDOC_JS_URL,
            redoc_favicon_url=settings.FAVICON_URL,
        )


def register_frontend(app: FastAPI) -> None:
    if path_conf.FRONTEND_DIST_DIR.exists():
        app.mount("/web", StaticFiles(directory=str(path_conf.FRONTEND_DIST_DIR), html=True), name="frontend")
