"use client";

import { useQuery } from "@tanstack/react-query";
import { evaluationsAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Progress } from "@/components/ui/progress";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { CheckCircle2, XCircle, FileText, Brain } from "lucide-react";

interface EvaluationResultsViewerProps {
  evaluationId: number;
}

export default function EvaluationResultsViewer({
  evaluationId,
}: EvaluationResultsViewerProps) {
  const { data: evaluation, isLoading } = useQuery({
    queryKey: ["evaluation", evaluationId],
    queryFn: () => evaluationsAPI.get(evaluationId),
    refetchInterval: 5000, // Refresh while running
    enabled: !!evaluationId,
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-20 bg-muted rounded animate-pulse"
              />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!evaluation) {
    return (
      <Card>
        <CardContent className="p-6 text-center text-muted-foreground">
          Evaluation not found
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Evaluation Results</CardTitle>
          <Badge variant={evaluation.status === "completed" ? "default" : "secondary"}>
            {evaluation.status}
          </Badge>
        </div>
        <div className="text-sm text-muted-foreground">
          {evaluation.results?.length || 0} transcript(s) evaluated
        </div>
      </CardHeader>
      <CardContent>
        {evaluation.results && evaluation.results.length > 0 ? (
          <Accordion type="single" collapsible className="w-full">
            {evaluation.results.map((result: any, index: number) => (
              <AccordionItem key={result.id} value={`result-${result.id}`}>
                <AccordionTrigger className="hover:no-underline">
                  <div className="flex items-center justify-between w-full pr-4">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      <span className="font-medium">{result.transcript_name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={result.final_score >= 0.7 ? "default" : "destructive"}>
                        {(result.final_score * 100).toFixed(0)}% pass
                      </Badge>
                      {result.schema_overlap_percentage !== null && result.schema_overlap_percentage !== undefined && (
                        <Badge variant="outline">
                          {(result.schema_overlap_percentage * 100).toFixed(0)}% stability
                        </Badge>
                      )}
                    </div>
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-4 pt-2">
                    {/* Extracted Data Section */}
                    <div>
                      <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                        <Brain className="h-4 w-4" />
                        Extracted Data
                      </h4>
                      <ScrollArea className="h-[200px] w-full rounded-md border p-4">
                        <pre className="text-xs whitespace-pre-wrap font-mono">
                          {JSON.stringify(result.extracted_data, null, 2)}
                        </pre>
                      </ScrollArea>
                    </div>

                    {/* Schema Stability Section */}
                    {result.schema_overlap_percentage !== null && result.schema_overlap_percentage !== undefined && (
                      <div>
                        <h4 className="text-sm font-medium mb-2">Schema Stability</h4>
                        <div className="flex items-center gap-3 p-3 border rounded-lg">
                          <Progress
                            value={result.schema_overlap_percentage * 100}
                            className="flex-1"
                          />
                          <span className="text-sm font-medium min-w-[3rem] text-right">
                            {(result.schema_overlap_percentage * 100).toFixed(1)}%
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Characteristic Votes Section */}
                    <div>
                      <h4 className="text-sm font-medium mb-2">
                        Characteristic Evaluations
                      </h4>
                      <div className="space-y-2">
                        {result.characteristic_votes?.map((vote: any) => (
                          <Card key={vote.id} className="p-3">
                            <div className="flex items-start gap-3">
                              <div className="mt-0.5">
                                {vote.vote ? (
                                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                                ) : (
                                  <XCircle className="h-5 w-5 text-red-600" />
                                )}
                              </div>
                              <div className="flex-1 space-y-1">
                                <div className="flex items-center justify-between">
                                  <p className="font-medium text-sm">
                                    {vote.characteristic_name}
                                  </p>
                                  <Badge variant={vote.vote ? "default" : "destructive"}>
                                    {vote.vote ? "Pass" : "Fail"}
                                  </Badge>
                                </div>

                                {/* Display all fields from result_data (if available, otherwise fall back to individual fields) */}
                                {vote.result_data && Object.keys(vote.result_data).length > 0 ? (
                                  <div className="space-y-2 mt-2">
                                    {/* Handle top-level numerator/denominator first */}
                                    {vote.result_data.numerator !== undefined && vote.result_data.denominator !== undefined && (
                                      <div className="text-sm">
                                        <span className="text-muted-foreground font-medium">Score:</span>
                                        <span className="ml-2 font-medium">
                                          {vote.result_data.numerator}/{vote.result_data.denominator}
                                          {vote.result_data.denominator > 0 && (
                                            <span className="text-muted-foreground ml-1">
                                              ({((vote.result_data.numerator / vote.result_data.denominator) * 100).toFixed(1)}%)
                                            </span>
                                          )}
                                        </span>
                                      </div>
                                    )}

                                    {Object.entries(vote.result_data).map(([key, value]: [string, any]) => {
                                      // Skip passes (already shown as badge)
                                      if (key === 'passes') return null;

                                      // Skip numerator/denominator (already shown above)
                                      if (key === 'numerator' || key === 'denominator') return null;

                                      // Handle reasoning specially (multiline text)
                                      if (key === 'reasoning' && typeof value === 'string') {
                                        return (
                                          <div key={key}>
                                            <span className="text-xs font-medium text-muted-foreground">Reasoning:</span>
                                            <p className="text-sm text-muted-foreground whitespace-pre-wrap mt-1">
                                              {value}
                                            </p>
                                          </div>
                                        );
                                      }

                                      // Handle metrics object specially
                                      if (key === 'metrics' && typeof value === 'object' && value !== null) {
                                        return (
                                          <div key={key} className="space-y-1">
                                            <span className="text-xs font-medium text-muted-foreground">Metrics:</span>
                                            <div className="flex flex-wrap gap-2">
                                              {Object.entries(value).map(([metricKey, metricValue]: [string, any]) => {
                                                if (typeof metricValue === 'object' && metricValue.numerator !== undefined && metricValue.denominator !== undefined) {
                                                  const percentage = metricValue.denominator > 0
                                                    ? (metricValue.numerator / metricValue.denominator * 100).toFixed(1)
                                                    : '0.0';
                                                  return (
                                                    <div key={metricKey} className="text-xs">
                                                      <span className="text-muted-foreground">{metricKey}:</span>
                                                      <span className="font-medium ml-1">
                                                        {metricValue.numerator}/{metricValue.denominator} ({percentage}%)
                                                      </span>
                                                    </div>
                                                  );
                                                } else if (typeof metricValue === 'number') {
                                                  return (
                                                    <div key={metricKey} className="text-xs">
                                                      <span className="text-muted-foreground">{metricKey}:</span>
                                                      <span className="font-medium ml-1">
                                                        {(metricValue * 100).toFixed(0)}%
                                                      </span>
                                                    </div>
                                                  );
                                                }
                                                return null;
                                              })}
                                            </div>
                                          </div>
                                        );
                                      }

                                      // Handle arrays
                                      if (Array.isArray(value)) {
                                        return (
                                          <div key={key} className="text-xs">
                                            <span className="text-muted-foreground font-medium">{key}:</span>
                                            <ul className="list-disc list-inside ml-2 mt-1">
                                              {value.map((item, idx) => (
                                                <li key={idx} className="text-muted-foreground">
                                                  {typeof item === 'object' ? JSON.stringify(item) : String(item)}
                                                </li>
                                              ))}
                                            </ul>
                                          </div>
                                        );
                                      }

                                      // Handle objects (non-metrics)
                                      if (typeof value === 'object' && value !== null) {
                                        return (
                                          <div key={key} className="text-xs">
                                            <span className="text-muted-foreground font-medium">{key}:</span>
                                            <pre className="text-xs bg-muted p-2 rounded mt-1 whitespace-pre-wrap">
                                              {JSON.stringify(value, null, 2)}
                                            </pre>
                                          </div>
                                        );
                                      }

                                      // Handle primitives (string, number, boolean)
                                      return (
                                        <div key={key} className="text-xs">
                                          <span className="text-muted-foreground font-medium">{key}:</span>
                                          <span className="ml-1">
                                            {String(value)}
                                          </span>
                                        </div>
                                      );
                                    })}
                                  </div>
                                ) : (
                                  /* Fallback to individual fields for old evaluations */
                                  <div className="space-y-2 mt-2">
                                    {/* Reasoning */}
                                    {vote.reasoning && (
                                      <div>
                                        <span className="text-xs font-medium text-muted-foreground">Reasoning:</span>
                                        <p className="text-sm text-muted-foreground whitespace-pre-wrap mt-1">
                                          {vote.reasoning}
                                        </p>
                                      </div>
                                    )}

                                    {/* Metrics */}
                                    {vote.metrics && Object.keys(vote.metrics).length > 0 && (
                                      <div className="space-y-1">
                                        <span className="text-xs font-medium text-muted-foreground">Metrics:</span>
                                        <div className="flex flex-wrap gap-2">
                                          {Object.entries(vote.metrics).map(([key, value]: [string, any]) => {
                                            if (typeof value === 'object' && value.numerator !== undefined && value.denominator !== undefined) {
                                              const percentage = value.denominator > 0
                                                ? (value.numerator / value.denominator * 100).toFixed(1)
                                                : '0.0';
                                              return (
                                                <div key={key} className="text-xs">
                                                  <span className="text-muted-foreground">{key}:</span>
                                                  <span className="font-medium ml-1">
                                                    {value.numerator}/{value.denominator} ({percentage}%)
                                                  </span>
                                                </div>
                                              );
                                            } else if (typeof value === 'number') {
                                              return (
                                                <div key={key} className="text-xs">
                                                  <span className="text-muted-foreground">{key}:</span>
                                                  <span className="font-medium ml-1">
                                                    {(value * 100).toFixed(0)}%
                                                  </span>
                                                </div>
                                              );
                                            }
                                            return null;
                                          })}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>
                          </Card>
                        ))}
                      </div>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        ) : (
          <div className="text-center text-muted-foreground py-8">
            No results yet
          </div>
        )}
      </CardContent>
    </Card>
  );
}
