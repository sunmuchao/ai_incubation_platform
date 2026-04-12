"""
路由注册中心

将所有路由注册逻辑集中管理，保持 main.py 简洁。
"""
from fastapi import FastAPI
from utils.logger import logger


def register_all_routers(app: FastAPI) -> None:
    """
    注册所有路由到 FastAPI 应用
    """
    logger.info("Starting router registration...")
    registered_count = 0

    # ========== 核心路由 ==========
    from api.users import router as users_router
    from api.matching import router as matching_router
    from api.relationship import router as relationship_router
    from api.activities import router as activities_router
    from api.profile import router as profile_router

    app.include_router(users_router)
    app.include_router(matching_router)
    app.include_router(relationship_router)
    app.include_router(activities_router)
    app.include_router(profile_router)
    registered_count += 5

    # ========== 扩展路由 ==========
    from api.photos import router as photos_router
    from api.identity_verification import router as identity_router
    from api.chat import router as chat_router
    from api.membership import router as membership_router
    from api.verification_badges import router as verification_router
    from api.ai_companion import router as companion_router
    from api.relationship_preferences import router as relationship_pref_router

    app.include_router(photos_router)
    app.include_router(identity_router)
    app.include_router(chat_router)
    app.include_router(membership_router)
    app.include_router(verification_router)
    app.include_router(companion_router)
    app.include_router(relationship_pref_router)
    registered_count += 7

    # ========== 通知分享路由 ==========
    from api.notification_share_apis import router_notifications, router_share
    app.include_router(router_notifications)
    app.include_router(router_share)
    registered_count += 2

    # ========== Milestone 路由 ==========
    from api.milestone_apis import router_milestones, router_date_suggestions, router_couple_games
    app.include_router(router_milestones)
    app.include_router(router_date_suggestions)
    app.include_router(router_couple_games)
    registered_count += 3

    # ========== LifeIntegration 路由 ==========
    from api.life_integration_apis import (
        router_date_plan, router_album, router_tribe, router_digital_home,
        router_family_sim, router_stress_test, router_growth, router_trust
    )
    app.include_router(router_date_plan)
    app.include_router(router_album)
    app.include_router(router_tribe)
    app.include_router(router_digital_home)
    app.include_router(router_family_sim)
    app.include_router(router_stress_test)
    app.include_router(router_growth)
    app.include_router(router_trust)
    registered_count += 8

    # ========== 微信登录路由 ==========
    from api.wechat_login import router as wechat_login_router
    app.include_router(wechat_login_router)
    registered_count += 1

    # ========== Rose 玫瑰表达路由 ==========
    from api.rose import router as rose_router
    app.include_router(rose_router)
    registered_count += 1

    # ========== Gift 虚拟礼物路由 ==========
    from api.gift import router as gift_router
    app.include_router(gift_router)
    registered_count += 1

    # ========== FaceVerification 人脸认证路由 ==========
    from api.face_verification import router as face_verification_router
    app.include_router(face_verification_router)
    registered_count += 1

    # ========== Your Turn 提醒路由 ==========
    from api.your_turn import router as your_turn_router
    app.include_router(your_turn_router)
    registered_count += 1

    # ========== Who Likes Me 路由 ==========
    from api.who_likes_me import router as who_likes_me_router
    app.include_router(who_likes_me_router)
    registered_count += 1

    # ========== Photo Comment 路由 ==========
    from api.photo_comment import router as photo_comment_router
    app.include_router(photo_comment_router)
    registered_count += 1

    # ========== Video Clip 路由 ==========
    from api.video_clip import router as video_clip_router
    app.include_router(video_clip_router)
    registered_count += 1

    # ========== Matching Preference 路由 ==========
    from api.matching_preference import router as matching_preference_router
    app.include_router(matching_preference_router)
    registered_count += 1

    # ========== Date Reminder 路由 ==========
    from api.date_reminder import router as date_reminder_router
    app.include_router(date_reminder_router)
    registered_count += 1

    # ========== Gift Integration 路由 ==========
    from api.gift_integration import router as gift_integration_router
    app.include_router(gift_integration_router)
    registered_count += 1

    # ========== v1.x 功能路由 ==========
    from api.payment import router as payment_router
    from api.video_date import router as video_date_router
    from api.performance import router as performance_router
    app.include_router(payment_router)
    app.include_router(video_date_router)
    app.include_router(performance_router)
    registered_count += 3

    # ========== AI Native 路由 ==========
    from api.ai_awareness import router as ai_awareness_router
    from api.skills import router as skills_router
    from api.agent_intervention import router as agent_intervention_router
    from api.llm_cache import router as llm_cache_router
    from api.digital_twin import router as digital_twin_router
    from api.scene_detection import router as scene_detection_router
    from api.checker import router as checker_router
    from api.grayscale_apis import router as grayscale_router
    from api.autonomous_apis import router as autonomous_router
    from api.deerflow import router as deerflow_router
    app.include_router(ai_awareness_router)
    app.include_router(skills_router)
    app.include_router(agent_intervention_router)
    app.include_router(llm_cache_router)
    app.include_router(digital_twin_router)
    app.include_router(scene_detection_router)
    app.include_router(checker_router)
    app.include_router(grayscale_router)
    app.include_router(autonomous_router)
    app.include_router(deerflow_router)
    registered_count += 10

    logger.info(f"All routers registered successfully. Total: {registered_count}")

    # ========== 已删除路由说明 ==========
    # 以下功能已迁移至 Skill 层，不再暴露 HTTP 路由：
    # - behavior, recommendation, safety: 改用 Skill 调用
    # - emotion_analysis, behavior_lab, conflict_handling: 改用 Skill 调用
    # - values_evolution, perception_layer: 改用 Skill 调用
    # - love_language_profile, date_simulation: 改用 Skill 调用
    # - conversation_matching, registration_conversation: 改用 Skill 调用
    # - deep_icebreaker, joint_activity: 改用 Skill 调用
    # - message_interpretation, stress_test: 改用 Skill 调用
    #
    # 已合并路由：
    # - conversations → chat.py
    # - video → video_date.py
    # - api_checker + skills_checker → checker.py


def get_api_endpoints_summary() -> dict:
    """获取 API 端点摘要"""
    return {
        "core": "/api/users, /api/matching, /api/relationship",
        "social": "/api/chat, /api/photos, /api/activities",
        "membership": "/api/membership, /api/payment",
        "safety": "/api/identity, /api/verification",
        "ai_features": "/api/ai-companion, /api/skills",
        "milestone": "/api/milestones, /api/date-suggestions, /api/couple-games",
        "life_integration": "/api/date-plan, /api/album, /api/tribe, /api/digital-home",
        "ai_native": "/api/ai-awareness, /api/deerflow, /api/autonomous",
    }