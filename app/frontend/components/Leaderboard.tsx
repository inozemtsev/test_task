"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Trophy, Medal, Award, Calendar, Eye } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import EvaluationResultsViewer from "@/components/EvaluationResultsViewer";

interface LeaderboardEntry {
  experiment_id: number;
  experiment_name: string;
  avg_score: number;
  num_transcripts: number;
  evaluation_id: number;
  completed_at: string;
  avg_schema_overlap?: number;
  avg_metrics?: Record<string, any>;
  characteristic_results?: Record<string, any>;
}

interface LeaderboardProps {
  experimentId: number;
  leaderboard: LeaderboardEntry[];
}

export default function Leaderboard({
  experimentId,
  leaderboard,
}: LeaderboardProps) {
  const [selectedEvaluationId, setSelectedEvaluationId] = useState<number | null>(null);

  if (leaderboard.length === 0) {
    return (
      <Card className="h-96 flex items-center justify-center">
        <CardContent className="text-center text-muted-foreground">
          <Trophy className="mx-auto h-12 w-12 mb-4 opacity-50" />
          <p>No evaluations completed yet</p>
          <p className="text-sm mt-1">
            Run an evaluation to see results on the leaderboard
          </p>
        </CardContent>
      </Card>
    );
  }

  const getRankIcon = (index: number) => {
    switch (index) {
      case 0:
        return <Trophy className="h-5 w-5 text-yellow-500" />;
      case 1:
        return <Medal className="h-5 w-5 text-gray-400" />;
      case 2:
        return <Award className="h-5 w-5 text-amber-600" />;
      default:
        return <div className="h-5 w-5 flex items-center justify-center text-sm font-medium text-muted-foreground">{index + 1}</div>;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.9) return "text-green-600";
    if (score >= 0.7) return "text-blue-600";
    if (score >= 0.5) return "text-yellow-600";
    return "text-red-600";
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Trophy className="h-5 w-5" />
          Evaluation Leaderboard
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Ranked by average score across all transcripts
        </p>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {leaderboard.map((entry, index) => (
            <div
              key={entry.evaluation_id}
              className="flex items-center gap-4 p-4 border rounded-lg hover:bg-accent/50 transition-colors"
            >
              <div className="flex items-center justify-center w-8">
                {getRankIcon(index)}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <p className="font-medium truncate">{entry.experiment_name}</p>
                  <Badge variant="outline" className="text-xs">
                    #{entry.evaluation_id}
                  </Badge>
                </div>
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <span>{entry.num_transcripts} transcripts</span>
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {new Date(entry.completed_at).toLocaleDateString()}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-3">
                {/* Schema Stability */}
                {entry.avg_schema_overlap !== null && entry.avg_schema_overlap !== undefined && (
                  <div className="text-right">
                    <div className="text-lg font-semibold text-blue-600">
                      {(entry.avg_schema_overlap * 100).toFixed(1)}%
                    </div>
                    <div className="text-xs text-muted-foreground">schema stability</div>
                  </div>
                )}

                {/* Characteristic Results */}
                {entry.characteristic_results && Object.keys(entry.characteristic_results).length > 0 && (
                  <div className="flex flex-wrap gap-2 max-w-md">
                    {Object.entries(entry.characteristic_results).map(([charName, charData]: [string, any]) => (
                      <div key={charName} className="flex flex-col gap-1">
                        <div className="text-xs font-medium text-muted-foreground">{charName}</div>
                        <div className="flex flex-wrap gap-1">
                          {/* Show pass/fail if no metrics */}
                          {(!charData.metrics || Object.keys(charData.metrics).length === 0) && (
                            <Badge variant={charData.passes > charData.fails ? "default" : "destructive"} className="text-xs">
                              {charData.passes}/{charData.total}
                            </Badge>
                          )}

                          {/* Show metrics */}
                          {charData.metrics && Object.entries(charData.metrics).map(([metricKey, metricValue]: [string, any]) => {
                            if (typeof metricValue === 'object' && metricValue.numerator !== undefined && metricValue.denominator !== undefined) {
                              const percentage = metricValue.denominator > 0
                                ? (metricValue.numerator / metricValue.denominator * 100).toFixed(1)
                                : '0.0';
                              return (
                                <Badge key={metricKey} variant="outline" className="text-xs">
                                  {metricKey}: {metricValue.numerator}/{metricValue.denominator} ({percentage}%)
                                </Badge>
                              );
                            } else if (typeof metricValue === 'number') {
                              return (
                                <Badge key={metricKey} variant="outline" className="text-xs">
                                  {metricKey}: {(metricValue * 100).toFixed(0)}%
                                </Badge>
                              );
                            }
                            return null;
                          })}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedEvaluationId(entry.evaluation_id)}
                >
                  <Eye className="h-4 w-4 mr-1" />
                  View
                </Button>
              </div>
            </div>
          ))}
        </div>
      </CardContent>

      <Dialog open={!!selectedEvaluationId} onOpenChange={() => setSelectedEvaluationId(null)}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Evaluation Details</DialogTitle>
          </DialogHeader>
          {selectedEvaluationId && (
            <EvaluationResultsViewer evaluationId={selectedEvaluationId} />
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
}
