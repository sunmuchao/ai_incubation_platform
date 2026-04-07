"""
国际化 API 端点
提供多语言翻译、时区适配等接口
"""

from fastapi import APIRouter, HTTPException, Query, Header
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime
import pytz

from services.i18n_service import get_i18n_service

router = APIRouter(prefix="/api/i18n", tags=["Internationalization"])

i18n_service = get_i18n_service()


class TranslationRequest(BaseModel):
    """翻译请求"""
    key: str
    lang: Optional[str] = None
    args: Optional[List[str]] = []


class TranslationResponse(BaseModel):
    """翻译响应"""
    key: str
    translation: str
    lang: str


class LanguageInfo(BaseModel):
    """语言信息"""
    code: str
    name: str
    direction: str  # 'ltr' or 'rtl'


class TimezoneRequest(BaseModel):
    """时区请求"""
    datetime: str
    from_timezone: str
    to_timezone: str


class TimezoneResponse(BaseModel):
    """时区响应"""
    original: str
    converted: str
    from_timezone: str
    to_timezone: str


@router.get("/languages", response_model=List[LanguageInfo])
async def get_supported_languages():
    """获取支持的语言列表"""
    languages = []
    for code, name in i18n_service.get_supported_languages().items():
        languages.append(LanguageInfo(
            code=code,
            name=name,
            direction=i18n_service.get_language_direction(code)
        ))
    return languages


@router.post("/translate", response_model=TranslationResponse)
async def translate(request: TranslationRequest):
    """翻译文本"""
    translation = i18n_service.t(
        request.key,
        request.lang,
        *request.args if request.args else []
    )
    return TranslationResponse(
        key=request.key,
        translation=translation,
        lang=request.lang or i18n_service.DEFAULT_LANGUAGE
    )


@router.get("/translate/{key}")
async def translate_key(
    key: str,
    lang: Optional[str] = Query(None),
    args: Optional[str] = Query(None)
):
    """通过 URL 获取翻译"""
    args_list = args.split(',') if args else []
    translation = i18n_service.t(key, lang, *args_list)
    return {"key": key, "translation": translation, "lang": lang or i18n_service.DEFAULT_LANGUAGE}


@router.get("/rtl/{lang}")
async def is_rtl_language(lang: str):
    """判断语言是否为 RTL"""
    return {"lang": lang, "is_rtl": i18n_service.is_rtl(lang)}


@router.post("/timezone/convert")
async def convert_timezone(request: TimezoneRequest):
    """转换时区"""
    try:
        dt = datetime.fromisoformat(request.datetime)
        if dt.tzinfo is None:
            dt = pytz.timezone(request.from_timezone).localize(dt)

        converted = dt.astimezone(pytz.timezone(request.to_timezone))

        return TimezoneResponse(
            original=request.datetime,
            converted=converted.isoformat(),
            from_timezone=request.from_timezone,
            to_timezone=request.to_timezone
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/timezone/list")
async def list_timezones():
    """获取所有可用时区"""
    return {"timezones": pytz.all_timezones[:50]}  # 返回前 50 个常用时区


@router.get("/datetime/format")
async def format_datetime(
    datetime_str: str,
    lang: Optional[str] = Query(None),
    timezone: Optional[str] = Query(None)
):
    """格式化日期时间"""
    try:
        dt = datetime.fromisoformat(datetime_str)
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)

        formatted = i18n_service.format_datetime(dt, lang, timezone)
        return {"datetime": datetime_str, "formatted": formatted}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/datetime/relative")
async def format_relative_time(
    datetime_str: str,
    lang: Optional[str] = Query(None),
    timezone: Optional[str] = Query(None)
):
    """格式化相对时间"""
    try:
        dt = datetime.fromisoformat(datetime_str)
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)

        relative = i18n_service.format_relative_time(dt, lang, timezone)
        return {"datetime": datetime_str, "relative": relative}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/locale/{lang}")
async def get_locale(lang: str):
    """获取完整语言包"""
    if lang not in i18n_service._translations:
        raise HTTPException(status_code=404, detail=f"Language {lang} not found")

    return {
        "lang": lang,
        "name": i18n_service.get_language_name(lang),
        "direction": i18n_service.get_language_direction(lang),
        "translations": i18n_service._translations[lang]
    }
