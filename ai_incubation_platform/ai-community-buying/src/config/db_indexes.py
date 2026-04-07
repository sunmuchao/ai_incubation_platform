"""
数据库索引优化脚本

在现有实体模型基础上添加索引，提升查询性能。
"""
from sqlalchemy import Index
from models.entities import (
    ProductEntity, GroupBuyEntity, GroupMemberEntity,
    OrderEntity, NotificationEntity, ProductRecommendationEntity
)


def create_indexes():
    """
    为所有表创建优化索引

    索引设计原则:
    1. 外键字段必须建立索引
    2. 频繁查询的过滤字段建立索引
    3. 频繁排序的字段建立索引
    4. 组合查询考虑复合索引
    """
    indexes = []

    # ========== ProductEntity 索引 ==========
    # status 字段常用于过滤
    indexes.append(Index(
        'idx_product_status',
        ProductEntity.status
    ))
    # 名称模糊查询索引（SQLite 不支持全文索引，仅标记）
    indexes.append(Index(
        'idx_product_name',
        ProductEntity.name
    ))
    # 复合索引：status + created_at 用于"按状态过滤后排序"
    indexes.append(Index(
        'idx_product_status_created',
        ProductEntity.status,
        ProductEntity.created_at.desc()
    ))

    # ========== GroupBuyEntity 索引 ==========
    # 外键索引
    indexes.append(Index(
        'idx_groupbuy_product_id',
        GroupBuyEntity.product_id
    ))
    # 状态过滤索引
    indexes.append(Index(
        'idx_groupbuy_status',
        GroupBuyEntity.status
    ))
    # 组织者查询索引
    indexes.append(Index(
        'idx_groupbuy_organizer',
        GroupBuyEntity.organizer_id
    ))
    # 复合索引：status + deadline 用于"查询活跃团购"
    indexes.append(Index(
        'idx_groupbuy_status_deadline',
        GroupBuyEntity.status,
        GroupBuyEntity.deadline
    ))
    # 复合索引：product_id + status 用于"查询某商品的团购"
    indexes.append(Index(
        'idx_groupbuy_product_status',
        GroupBuyEntity.product_id,
        GroupBuyEntity.status
    ))

    # ========== GroupMemberEntity 索引 ==========
    # 外键索引
    indexes.append(Index(
        'idx_groupmember_group_id',
        GroupMemberEntity.group_buy_id
    ))
    # 用户参团查询索引
    indexes.append(Index(
        'idx_groupmember_user_id',
        GroupMemberEntity.user_id
    ))
    # 复合索引：user_id + join_time 用于"用户参团历史"
    indexes.append(Index(
        'idx_groupmember_user_time',
        GroupMemberEntity.user_id,
        GroupMemberEntity.join_time.desc()
    ))
    # 复合索引：group_id + user_id 用于"检查用户是否已参团"（唯一约束）
    indexes.append(Index(
        'idx_groupmember_group_user',
        GroupMemberEntity.group_buy_id,
        GroupMemberEntity.user_id,
        unique=True
    ))

    # ========== OrderEntity 索引 ==========
    # 外键索引
    indexes.append(Index(
        'idx_order_group_buy_id',
        OrderEntity.group_buy_id
    ))
    indexes.append(Index(
        'idx_order_product_id',
        OrderEntity.product_id
    ))
    # 用户订单查询索引
    indexes.append(Index(
        'idx_order_user_id',
        OrderEntity.user_id
    ))
    # 复合索引：user_id + created_at 用于"用户订单历史"
    indexes.append(Index(
        'idx_order_user_time',
        OrderEntity.user_id,
        OrderEntity.created_at.desc()
    ))
    # 复合索引：group_buy_id + status 用于"查询团购订单"
    indexes.append(Index(
        'idx_order_group_status',
        OrderEntity.group_buy_id,
        OrderEntity.status
    ))

    # ========== NotificationEntity 索引 ==========
    # 用户通知查询索引
    indexes.append(Index(
        'idx_notification_user_id',
        NotificationEntity.user_id
    ))
    # 复合索引：user_id + is_read 用于"查询未读通知"
    indexes.append(Index(
        'idx_notification_user_read',
        NotificationEntity.user_id,
        NotificationEntity.is_read
    ))
    # 复合索引：user_id + created_at 用于"用户通知列表"
    indexes.append(Index(
        'idx_notification_user_time',
        NotificationEntity.user_id,
        NotificationEntity.created_at.desc()
    ))

    # ========== ProductRecommendationEntity 索引 ==========
    # 社区推荐查询索引
    indexes.append(Index(
        'idx_recommendation_community',
        ProductRecommendationEntity.community_id
    ))
    # 复合索引：community_id + score 用于"社区推荐排序"
    indexes.append(Index(
        'idx_recommendation_community_score',
        ProductRecommendationEntity.community_id,
        ProductRecommendationEntity.score.desc()
    ))

    return indexes


def apply_indexes(base, engine):
    """
    应用所有索引到数据库

    Args:
        base: SQLAlchemy Base 类
        engine: 数据库引擎
    """
    indexes = create_indexes()
    applied = []

    for index in indexes:
        try:
            # 检查索引是否已存在
            if not hasattr(index, 'name') or not index.name:
                continue

            # 创建索引（如果不存在）
            index.create(bind=engine, checkfirst=True)
            applied.append(index.name)
        except Exception as e:
            # SQLite 某些版本不支持并发创建索引，记录但继续
            print(f"创建索引 {index.name} 时出错：{e}")

    return applied


def get_index_recommendations():
    """
    获取索引优化建议

    Returns:
        建议列表
    """
    return [
        {
            "table": "products",
            "recommendation": "为 status 和 created_at 添加复合索引",
            "reason": "频繁按状态过滤并按时间排序",
            "priority": "high"
        },
        {
            "table": "group_buys",
            "recommendation": "为 product_id 和 status 添加复合索引",
            "reason": "频繁查询某商品的所有活跃团购",
            "priority": "high"
        },
        {
            "table": "group_members",
            "recommendation": "为 user_id 和 group_buy_id 添加唯一约束",
            "reason": "防止用户重复参团，加速去重检查",
            "priority": "critical"
        },
        {
            "table": "orders",
            "recommendation": "为 user_id 和 created_at 添加复合索引",
            "reason": "用户订单列表查询频繁",
            "priority": "high"
        },
        {
            "table": "notifications",
            "recommendation": "为 user_id 和 is_read 添加复合索引",
            "reason": "频繁查询用户未读通知",
            "priority": "medium"
        }
    ]
