/**
 * 个人中心页面组件
 */
'use client';

import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { api } from '@/lib/api';
import { ScrollArea } from '@/components/ui/scroll-area';
import { User, Award, TrendingUp, MessageSquare, Star } from 'lucide-react';
import { formatNumber } from '@/lib/utils';

interface Member {
  id: string;
  username: string;
  member_type: 'human' | 'ai';
  bio?: string;
  reputation?: number;
}

interface LevelConfig {
  levels: Array<{
    level: number;
    name: string;
    min_experience: number;
  }>;
}

export function ProfilePage() {
  const [members, setMembers] = useState<Member[]>([]);
  const [levels, setLevels] = useState<LevelConfig | null>(null);
  const [currentUser, setCurrentUser] = useState<Member | null>(null);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [membersData, levelsData] = await Promise.all([
          api.members.list(),
          api.levels.getConfig(),
        ]);
        setMembers(membersData);
        setLevels(levelsData);

        // 设置当前用户（演示用，取第一个）
        if (membersData.length > 0) {
          setCurrentUser(membersData[0]);
        }
      } catch (error) {
        console.error('加载数据失败:', error);
      }
    };
    loadData();
  }, []);

  // 获取用户等级
  const getUserLevel = (reputation?: number) => {
    if (!reputation || !levels) return 1;
    for (let i = levels.levels.length - 1; i >= 0; i--) {
      if (reputation >= levels.levels[i].min_experience) {
        return levels.levels[i].level;
      }
    }
    return 1;
  };

  const getLevelName = (level: number) => {
    return levels?.levels.find((l) => l.level === level)?.name || '新手';
  };

  return (
    <ScrollArea className="h-[calc(100vh-4rem)]">
      <div className="p-4 space-y-4 max-w-3xl mx-auto">
        {/* 用户信息卡片 */}
        {currentUser && (
          <Card>
            <CardHeader>
              <div className="flex items-center gap-4">
                <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
                  <User className="h-8 w-8 text-primary" />
                </div>
                <div>
                  <h2 className="text-xl font-bold">{currentUser.username}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant={currentUser.member_type === 'ai' ? 'ai' : 'human'}>
                      {currentUser.member_type === 'ai' ? 'AI 成员' : '人类成员'}
                    </Badge>
                    <Badge variant="outline">
                      Lv.{getUserLevel(currentUser.reputation)} {getLevelName(getUserLevel(currentUser.reputation))}
                    </Badge>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4 mt-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">
                    {formatNumber(currentUser.reputation || 0)}
                  </div>
                  <div className="text-xs text-muted-foreground">声誉值</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">0</div>
                  <div className="text-xs text-muted-foreground">帖子数</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-primary">0</div>
                  <div className="text-xs text-muted-foreground">关注数</div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* 等级体系说明 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Award className="h-5 w-5" />
              等级体系
            </CardTitle>
          </CardHeader>
          <CardContent>
            {levels ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {levels.levels.map((level) => (
                  <div
                    key={level.level}
                    className="p-3 rounded-lg bg-secondary text-center"
                  >
                    <div className="text-sm font-bold text-primary">
                      Lv.{level.level}
                    </div>
                    <div className="text-xs text-muted-foreground truncate">
                      {level.name}
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {level.min_experience}+ 经验
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground">等级信息加载中...</p>
            )}
          </CardContent>
        </Card>

        {/* 成员列表 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              社区成员
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {members.map((member) => (
                <div
                  key={member.id}
                  className="flex items-center gap-3 p-3 rounded-lg bg-secondary"
                >
                  <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <User className="h-5 w-5 text-primary" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{member.username}</div>
                    <div className="text-xs text-muted-foreground flex items-center gap-2">
                      <Badge variant={member.member_type === 'ai' ? 'ai' : 'human'} className="text-xs">
                        {member.member_type === 'ai' ? 'AI' : '人类'}
                      </Badge>
                      <span className="flex items-center gap-1">
                        <Star className="h-3 w-3" />
                        {member.reputation || 0}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </ScrollArea>
  );
}
