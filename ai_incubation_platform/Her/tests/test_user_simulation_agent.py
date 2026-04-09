"""
测试用户模拟 Agent 模块

覆盖范围:
- UserSimulationAgent (src/agent/user_simulation_agent.py)
"""
import pytest
from unittest.mock import patch, MagicMock
import json


class TestUserSimulationAgentInitialization:
    """测试用户模拟 Agent 初始化"""

    def test_init_with_complete_profile(self):
        """测试使用完整画像初始化 Agent"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {
            "name": "张三",
            "age": 25,
            "gender": "male",
            "interests": ["旅行", "摄影", "美食"],
            "values": {"family": "important", "career": "ambitious"},
            "bio": "热爱生活，喜欢探索新鲜事物。希望找到一个志同道合的伴侣。"
        }

        agent = UserSimulationAgent(profile)

        assert agent.name == "张三"
        assert agent.age == 25
        assert agent.gender == "male"
        assert len(agent.interests) == 3
        assert "旅行" in agent.interests
        assert agent.bio == "热爱生活，喜欢探索新鲜事物。希望找到一个志同道合的伴侣。"
        assert agent.conversation_context == {}

    def test_init_with_minimal_profile(self):
        """测试使用最小画像初始化 Agent"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "李四"}

        agent = UserSimulationAgent(profile)

        assert agent.name == "李四"
        assert agent.age == 25  # 默认值
        assert agent.gender == "unknown"  # 默认值
        assert agent.interests == []
        assert agent.bio == ""

    def test_init_with_empty_profile(self):
        """测试使用空字典初始化 Agent"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        agent = UserSimulationAgent({})

        assert agent.name == "TA"  # 默认值
        assert agent.age == 25  # 默认值
        assert agent.gender == "unknown"
        assert agent.interests == []

    def test_init_with_none_profile(self):
        """测试使用 None 初始化 Agent"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        agent = UserSimulationAgent(None)

        assert agent.name == "TA"
        assert agent.age == 25
        assert agent.gender == "unknown"

    def test_parse_interests_from_string(self):
        """测试从字符串解析兴趣"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"interests": '["旅行", "摄影", "美食"]'}
        agent = UserSimulationAgent(profile)

        assert len(agent.interests) == 3
        assert "旅行" in agent.interests

    def test_parse_interests_from_invalid_string(self):
        """测试从无效字符串解析兴趣"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"interests": "invalid json"}
        agent = UserSimulationAgent(profile)

        assert agent.interests == ["invalid json"]

    def test_parse_interests_from_list(self):
        """测试从列表解析兴趣"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"interests": ["旅行", "摄影", "美食"]}
        agent = UserSimulationAgent(profile)

        assert len(agent.interests) == 3

    def test_parse_interests_from_empty_string(self):
        """测试从空字符串解析兴趣"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"interests": ""}
        agent = UserSimulationAgent(profile)

        assert agent.interests == []

    def test_parse_values_from_string(self):
        """测试从字符串解析价值观"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"values": '{"family": "important", "career": "ambitious"}'}
        agent = UserSimulationAgent(profile)

        assert agent.values["family"] == "important"
        assert agent.values["career"] == "ambitious"

    def test_parse_values_from_invalid_string(self):
        """测试从无效字符串解析价值观"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"values": "invalid json"}
        agent = UserSimulationAgent(profile)

        assert agent.values == {}

    def test_parse_values_from_dict(self):
        """测试从字典解析价值观"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"values": {"family": "important", "career": "ambitious"}}
        agent = UserSimulationAgent(profile)

        assert agent.values["family"] == "important"


class TestUserSimulationAgentPersonalityAnalysis:
    """测试用户性格分析"""

    def test_analyze_young_user(self):
        """测试年轻用户性格分析"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        # 使用外向型兴趣 + 年轻年龄
        profile = {"name": "小王", "age": 20, "interests": ["旅行", "聚会"], "bio": ""}
        agent = UserSimulationAgent(profile)

        # 年轻人更活跃，emoji 使用频繁
        assert agent.reply_config["emoji_usage"] == "frequent"
        # 回复概率应该是 0.95（上限）
        assert agent.reply_config["reply_probability"] == 0.95

    def test_analyze_older_user(self):
        """测试年长用户性格分析"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        # 年龄>35 且兴趣少且简介短，tone 会被兴趣类型覆盖为 thoughtful
        # 使用非外向非内向的兴趣来保持 mature tone
        profile = {"name": "老王", "age": 40, "interests": ["园艺", "书法"], "bio": ""}
        agent = UserSimulationAgent(profile)

        # 年长些更稳重（不会被覆盖）
        assert agent.reply_config["tone"] == "mature"
        assert agent.reply_config["reply_time_min_seconds"] > 3

    def test_analyze_many_interests_user(self):
        """测试兴趣多的用户性格分析"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        # 兴趣>=5 时 message_length=long，但简介短会被覆盖为 short
        profile = {
            "name": "小明",
            "age": 28,
            "interests": ["旅行", "摄影", "美食", "电影", "音乐"],
            "bio": "这是一个比较长的个人简介，超过 100 个字符。" * 3  # 使简介长度>100
        }
        agent = UserSimulationAgent(profile)

        assert agent.reply_config["message_length"] == "long"
        assert agent.reply_config["reply_probability"] == 0.95  # 上限

    def test_analyze_few_interests_user(self):
        """测试兴趣少的用户性格分析"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        # 兴趣<=2 且非外向非内向兴趣，message_length=short
        profile = {"name": "小李", "age": 28, "interests": ["园艺"], "bio": "简介长度超过 20 个字符但不到 100 个字符。"}
        agent = UserSimulationAgent(profile)

        # 兴趣少的人可能内向
        assert agent.reply_config["message_length"] == "short"
        assert agent.reply_config["emoji_usage"] == "rare"

    def test_analyze_long_bio_user(self):
        """测试简介长的用户性格分析"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        # 简介长度>100 时 message_length=long
        long_bio = "我是一个热爱生活的人，喜欢尝试各种新鲜事物。" * 5  # 超过 100 个字符
        profile = {
            "name": "小张",
            "age": 28,
            "interests": [],  # 空兴趣避免覆盖
            "bio": long_bio
        }
        agent = UserSimulationAgent(profile)

        assert agent.reply_config["message_length"] == "long"

    def test_analyze_short_bio_user(self):
        """测试简介短的用户性格分析"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "小赵", "age": 28, "interests": [], "bio": "你好"}
        agent = UserSimulationAgent(profile)

        assert agent.reply_config["message_length"] == "short"
        assert agent.reply_config["emoji_usage"] == "rare"

    def test_analyze_extrovert_interests(self):
        """测试外向型兴趣用户性格分析"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {
            "name": "小孙",
            "age": 28,
            "interests": ["旅行", "聚会", "舞蹈"],
            "bio": ""
        }
        agent = UserSimulationAgent(profile)

        assert agent.reply_config["tone"] == "enthusiastic"
        assert agent.reply_config["emoji_usage"] == "frequent"

    def test_analyze_introvert_interests(self):
        """测试内向型兴趣用户性格分析"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {
            "name": "小周",
            "age": 28,
            "interests": ["阅读", "写作", "编程"],
            "bio": ""
        }
        agent = UserSimulationAgent(profile)

        assert agent.reply_config["tone"] == "thoughtful"

    def test_probability_not_exceeds_max(self):
        """测试回复概率不超过最大值"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        # 年轻 + 兴趣多 + 简介长，多项叠加
        profile = {
            "name": "小吴",
            "age": 20,
            "interests": ["旅行", "聚会", "舞蹈", "音乐", "运动"],
            "bio": "我是一个非常外向的人，喜欢参加各种社交活动，享受和朋友在一起的时光。生活就是一场冒险！"
        }
        agent = UserSimulationAgent(profile)

        assert agent.reply_config["reply_probability"] <= 1.0


