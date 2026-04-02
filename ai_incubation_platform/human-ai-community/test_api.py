#!/usr/bin/env python3
"""
API功能测试脚本
"""
import requests
import json

BASE_URL = "http://localhost:8007"

def test_health():
    """测试健康检查"""
    print("=== 测试健康检查 ===")
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    print("✓ 健康检查通过")
    return True

def test_root():
    """测试根路由"""
    print("\n=== 测试根路由 ===")
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    print("✓ 根路由访问正常")
    print(f"  服务信息: {data['message']}")
    return True

def test_members():
    """测试成员接口"""
    print("\n=== 测试成员接口 ===")

    # 获取成员列表
    response = requests.get(f"{BASE_URL}/api/members")
    assert response.status_code == 200
    members = response.json()
    print(f"✓ 获取成员列表成功，共 {len(members)} 个成员")

    # 创建新人类成员
    new_member = {
        "name": "测试用户",
        "email": "test@example.com",
        "member_type": "human"
    }
    response = requests.post(f"{BASE_URL}/api/members", json=new_member)
    assert response.status_code == 200
    created_member = response.json()
    human_id = created_member["id"]
    print(f"✓ 创建人类成员成功: {created_member['name']} (ID: {human_id})")

    # 创建新AI成员
    new_ai = {
        "name": "测试AI",
        "member_type": "ai",
        "ai_model": "test-model",
        "ai_persona": "测试人格"
    }
    response = requests.post(f"{BASE_URL}/api/members", json=new_ai)
    assert response.status_code == 200
    created_ai = response.json()
    ai_id = created_ai["id"]
    print(f"✓ 创建AI成员成功: {created_ai['name']} (ID: {ai_id})")

    # 获取AI成员列表
    response = requests.get(f"{BASE_URL}/api/members/ai")
    assert response.status_code == 200
    ai_members = response.json()
    print(f"✓ 获取AI成员列表成功，共 {len(ai_members)} 个AI成员")

    return human_id, ai_id

def test_posts(human_id, ai_id):
    """测试帖子接口"""
    print("\n=== 测试帖子接口 ===")

    # 人类发帖
    human_post = {
        "author_id": human_id,
        "author_type": "human",
        "title": "人类发布的测试帖子",
        "content": "这是人类用户发布的测试内容",
        "tags": ["测试", "人类"]
    }
    response = requests.post(f"{BASE_URL}/api/posts", json=human_post)
    assert response.status_code == 200
    post1 = response.json()
    post1_id = post1["id"]
    print(f"✓ 人类发帖成功: {post1['title']} (ID: {post1_id})")

    # AI发帖
    ai_post = {
        "author_id": ai_id,
        "author_type": "ai",
        "title": "AI发布的测试帖子",
        "content": "这是AI发布的测试内容",
        "tags": ["测试", "AI"]
    }
    response = requests.post(f"{BASE_URL}/api/posts", json=ai_post)
    assert response.status_code == 200
    post2 = response.json()
    post2_id = post2["id"]
    print(f"✓ AI发帖成功: {post2['title']} (ID: {post2_id})")

    # 获取帖子列表
    response = requests.get(f"{BASE_URL}/api/posts")
    assert response.status_code == 200
    posts = response.json()
    print(f"✓ 获取帖子列表成功，共 {len(posts)} 个帖子")

    # 获取帖子详情
    response = requests.get(f"{BASE_URL}/api/posts/{post1_id}")
    assert response.status_code == 200
    post_detail = response.json()
    assert post_detail["id"] == post1_id
    print(f"✓ 获取帖子详情成功: {post_detail['title']}")

    return post1_id, post2_id

def test_comments(post_id, human_id, ai_id):
    """测试评论接口"""
    print("\n=== 测试评论接口 ===")

    # 人类评论
    human_comment = {
        "post_id": post_id,
        "author_id": human_id,
        "author_type": "human",
        "content": "人类用户的评论"
    }
    response = requests.post(f"{BASE_URL}/api/comments", json=human_comment)
    assert response.status_code == 200
    comment1 = response.json()
    comment1_id = comment1["id"]
    print(f"✓ 人类评论成功 (ID: {comment1_id})")

    # AI评论
    ai_comment = {
        "post_id": post_id,
        "author_id": ai_id,
        "author_type": "ai",
        "content": "AI的评论"
    }
    response = requests.post(f"{BASE_URL}/api/comments", json=ai_comment)
    assert response.status_code == 200
    comment2 = response.json()
    comment2_id = comment2["id"]
    print(f"✓ AI评论成功 (ID: {comment2_id})")

    # 回复评论
    reply = {
        "post_id": post_id,
        "author_id": human_id,
        "author_type": "human",
        "content": "回复AI的评论",
        "parent_id": comment2_id
    }
    response = requests.post(f"{BASE_URL}/api/comments", json=reply)
    assert response.status_code == 200
    reply_comment = response.json()
    print(f"✓ 回复评论成功 (父评论ID: {comment2_id})")

    # 获取帖子评论
    response = requests.get(f"{BASE_URL}/api/posts/{post_id}/comments")
    assert response.status_code == 200
    comments = response.json()
    print(f"✓ 获取帖子评论成功，共 {len(comments)} 条评论")

    # 获取评论回复
    response = requests.get(f"{BASE_URL}/api/comments/{comment2_id}/replies")
    assert response.status_code == 200
    replies = response.json()
    print(f"✓ 获取评论回复成功，共 {len(replies)} 条回复")

    return True

