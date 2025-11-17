"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { judgesAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Plus, Trash2, CheckCircle2, XCircle, Trophy } from "lucide-react";
import CharacteristicForm from "@/components/CharacteristicForm";
import Leaderboard from "@/components/Leaderboard";

interface JudgeDetailProps {
  judgeId: number;
  availableModels: string[];
}

export default function JudgeDetail({
  judgeId,
  availableModels,
}: JudgeDetailProps) {
  const queryClient = useQueryClient();
  const [showAddCharacteristic, setShowAddCharacteristic] = useState(false);

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

  const deleteCharacteristicMutation = useMutation({
    mutationFn: judgesAPI.deleteCharacteristic,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["judge", judgeId] });
      queryClient.invalidateQueries({ queryKey: ["judges"] });
    },
  });

  const handleDeleteCharacteristic = (characteristicId: number) => {
    if (
      confirm("Are you sure you want to delete this characteristic?")
    ) {
      deleteCharacteristicMutation.mutate(characteristicId);
    }
  };

  const handleAddSuccess = () => {
    setShowAddCharacteristic(false);
    queryClient.invalidateQueries({ queryKey: ["judge", judgeId] });
    queryClient.invalidateQueries({ queryKey: ["judges"] });
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
                <Badge variant="outline">
                  {judge.characteristics?.length || 0} characteristics
                </Badge>
              </div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="characteristics">
            <TabsList>
              <TabsTrigger value="characteristics">
                Characteristics ({judge.characteristics?.length || 0})
              </TabsTrigger>
              <TabsTrigger value="leaderboard">
                <Trophy className="h-4 w-4 mr-1" />
                Leaderboard ({leaderboard?.length || 0})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="characteristics" className="space-y-4 mt-4">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">Evaluation Criteria</h3>
                <Button
                  size="sm"
                  variant={showAddCharacteristic ? "secondary" : "default"}
                  onClick={() => setShowAddCharacteristic(!showAddCharacteristic)}
                >
                  <Plus className="h-4 w-4 mr-1" />
                  {showAddCharacteristic ? "Cancel" : "Add"}
                </Button>
              </div>

              {showAddCharacteristic && (
                <div className="p-4 border rounded-lg bg-muted/50">
                  <CharacteristicForm
                    judgeId={judgeId}
                    onSuccess={handleAddSuccess}
                  />
                </div>
              )}

              {judge.characteristics && judge.characteristics.length > 0 ? (
                <ScrollArea className="h-[400px]">
                  <div className="space-y-3 pr-4">
                    {judge.characteristics.map((char: any) => (
                      <div
                        key={char.id}
                        className="border rounded-lg p-4 hover:bg-accent/50 transition-colors"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                            <h4 className="font-medium">{char.name}</h4>
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => handleDeleteCharacteristic(char.id)}
                            className="h-8 w-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                        <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                          {char.prompt}
                        </p>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              ) : (
                <div className="text-center py-8 text-muted-foreground border rounded-lg">
                  <XCircle className="mx-auto h-8 w-8 mb-2 opacity-50" />
                  <p className="text-sm">No characteristics defined</p>
                  <p className="text-xs mt-1">
                    Add characteristics to define evaluation criteria
                  </p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="leaderboard" className="mt-4">
              <Leaderboard
                experimentId={judgeId}
                leaderboard={leaderboard || []}
              />
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
}
