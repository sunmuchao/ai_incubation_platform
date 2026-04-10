"""
路由注册中心

将所有路由注册逻辑集中管理，保持 main.py 简洁。

使用示例:
    from routers import register_all_routers
    register_all_routers(app)
"""
from fastapi import FastAPI
from utils.logger import logger


def register_all_routers(app: FastAPI) -> None:
    """
    注册所有路由到 FastAPI 应用

    Args:
        app: FastAPI 应用实例
    """
    logger.info("Starting router registration...")
    registered_count = 0

    # ========== 核心路由 (P0-P3) ==========
    from api.users import router as users_router
    from api.matching import router as matching_router
    from api.behavior import router as behavior_router
    from api.relationship import router as relationship_router
    from api.activities import router as activities_router
    from api.conversations import router as conversations_router
    from api.profile import router as profile_router

    app.include_router(users_router)
    registered_count += 1
    logger.debug(f"Registered router: users_router")
    app.include_router(matching_router)
    registered_count += 1
    logger.debug(f"Registered router: matching_router")
    app.include_router(behavior_router)
    registered_count += 1
    logger.debug(f"Registered router: behavior_router")
    app.include_router(relationship_router)
    registered_count += 1
    logger.debug(f"Registered router: relationship_router")
    app.include_router(activities_router)
    registered_count += 1
    logger.debug(f"Registered router: activities_router")
    app.include_router(conversations_router)
    registered_count += 1
    logger.debug(f"Registered router: conversations_router")
    app.include_router(profile_router)
    registered_count += 1
    logger.debug(f"Registered router: profile_router")

    # ========== P4-P6 路由 ==========
    from api.photos import router as photos_router
    from api.identity_verification import router as identity_router
    from api.chat import router as chat_router
    from api.membership import router as membership_router
    from api.video import router as video_router
    from api.verification_badges import router as verification_router
    from api.ai_companion import router as companion_router
    from api.relationship_preferences import router as relationship_pref_router
    from api.recommendation import router as recommendation_router
    from api.conversations_v2 import router as conversations_v2_router

    app.include_router(photos_router)
    app.include_router(identity_router)
    app.include_router(chat_router)
    app.include_router(membership_router)
    app.include_router(video_router)
    app.include_router(verification_router)
    app.include_router(companion_router)
    app.include_router(relationship_pref_router)
    app.include_router(recommendation_router)
    app.include_router(conversations_v2_router)
    registered_count += 10
    logger.debug(f"Registered P4-P6 routers: 10 routers")

    # ========== P7-P9 路由 ==========
    from api.safety import router as safety_router
    from api.p9_apis import router_notifications, router_share

    app.include_router(safety_router)
    app.include_router(router_notifications)
    app.include_router(router_share)
    registered_count += 3
    logger.debug(f"Registered P7-P9 routers: 3 routers")

    # ========== P10-P12 路由 ==========
    from api.p10_apis import router_milestones, router_date_suggestions, router_couple_games
    from api.p11_apis import router_emotion_analysis, router_safety, router_reports
    from api.p12_apis import (
        router_experiences,
        router_silence,
        router_icebreaker,
        router_emotion,
        router_love_language,
        router_weather
    )
    from api.conflict_handling import router as conflict_handling_router
    from api.values_evolution import router as values_evolution_router
    from api.perception_layer import router as perception_layer_router

    app.include_router(router_milestones)
    app.include_router(router_date_suggestions)
    app.include_router(router_couple_games)
    app.include_router(router_emotion_analysis)
    app.include_router(router_safety)
    app.include_router(router_reports)
    app.include_router(router_experiences)
    app.include_router(router_silence)
    app.include_router(router_icebreaker)
    app.include_router(router_emotion)
    app.include_router(router_love_language)
    app.include_router(router_weather)
    app.include_router(conflict_handling_router)
    app.include_router(values_evolution_router)
    app.include_router(perception_layer_router)
    registered_count += 15
    logger.debug(f"Registered P10-P12 routers: 15 routers")

    # ========== P13-P14 路由 ==========
    from api.p13_apis import (
        router_love_language_profile,
        router_relationship_trend,
        router_warning_response,
        router_p13_comprehensive
    )
    from api.p14_apis import (
        router_avatar,
        router_simulation,
        router_outfit,
        router_venue,
        router_topics
    )

    app.include_router(router_love_language_profile)
    app.include_router(router_relationship_trend)
    app.include_router(router_warning_response)
    app.include_router(router_p13_comprehensive)
    app.include_router(router_avatar)
    app.include_router(router_simulation)
    app.include_router(router_outfit)
    app.include_router(router_venue)
    app.include_router(router_topics)
    registered_count += 9
    logger.debug(f"Registered P13-P14 routers: 9 routers")

    # ========== P15-P17 路由 ==========
    from api.p15_p16_p17_apis import router_date_plan, router_album
    from api.p15_p16_p17_apis import router_tribe, router_digital_home, router_family_sim
    from api.p15_p16_p17_apis import router_stress_test, router_growth, router_trust

    app.include_router(router_date_plan)
    app.include_router(router_album)
    app.include_router(router_tribe)
    app.include_router(router_digital_home)
    app.include_router(router_family_sim)
    app.include_router(router_stress_test)
    app.include_router(router_growth)
    app.include_router(router_trust)
    registered_count += 8
    logger.debug(f"Registered P15-P17 routers: 8 routers")

    # ========== 悬浮球快速对话路由 ==========
    from api.quick_chat import router as quick_chat_router

    app.include_router(quick_chat_router)
    registered_count += 1
    logger.debug(f"Registered router: quick_chat_router")

    # ========== 微信登录路由 ==========
    from api.wechat_login import router as wechat_login_router

    app.include_router(wechat_login_router)
    registered_count += 1
    logger.debug(f"Registered router: wechat_login_router")

    # ========== P2: 礼物闭环集成路由 ==========
    from api.gift_integration import router as gift_integration_router

    app.include_router(gift_integration_router)
    registered_count += 1
    logger.debug(f"Registered router: gift_integration_router")

    # ========== v1.x 功能路由 ==========
    from api.payment import router as payment_router
    from api.video_date import router as video_date_router
    from api.performance import router as performance_router

    app.include_router(payment_router)
    app.include_router(video_date_router)
    app.include_router(performance_router)
    registered_count += 3
    logger.debug(f"Registered v1.x routers: 3 routers")

    # ========== AI Native 路由 ==========
    from api.conversation_matching import router as conversation_matching_router
    from api.ai_awareness import router as ai_awareness_router
    from api.registration_conversation import router as registration_conversation_router
    from api.skills import router as skills_router
    from api.credit import router as credit_router
    from api.agent_intervention import router as agent_intervention_router
    from api.llm_cache import router as llm_cache_router
    from api.identity_verification_p0 import router as identity_verification_p0_router
    from api.ai_learning import router as ai_learning_router
    from api.digital_twin import router as digital_twin_router  # P2 数字孪生
    from api.adaptive_ui import router as adaptive_ui_router
    from api.ai_interlocutor import router as ai_interlocutor_router  # AI 预沟通
    from services.scene_detection_service import router as scene_detection_router  # 场景检测
    from utils.api_checker import router as api_checker_router  # API 检查
    from utils.skills_checker import router as skills_checker_router  # Skills 检查

    app.include_router(conversation_matching_router)
    app.include_router(ai_awareness_router)
    app.include_router(registration_conversation_router)
    app.include_router(skills_router)
    app.include_router(credit_router)
    app.include_router(agent_intervention_router)
    app.include_router(llm_cache_router)
    app.include_router(identity_verification_p0_router)
    app.include_router(ai_learning_router)
    app.include_router(digital_twin_router)
    app.include_router(adaptive_ui_router)
    app.include_router(ai_interlocutor_router)
    app.include_router(scene_detection_router)
    app.include_router(api_checker_router)
    app.include_router(skills_checker_router)
    registered_count += 15
    logger.debug(f"Registered AI Native routers: 15 routers")

    logger.info(f"All routers registered successfully. Total routers: {registered_count}")


def get_api_endpoints_summary() -> dict:
    """
    获取 API 端点摘要

    Returns:
        端点摘要字典
    """
    return {
        "core": "/api/users, /api/matching, /api/behavior, /api/relationship",
        "social": "/api/chat, /api/photos, /api/activities, /api/conversations",
        "membership": "/api/membership, /api/payment",
        "safety": "/api/safety, /api/identity, /api/verification",
        "ai_features": "/api/ai-companion, /api/recommendation, /api/conversation-matching",
        "enterprise": "/api/dashboard, /api/performance, /api/departments",
        "advanced": "/api/p10-22/* (P10-P22 高级功能)",
    }