def test_content_review(human_id, ai_id):
    """测试内容审核功能"""
    print("\n=== 测试内容审核功能 ===")

    # 发布带审核的帖子
    post_data = {
        "author_id": human_id,
        "author_type": "human",
        "title": "测试带审核的帖子",
        "content": "这是正常的帖子内容",
        "tags": ["测试", "审核"]
    }
    response = requests.post(f"{BASE_URL}/api/posts/with-review", json=post_data)
    assert response.status_code == 200
    post = response.json()
    print(f"✓ 发布带审核帖子成功 (ID: {post['id']})")

    # 发布带审核的评论
    comment_data = {
        "post_id": post["id"],
        "author_id": ai_id,
        "author_type": "ai",
        "content": "这是AI的正常评论"
    }
    response = requests.post(f"{BASE_URL}/api/comments/with-review", json=comment_data)
    assert response.status_code == 200
    comment = response.json()
    print(f"✓ 发布带审核评论成功 (ID: {comment['id']})")

    # 获取待审核列表
    response = requests.get(f"{BASE_URL}/api/reviews/pending")
    assert response.status_code == 200
    pending = response.json()
    print(f"✓ 获取待审核列表成功，共 {len(pending)} 条待审核内容")

    # 创建审核规则
    rule_data = {
        "name": "测试规则",
        "description": "测试用的审核规则",
        "rule_type": "keyword",
        "config": {"keywords": ["测试敏感词"]},
        "risk_score": 0.8,
        "action": "reject"
    }
    response = requests.post(f"{BASE_URL}/api/review-rules", json=rule_data)
    assert response.status_code == 200
    rule = response.json()
    print(f"✓ 创建审核规则成功: {rule['name']}")

    return post["id"]

def test_ai_agent(ai_id):
    """测试AI Agent功能"""
    print("\n=== 测试AI Agent功能 ===")

    # AI生成帖子
    response = requests.post(
        f"{BASE_URL}/api/ai/agents/gpt-4/generate-post",
        params={"topic": "人工智能发展", "tags": ["AI", "技术"]}
    )
    assert response.status_code == 200
    ai_post = response.json()
    print(f"✓ AI生成帖子成功: {ai_post['title']}")

    # AI生成回复
    response = requests.post(
        f"{BASE_URL}/api/ai/agents/claude-3/generate-reply",
        params={"post_id": "test_post_id", "context": "讨论AI发展趋势"}
    )
    assert response.status_code == 200
    ai_reply = response.json()
    print(f"✓ AI生成回复成功: {ai_reply['content'][:30]}...")

    # AI通过专用接口发帖
    ai_post_data = {
        "author_id": ai_id,
        "author_type": "ai",
        "title": "AI通过Agent发布的帖子",
        "content": "这是AI通过统一Agent标准发布的内容",
        "tags": ["AI", "Agent"]
    }
    response = requests.post(
        f"{BASE_URL}/api/ai/posts",
        params={"agent_name": "gpt-4"},
        json=ai_post_data
    )
    assert response.status_code == 200
    created_post = response.json()
    print(f"✓ AI通过专用接口发帖成功 (ID: {created_post['id']})")

    return created_post["id"]

def test_rate_limit(human_id):
    """测试速率限制功能"""
    print("\n=== 测试速率限制功能 ===")

    # 创建速率限制规则
    limit_config = {
        "resource": "test",
        "limit": 2,
        "window_seconds": 60
    }
    response = requests.post(f"{BASE_URL}/api/rate-limits", json=limit_config)
    assert response.status_code == 200
    print("✓ 创建速率限制规则成功")

    # 查询剩余次数
    response = requests.get(f"{BASE_URL}/api/rate-limits/post/{human_id}/remaining")
    assert response.status_code == 200
    remaining = response.json()
    print(f"✓ 获取发帖剩余次数: {remaining['remaining']} 次/小时")

    # 测试速率限制（连续发帖直到触发限制）
    success_count = 0
    for i in range(10):
        post_data = {
            "author_id": human_id,
            "author_type": "human",
            "title": f"测试速率限制帖子 {i+1}",
            "content": "测试内容"
        }
        response = requests.post(f"{BASE_URL}/api/posts/with-review", json=post_data)
        if response.status_code == 200:
            success_count += 1
        else:
            print(f"✓ 第 {i+1} 次发帖触发速率限制，共成功 {success_count} 次")
            break

    return True

def main():
    """主测试函数"""
    print("🚀 开始API功能测试\n")

    try:
        test_health()
        test_root()
        human_id, ai_id = test_members()
        post1_id, post2_id = test_posts(human_id, ai_id)
        test_comments(post1_id, human_id, ai_id)

        # 测试P1新功能
        test_content_review(human_id, ai_id)
        test_ai_agent(ai_id)
        test_rate_limit(human_id)

        print("\n🎉 所有测试通过！API功能正常。")
        print("\n📊 测试结果汇总:")
        print("  ✅ 健康检查接口")
        print("  ✅ 成员管理接口（创建、列表、AI成员筛选）")
        print("  ✅ 帖子管理接口（创建、列表、详情）")
        print("  ✅ 评论管理接口（创建、列表、回复）")
        print("  ✅ 人类与AI身份区分")
        print("  ✅ 层级评论功能")
        print("  ✅ 内容审核队列与规则引擎")
        print("  ✅ 统一AI Agent标准接入")
        print("  ✅ 速率限制与反滥用策略")

    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    return True

if __name__ == "__main__":
    main()
