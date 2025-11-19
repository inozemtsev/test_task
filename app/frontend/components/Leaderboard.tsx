"use client";

import { useState, useMemo } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Trophy, Medal, Award, Calendar, Eye, ArrowUpDown } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import EvaluationResultsViewer from "@/components/EvaluationResultsViewer";

interface LeaderboardEntry {
  experiment_id: number;
  experiment_name: string;
  avg_score: number;
  num_transcripts: number;
  evaluation_id: number;
  completed_at: string;
  schema_stability?: number;
  global_precision?: number;
  global_recall?: number;
  global_f1?: number;
  total_tp?: number;
  total_fp?: number;
  total_fn?: number;
}

interface LeaderboardProps {
  leaderboard: LeaderboardEntry[];
}

type SortField = "global_f1" | "avg_score" | "global_precision" | "global_recall" | "schema_stability";

export default function Leaderboard({
  leaderboard,
}: LeaderboardProps) {
  const [selectedEvaluationId, setSelectedEvaluationId] = useState<number | null>(null);
  const [sortBy, setSortBy] = useState<SortField>("global_f1");

  // Sort leaderboard based on selected field
  const sortedLeaderboard = useMemo(() => {
    return [...leaderboard].sort((a, b) => {
      const aValue = a[sortBy] ?? 0;
      const bValue = b[sortBy] ?? 0;
      return bValue - aValue; // Descending order
    });
  }, [leaderboard, sortBy]);

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
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Trophy className="h-5 w-5" />
              Evaluation Leaderboard
            </CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              Ranked by {sortBy.replace(/_/g, " ")}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <ArrowUpDown className="h-4 w-4 text-muted-foreground" />
            <Select value={sortBy} onValueChange={(value) => setSortBy(value as SortField)}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Sort by..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="global_f1">Global F1</SelectItem>
                <SelectItem value="global_precision">Precision</SelectItem>
                <SelectItem value="global_recall">Recall</SelectItem>
                <SelectItem value="avg_score">Avg Score</SelectItem>
                <SelectItem value="schema_stability">Schema Stability</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {sortedLeaderboard.map((entry, index) => (
            <div
              key={entry.evaluation_id}
              className="flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 p-3 sm:p-4 border rounded-lg hover:bg-accent/50 transition-colors"
            >
              {/* Rank Icon */}
              <div className="hidden sm:flex items-center justify-center w-8 flex-shrink-0">
                {getRankIcon(index)}
              </div>

              {/* Mobile: Rank + Title on same line */}
              <div className="flex sm:hidden items-center gap-2">
                <div className="flex items-center justify-center w-6">
                  {getRankIcon(index)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium truncate">{entry.experiment_name}</p>
                    <Badge variant="outline" className="text-xs">
                      #{entry.evaluation_id}
                    </Badge>
                  </div>
                </div>
              </div>

              {/* Desktop: Title */}
              <div className="hidden sm:block flex-1 min-w-0">
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

              {/* Metrics Section */}
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
                {/* Global Metrics */}
                {entry.global_f1 !== null && entry.global_f1 !== undefined && (
                  <div className="grid grid-cols-3 gap-2 sm:flex sm:gap-3">
                    <div className="text-center sm:text-right">
                      <div className={`text-base sm:text-lg font-semibold ${getScoreColor(entry.schema_stability ?? 0)}`}>
                        {((entry.schema_stability ?? 0) * 100).toFixed(1)}%
                      </div>
                      <div className="text-xs text-muted-foreground">Scheme Stability</div>
                    </div>
                    <div className="text-center sm:text-right">
                      <div className={`text-base sm:text-lg font-semibold ${getScoreColor(entry.global_precision ?? 0)}`}>
                        {((entry.global_precision ?? 0) * 100).toFixed(1)}%
                      </div>
                      <div className="text-xs text-muted-foreground">Precision</div>
                    </div>
                    <div className="text-center sm:text-right">
                      <div className={`text-base sm:text-lg font-semibold ${getScoreColor(entry.global_recall ?? 0)}`}>
                        {((entry.global_recall ?? 0) * 100).toFixed(1)}%
                      </div>
                      <div className="text-xs text-muted-foreground">Recall</div>
                    </div>
                    <div className="text-center sm:text-right">
                      <div className={`text-base sm:text-lg font-semibold ${getScoreColor(entry.global_f1)}`}>
                        {(entry.global_f1 * 100).toFixed(1)}%
                      </div>
                      <div className="text-xs text-muted-foreground">F1</div>
                    </div>
                  </div>
                )}

                {/* View Button */}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedEvaluationId(entry.evaluation_id)}
                  className="w-full sm:w-auto"
                >
                  <Eye className="h-4 w-4 mr-1" />
                  View
                </Button>
              </div>

              {/* Mobile: Additional info below */}
              <div className="sm:hidden flex items-center gap-3 text-xs text-muted-foreground border-t pt-2 mt-1">
                <span>{entry.num_transcripts} transcripts</span>
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  {new Date(entry.completed_at).toLocaleDateString()}
                </span>
                {entry.schema_stability !== null && entry.schema_stability !== undefined && (
                  <span>
                    Stability: {(entry.schema_stability * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>

      <Dialog open={!!selectedEvaluationId} onOpenChange={() => setSelectedEvaluationId(null)}>
        <DialogContent className="max-w-full sm:max-w-4xl max-h-[80vh] overflow-y-auto">
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