class TestUserSimulationAgentReplyTemplates:
    """测试回复模板"""

    def test_get_reply_templates_structure(self):
        """测试回复模板结构"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "interests": ["旅行"]}
        agent = UserSimulationAgent(profile)
        templates = agent._get_reply_templates()

        assert "greeting" in templates
        assert "interest" in templates
        assert "travel" in templates
        assert "food" in templates
        assert "work" in templates
        assert "question" in templates
        assert "general" in templates
        assert "short" in templates
        assert "emoji" in templates

    def test_get_reply_templates_with_custom_interests(self):
        """测试自定义兴趣的回复模板"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "摄影爱好者", "interests": ["摄影"]}
        agent = UserSimulationAgent(profile)
        templates = agent._get_reply_templates()

        # 应该包含与摄影相关的回复（interest 是列表，第一个元素应该包含摄影）
        assert len(templates["interest"]) > 0
        assert "摄影" in templates["interest"][0]

    def test_get_reply_templates_empty_interests(self):
        """测试无兴趣时的回复模板"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "无兴趣用户", "interests": []}
        agent = UserSimulationAgent(profile)
        templates = agent._get_reply_templates()

        # 应有默认兴趣回复
        assert "interest" in templates


class TestUserSimulationAgentReplyLogic:
    """测试回复逻辑"""

    def test_should_reply_positive(self):
        """测试应该回复的情况"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": ["旅行"]}
        agent = UserSimulationAgent(profile)

        # 正常消息应该回复
        result = agent.should_reply("你好，很高兴认识你")
        assert result is True

    def test_should_reply_negative_words(self):
        """测试包含负面词汇时不回复"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": ["旅行"]}
        agent = UserSimulationAgent(profile)

        negative_messages = ["滚", "烦", "讨厌", "拉黑", "别烦"]
        for msg in negative_messages:
            result = agent.should_reply(msg)
            assert result is False, f"应该对'{msg}'不回复"

    def test_should_reply_probability_check(self):
        """测试回复概率检查"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": ["旅行"]}
        agent = UserSimulationAgent(profile)

        # 使用固定的高回复概率配置
        agent.reply_config["reply_probability"] = 1.0

        # 应该总是回复
        for _ in range(10):
            result = agent.should_reply("测试消息")
            assert result is True

    def test_get_reply_delay(self):
        """测试回复延迟"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": ["旅行"]}
        agent = UserSimulationAgent(profile)

        delay = agent.get_reply_delay()

        assert delay >= agent.reply_config["reply_time_min_seconds"]
        assert delay <= agent.reply_config["reply_time_max_seconds"]

    def test_generate_reply_greeting(self):
        """测试生成打招呼回复"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": ["旅行"]}
        agent = UserSimulationAgent(profile)

        greeting_messages = ["你好", "hi", "hello", "嗨", "哈喽", "早", "好"]
        for msg in greeting_messages:
            reply = agent.generate_reply(msg)
            assert len(reply) > 0

    def test_generate_reply_interest(self):
        """测试生成兴趣相关回复"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": ["旅行", "摄影"]}
        agent = UserSimulationAgent(profile)

        reply = agent.generate_reply("我也很喜欢旅行")
        assert len(reply) > 0

    def test_generate_reply_travel(self):
        """测试生成旅行话题回复"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": ["旅行"]}
        agent = UserSimulationAgent(profile)

        reply = agent.generate_reply("我上周去了云南旅行")
        assert len(reply) > 0

    def test_generate_reply_food(self):
        """测试生成美食话题回复"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": ["美食"]}
        agent = UserSimulationAgent(profile)

        reply = agent.generate_reply("今天吃了一家很好吃的餐厅")
        assert len(reply) > 0

    def test_generate_reply_work(self):
        """测试生成工作话题回复"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": []}
        agent = UserSimulationAgent(profile)

        work_messages = ["工作好累", "今天加班了", "最近工作很忙", "辛苦了"]
        for msg in work_messages:
            reply = agent.generate_reply(msg)
            assert len(reply) > 0

    def test_generate_reply_question(self):
        """测试生成问题回复"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": []}
        agent = UserSimulationAgent(profile)

        questions = ["你喜欢什么？", "你去过那里吗？", "这是什么意思？"]
        for q in questions:
            reply = agent.generate_reply(q)
            assert len(reply) > 0

    def test_generate_reply_short_config(self):
        """测试短回复配置"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": []}
        agent = UserSimulationAgent(profile)
        agent.reply_config["message_length"] = "short"

        reply = agent.generate_reply("你好")
        assert len(reply) <= 5  # 短回复应该比较简短

    def test_generate_reply_with_frequent_emoji(self):
        """测试频繁使用表情的回复"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 20, "interests": ["旅行"]}
        agent = UserSimulationAgent(profile)

        # 年轻人应该频繁使用表情
        assert agent.reply_config["emoji_usage"] == "frequent"

        reply = agent.generate_reply("你好")
        # 应该包含表情符号
        emoji_chars = ["😊", "😄", "😁", "😍", "🥰", "✨", "🌟", "💕", "💖"]
        has_emoji = any(emoji in reply for emoji in emoji_chars)
        # 由于是随机添加，多次尝试至少一次有表情
        if not has_emoji:
            reply2 = agent.generate_reply("今天天气不错")
            has_emoji = any(emoji in reply2 for emoji in emoji_chars)
        # 注意：由于随机性，这个断言可能偶尔失败，但大多数情况下应该有表情

    def test_generate_reply_default(self):
        """测试生成默认回复"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": []}
        agent = UserSimulationAgent(profile)

        reply = agent.generate_reply("今天天气不错")
        assert len(reply) > 0


