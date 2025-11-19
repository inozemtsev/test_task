"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { judgesAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Trophy, Settings } from "lucide-react";
import Leaderboard from "@/components/Leaderboard";
import { JudgeConfigEditor, JudgeConfig } from "@/components/JudgeConfigEditor";

interface JudgeDetailProps {
  judgeId: number;
}

export default function JudgeDetail({
  judgeId,
}: JudgeDetailProps) {
  const queryClient = useQueryClient();
  const [configChanged, setConfigChanged] = useState(false);
  const [tempConfig, setTempConfig] = useState<JudgeConfig | null>(null);

  const { data: judge, isLoading } = useQuery({
    queryKey: ["judge", judgeId],
    queryFn: () => judgesAPI.get(judgeId),
    enabled: !!judgeId,
  });

  const { data: leaderboard } = useQuery({
    queryKey: ["judge-leaderboard", judgeId],
    queryFn: () => judgesAPI.getLeaderboard(judgeId),
    enabled: !!judgeId,
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  const updateJudgeMutation = useMutation({
    mutationFn: (config: JudgeConfig) =>
      judgesAPI.update(judgeId, { judge_config: config as unknown as Record<string, unknown> }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["judge", judgeId] });
      queryClient.invalidateQueries({ queryKey: ["judges"] });
      setConfigChanged(false);
      setTempConfig(null);
    },
  });

  const handleConfigChange = (config: JudgeConfig) => {
    setTempConfig(config);
    setConfigChanged(true);
  };

  const handleSaveConfig = () => {
    if (tempConfig) {
      updateJudgeMutation.mutate(tempConfig);
    }
  };

  const handleCancelConfig = () => {
    setTempConfig(null);
    setConfigChanged(false);
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="animate-pulse">
          <div className="h-8 bg-muted rounded w-1/2" />
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-20 bg-muted rounded animate-pulse" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!judge) {
    return (
      <Card className="h-full flex items-center justify-center">
        <CardContent className="text-center text-muted-foreground">
          <p>Judge not found</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div>
              <CardTitle>{judge.name}</CardTitle>
              <div className="flex items-center gap-2 mt-2">
                <Badge variant="secondary">{judge.model}</Badge>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="config">
            <TabsList>
              <TabsTrigger value="config">
                <Settings className="h-4 w-4 mr-1" />
                Configuration
              </TabsTrigger>
              <TabsTrigger value="leaderboard">
                <Trophy className="h-4 w-4 mr-1" />
                Leaderboard ({leaderboard?.length || 0})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="config" className="mt-4">
              <div className="space-y-4">
                <JudgeConfigEditor
                  config={tempConfig || judge.judge_config}
                  onChange={handleConfigChange}
                />
                {configChanged && (
                  <div className="flex items-center justify-end gap-2 p-4 border-t bg-muted/50">
                    <Button variant="outline" onClick={handleCancelConfig}>
                      Cancel
                    </Button>
                    <Button
                      onClick={handleSaveConfig}
                      disabled={updateJudgeMutation.isPending}
                    >
                      {updateJudgeMutation.isPending ? "Saving..." : "Save Configuration"}
                    </Button>
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="leaderboard" className="mt-4">
              <Leaderboard
                leaderboard={leaderboard || []}
              />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