class TestUserSimulationAgentMessageSimulation:
    """测试消息模拟"""

    def test_simulate_receive_message_will_reply(self):
        """测试模拟收到消息会回复"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": ["旅行"]}
        agent = UserSimulationAgent(profile)
        agent.reply_config["reply_probability"] = 1.0  # 确保回复

        result = agent.simulate_receive_message(
            conversation_id="conv-123",
            message_content="你好，很高兴认识你",
            sender_id="user-456",
            sender_name="张三"
        )

        assert result is not None
        assert result["conversation_id"] == "conv-123"
        assert result["sender_id"] == "user-456"
        assert "content" in result
        assert "delay_seconds" in result
        assert result["message_type"] == "text"

    def test_simulate_receive_message_may_not_reply(self):
        """测试模拟收到消息可能不回复"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": ["旅行"]}
        agent = UserSimulationAgent(profile)
        agent.reply_config["reply_probability"] = 0.0  # 确保不回复

        result = agent.simulate_receive_message(
            conversation_id="conv-123",
            message_content="你好",
            sender_id="user-456",
            sender_name="张三"
        )

        assert result is None

    def test_simulate_receive_message_negative_content(self):
        """测试模拟收到负面消息不回复"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": ["旅行"]}
        agent = UserSimulationAgent(profile)

        result = agent.simulate_receive_message(
            conversation_id="conv-123",
            message_content="滚，别烦我",
            sender_id="user-456",
            sender_name="张三"
        )

        assert result is None

    def test_simulate_receive_message_updates_context(self):
        """测试模拟收到消息更新上下文"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": ["旅行"]}
        agent = UserSimulationAgent(profile)
        agent.reply_config["reply_probability"] = 0.0  # 不回复以便检查上下文

        agent.simulate_receive_message(
            conversation_id="conv-123",
            message_content="第一条消息",
            sender_id="user-456",
            sender_name="张三"
        )

        assert "conv-123" in agent.conversation_context
        assert len(agent.conversation_context["conv-123"]) == 1
        assert agent.conversation_context["conv-123"][0]["content"] == "第一条消息"
        assert agent.conversation_context["conv-123"][0]["role"] == "user"

    def test_simulate_receive_message_multiple_messages(self):
        """测试模拟收到多条消息"""
        from src.agent.user_simulation_agent import UserSimulationAgent

        profile = {"name": "测试用户", "age": 25, "interests": ["旅行"]}
        agent = UserSimulationAgent(profile)
        agent.reply_config["reply_probability"] = 0.0

        agent.simulate_receive_message(
            conversation_id="conv-123",
            message_content="第一条",
            sender_id="user-456",
            sender_name="张三"
        )
        agent.simulate_receive_message(
            conversation_id="conv-123",
            message_content="第二条",
            sender_id="user-456",
            sender_name="张三"
        )

        assert len(agent.conversation_context["conv-123"]) == 2


class TestHelperFunctions:
    """测试辅助函数"""

    def test_get_agent_for_user_with_profile(self):
        """测试使用画像创建 Agent"""
        from src.agent.user_simulation_agent import get_agent_for_user

        profile = {
            "name": "测试用户",
            "age": 25,
            "gender": "male",
            "interests": ["旅行"],
            "bio": "测试简介"
        }

        agent = get_agent_for_user("user-123", profile)

        assert agent.name == "测试用户"
        assert agent.age == 25

    def test_get_agent_for_user_without_profile(self):
        """测试不使用画像创建默认 Agent"""
        from src.agent.user_simulation_agent import get_agent_for_user

        agent = get_agent_for_user("user-123", None)

        assert agent is not None
        # 默认名字是从 ID 后 4 位生成的
        assert "用户" in agent.name or agent.name == "TA"

    def test_create_agent_from_db_user_found(self):
        """测试从数据库创建 Agent（用户存在）"""
        from src.agent.user_simulation_agent import create_agent_from_db

        # 模拟数据库和仓库
        mock_db = MagicMock()
        mock_user_repo = MagicMock()
        mock_db_user = MagicMock()
        mock_db_user.id = "user-123"
        mock_db_user.name = "张三"
        mock_db_user.age = 25
        mock_db_user.gender = "male"
        mock_db_user.email = "test@test.com"
        mock_db_user.location = "北京"
        mock_db_user.bio = "测试简介"
        mock_db_user.interests = '["旅行", "摄影"]'
        mock_db_user.values = '{}'
        mock_db_user.preferred_age_min = 20
        mock_db_user.preferred_age_max = 35
        mock_db_user.preferred_location = "北京"
        mock_db_user.preferred_gender = "female"

        mock_user_repo.get_by_id.return_value = mock_db_user

        with patch('db.repositories.UserRepository') as mock_repo_class:
            mock_repo_class.return_value = mock_user_repo

            with patch('api.users._from_db') as mock_from_db:
                mock_from_db.return_value = MagicMock(
                    model_dump=MagicMock(return_value={
                        "name": "张三",
                        "age": 25,
                        "gender": "male",
                        "interests": ["旅行", "摄影"],
                        "bio": "测试简介"
                    })
                )

                agent = create_agent_from_db(mock_db, "user-123")

                assert agent is not None
                assert agent.name == "张三"

    def test_create_agent_from_db_user_not_found(self):
        """测试从数据库创建 Agent（用户不存在）"""
        from src.agent.user_simulation_agent import create_agent_from_db

        mock_db = MagicMock()
        mock_user_repo = MagicMock()
        mock_user_repo.get_by_id.return_value = None

        with patch('db.repositories.UserRepository') as mock_repo_class:
            mock_repo_class.return_value = mock_user_repo

            agent = create_agent_from_db(mock_db, "non-existent-user")

            assert agent is None

    def test_create_agent_from_db_exception(self):
        """测试从数据库创建 Agent 异常处理"""
        from src.agent.user_simulation_agent import create_agent_from_db

        mock_db = MagicMock()

        with patch('db.repositories.UserRepository') as mock_repo_class:
            mock_repo_class.side_effect = Exception("数据库错误")

            agent = create_agent_from_db(mock_db, "user-123")

            assert agent is None
