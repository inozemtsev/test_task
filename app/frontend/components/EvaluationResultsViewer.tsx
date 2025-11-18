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
import { CheckCircle2, XCircle, FileText, Brain, AlertTriangle, Info, TrendingUp, TrendingDown } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import Editor from "@monaco-editor/react";

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
        <div className="flex items-center gap-4 mt-2">
          <span className="text-sm text-muted-foreground">
            {evaluation.results?.length || 0} transcript(s) evaluated
          </span>
          {evaluation.schema_stability !== null && evaluation.schema_stability !== undefined && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Schema Stability:</span>
              <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/20 dark:text-blue-400 dark:border-blue-800">
                {(evaluation.schema_stability * 100).toFixed(1)}%
              </Badge>
            </div>
          )}
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
                    <Badge variant={result.final_score >= 0.7 ? "default" : "destructive"}>
                      {(result.final_score * 100).toFixed(0)}% pass
                    </Badge>
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-4 pt-2">
                    {/* Judge Results - TP/FP/FN Facts */}
                    {result.judge_result && (
                      <Card className="bg-green-50/50 dark:bg-green-950/20 border-green-200 dark:border-green-800">
                        <CardHeader className="pb-3">
                          <CardTitle className="text-sm flex items-center gap-2">
                            <Brain className="h-4 w-4" />
                            Judge Evaluation Results
                          </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                          {/* Summary Stats */}
                          <div className="grid grid-cols-3 gap-4">
                            <div className="text-center p-3 bg-green-100 dark:bg-green-900/30 rounded-lg">
                              <div className="text-2xl font-bold text-green-700 dark:text-green-400">
                                {result.judge_result.predicted_facts?.filter((f: any) => f.status === "TP" && f.in_scope).length || 0}
                              </div>
                              <div className="text-xs text-muted-foreground">True Positives</div>
                            </div>
                            <div className="text-center p-3 bg-red-100 dark:bg-red-900/30 rounded-lg">
                              <div className="text-2xl font-bold text-red-700 dark:text-red-400">
                                {result.judge_result.predicted_facts?.filter((f: any) => f.status === "FP" && f.in_scope).length || 0}
                              </div>
                              <div className="text-xs text-muted-foreground">False Positives</div>
                            </div>
                            <div className="text-center p-3 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
                              <div className="text-2xl font-bold text-amber-700 dark:text-amber-400">
                                {result.judge_result.gold_facts?.filter((f: any) => f.status === "FN" && f.in_scope).length || 0}
                              </div>
                              <div className="text-xs text-muted-foreground">False Negatives</div>
                            </div>
                          </div>

                          {/* Computed Metrics */}
                          {(() => {
                            const tp = result.judge_result.predicted_facts?.filter((f: any) => f.status === "TP" && f.in_scope).length || 0;
                            const fp = result.judge_result.predicted_facts?.filter((f: any) => f.status === "FP" && f.in_scope).length || 0;
                            const fn = result.judge_result.gold_facts?.filter((f: any) => f.status === "FN" && f.in_scope).length || 0;
                            const precision = (tp + fp) > 0 ? tp / (tp + fp) : 0;
                            const recall = (tp + fn) > 0 ? tp / (tp + fn) : 0;
                            const f1 = (precision + recall) > 0 ? 2 * (precision * recall) / (precision + recall) : 0;

                            return (
                              <div className="grid grid-cols-3 gap-4 pt-4 border-t">
                                <div>
                                  <div className="text-xs text-muted-foreground mb-1">Precision</div>
                                  <div className="flex items-center gap-2">
                                    <Progress value={precision * 100} className="h-2 flex-1" />
                                    <span className="text-sm font-medium">{(precision * 100).toFixed(1)}%</span>
                                  </div>
                                </div>
                                <div>
                                  <div className="text-xs text-muted-foreground mb-1">Recall</div>
                                  <div className="flex items-center gap-2">
                                    <Progress value={recall * 100} className="h-2 flex-1" />
                                    <span className="text-sm font-medium">{(recall * 100).toFixed(1)}%</span>
                                  </div>
                                </div>
                                <div>
                                  <div className="text-xs text-muted-foreground mb-1">F1 Score</div>
                                  <div className="flex items-center gap-2">
                                    <Progress value={f1 * 100} className="h-2 flex-1" />
                                    <span className="text-sm font-medium">{(f1 * 100).toFixed(1)}%</span>
                                  </div>
                                </div>
                              </div>
                            );
                          })()}

                          {/* Detailed Facts */}
                          <Collapsible className="pt-2 border-t">
                            <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium hover:underline">
                              <Info className="h-4 w-4" />
                              View Labeled Facts
                            </CollapsibleTrigger>
                            <CollapsibleContent className="space-y-4 pt-4">
                              {/* False Positives (Hallucinations) */}
                              {result.judge_result.predicted_facts?.filter((f: any) => f.status === "FP" && f.in_scope).length > 0 && (
                                <div>
                                  <h5 className="text-xs font-medium text-red-600 mb-2 flex items-center gap-1">
                                    <XCircle className="h-3 w-3" />
                                    False Positives - Hallucinated Facts
                                  </h5>
                                  <div className="space-y-2">
                                    {result.judge_result.predicted_facts
                                      .filter((f: any) => f.status === "FP" && f.in_scope)
                                      .map((fact: any, idx: number) => (
                                        <div key={idx} className="text-xs p-2 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded">
                                          <div className="font-medium text-red-700 dark:text-red-400 mb-1">
                                            {fact.fact_type} #{fact.id}
                                          </div>
                                          <pre className="text-xs overflow-auto">
                                            {JSON.stringify(fact.fields, null, 2)}
                                          </pre>
                                        </div>
                                      ))}
                                  </div>
                                </div>
                              )}

                              {/* False Negatives (Missed Facts) */}
                              {result.judge_result.gold_facts?.filter((f: any) => f.status === "FN" && f.in_scope).length > 0 && (
                                <div>
                                  <h5 className="text-xs font-medium text-amber-600 mb-2 flex items-center gap-1">
                                    <AlertTriangle className="h-3 w-3" />
                                    False Negatives - Missed Facts
                                  </h5>
                                  <div className="space-y-2">
                                    {result.judge_result.gold_facts
                                      .filter((f: any) => f.status === "FN" && f.in_scope)
                                      .map((fact: any, idx: number) => (
                                        <div key={idx} className="text-xs p-2 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800 rounded">
                                          <div className="font-medium text-amber-700 dark:text-amber-400 mb-1">
                                            {fact.fact_type} #{fact.id}
                                          </div>
                                          <pre className="text-xs overflow-auto">
                                            {JSON.stringify(fact.fields, null, 2)}
                                          </pre>
                                        </div>
                                      ))}
                                  </div>
                                </div>
                              )}

                              {/* True Positives */}
                              {result.judge_result.predicted_facts?.filter((f: any) => f.status === "TP" && f.in_scope).length > 0 && (
                                <div>
                                  <h5 className="text-xs font-medium text-green-600 mb-2 flex items-center gap-1">
                                    <CheckCircle2 className="h-3 w-3" />
                                    True Positives - Correctly Extracted Facts
                                  </h5>
                                  <div className="space-y-2">
                                    {result.judge_result.predicted_facts
                                      .filter((f: any) => f.status === "TP" && f.in_scope)
                                      .slice(0, 3)
                                      .map((fact: any, idx: number) => (
                                        <div key={idx} className="text-xs p-2 bg-green-50 dark:bg-green-950/20 border border-green-200 dark:border-green-800 rounded">
                                          <div className="font-medium text-green-700 dark:text-green-400 mb-1">
                                            {fact.fact_type} #{fact.id}
                                          </div>
                                          <pre className="text-xs overflow-auto">
                                            {JSON.stringify(fact.fields, null, 2)}
                                          </pre>
                                        </div>
                                      ))}
                                    {result.judge_result.predicted_facts.filter((f: any) => f.status === "TP" && f.in_scope).length > 3 && (
                                      <p className="text-xs text-muted-foreground italic">
                                        ... and {result.judge_result.predicted_facts.filter((f: any) => f.status === "TP" && f.in_scope).length - 3} more
                                      </p>
                                    )}
                                  </div>
                                </div>
                              )}
                            </CollapsibleContent>
                          </Collapsible>

                          {/* Judge Notes */}
                          {result.judge_result.notes && (
                            <div className="pt-2 border-t">
                              <h5 className="text-xs font-medium text-muted-foreground mb-2">Judge Notes:</h5>
                              <p className="text-xs italic">{result.judge_result.notes}</p>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    )}

                    {/* Metrics Overview Card */}
                    {result.schema_overlap_data && (
                      <Card className="bg-muted/30">
                        <CardContent className="pt-4">
                          <div className="space-y-3">
                            {/* Jaccard Similarity */}
                            <div>
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-medium">Schema Similarity (Jaccard)</span>
                                <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/20 dark:text-blue-400 dark:border-blue-800">
                                  {(result.schema_overlap_data.jaccard * 100).toFixed(1)}%
                                </Badge>
                              </div>
                              <Progress value={result.schema_overlap_data.jaccard * 100} className="h-2" />
                              <p className="text-xs text-muted-foreground mt-1">
                                {result.schema_overlap_data.intersection_count} / {result.schema_overlap_data.union_count} matching fields
                              </p>
                            </div>

                            {/* Top-level Metrics (if present) */}
                            {result.extracted_data?.numerator !== undefined && result.extracted_data?.denominator !== undefined && (
                              <div className="pt-2 border-t">
                                <span className="text-sm font-medium text-muted-foreground">Extraction Metrics: </span>
                                <span className="text-sm font-semibold">
                                  {result.extracted_data.numerator} / {result.extracted_data.denominator}
                                  {result.extracted_data.denominator > 0 && (
                                    <span className="text-muted-foreground ml-1">
                                      ({((result.extracted_data.numerator / result.extracted_data.denominator) * 100).toFixed(1)}%)
                                    </span>
                                  )}
                                </span>
                              </div>
                            )}

                            {/* Field Analysis Collapsible */}
                            <Collapsible className="pt-2 border-t">
                              <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium hover:underline">
                                <Info className="h-4 w-4" />
                                Field Analysis
                                <span className="text-xs text-muted-foreground">
                                  ({result.schema_overlap_data.missing_fields?.length || 0} missing, {result.schema_overlap_data.extra_fields?.length || 0} extra)
                                </span>
                              </CollapsibleTrigger>
                              <CollapsibleContent className="space-y-3 pt-3">
                                {/* Missing Fields */}
                                {result.schema_overlap_data.missing_fields && result.schema_overlap_data.missing_fields.length > 0 && (
                                  <div>
                                    <h5 className="text-xs font-medium text-amber-600 mb-2 flex items-center gap-1">
                                      <TrendingDown className="h-3 w-3" />
                                      Missing Fields ({result.schema_overlap_data.missing_fields.length})
                                    </h5>
                                    <div className="text-xs space-y-1">
                                      {result.schema_overlap_data.missing_fields.map((field: string, idx: number) => (
                                        <div key={idx} className="font-mono bg-amber-50 dark:bg-amber-950/20 px-2 py-1 rounded border border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400">
                                          {field}
                                        </div>
                                      ))}
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-1 italic">
                                      Fields defined in schema but not found in extraction
                                    </p>
                                  </div>
                                )}

                                {/* Extra Fields */}
                                {result.schema_overlap_data.extra_fields && result.schema_overlap_data.extra_fields.length > 0 && (
                                  <div>
                                    <h5 className="text-xs font-medium text-blue-600 mb-2 flex items-center gap-1">
                                      <TrendingUp className="h-3 w-3" />
                                      Extra Fields ({result.schema_overlap_data.extra_fields.length})
                                    </h5>
                                    <div className="text-xs space-y-1">
                                      {result.schema_overlap_data.extra_fields.map((field: string, idx: number) => (
                                        <div key={idx} className="font-mono bg-blue-50 dark:bg-blue-950/20 px-2 py-1 rounded border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-400">
                                          {field}
                                        </div>
                                      ))}
                                    </div>
                                    <p className="text-xs text-muted-foreground mt-1 italic">
                                      Fields found in extraction but not in schema
                                    </p>
                                  </div>
                                )}

                                {/* No issues */}
                                {(!result.schema_overlap_data.missing_fields || result.schema_overlap_data.missing_fields.length === 0) &&
                                 (!result.schema_overlap_data.extra_fields || result.schema_overlap_data.extra_fields.length === 0) && (
                                  <div className="text-sm text-muted-foreground flex items-center gap-2">
                                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                                    Perfect field match - all schema fields extracted, no extra fields
                                  </div>
                                )}
                              </CollapsibleContent>
                            </Collapsible>
                          </div>
                        </CardContent>
                      </Card>
                    )}

                    {/* Extracted Data Section */}
                    <Collapsible>
                      <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium hover:underline">
                        <Brain className="h-4 w-4" />
                        Extracted Data
                      </CollapsibleTrigger>
                      <CollapsibleContent className="pt-3">
                        <div className="border rounded-lg overflow-hidden">
                          <Editor
                            height="400px"
                            defaultLanguage="json"
                            value={JSON.stringify(result.extracted_data, null, 2)}
                            theme="vs-dark"
                            options={{
                              readOnly: true,
                              minimap: { enabled: false },
                              fontSize: 13,
                              lineNumbers: "on",
                              scrollBeyondLastLine: false,
                              automaticLayout: true,
                              tabSize: 2,
                            }}
                          />
                        </div>
                      </CollapsibleContent>
                    </Collapsible>

                    {/* Review Findings Section (Two-Pass Mode) */}
                    {result.review_data && (
                      <div>
                        <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                          <Info className="h-4 w-4" />
                          Review Findings (Two-Pass Extraction)
                        </h4>
                        <div className="space-y-3 border rounded-lg p-4">
                          {/* Summary */}
                          {result.review_data.summary && (
                            <div className="pb-2 border-b">
                              <p className="text-sm text-muted-foreground">{result.review_data.summary}</p>
                            </div>
                          )}

                          {/* Missing Items */}
                          {result.review_data.missing_items && result.review_data.missing_items.length > 0 && (
                            <div>
                              <h5 className="text-sm font-medium text-amber-600 mb-2 flex items-center gap-1">
                                <AlertTriangle className="h-3 w-3" />
                                Missing Items ({result.review_data.missing_items.length})
                              </h5>
                              <div className="space-y-2">
                                {result.review_data.missing_items.map((item: any, idx: number) => (
                                  <div key={idx} className="text-xs bg-amber-50 dark:bg-amber-950/20 p-2 rounded border border-amber-200 dark:border-amber-800">
                                    <div className="font-medium text-amber-700 dark:text-amber-400">
                                      {item.category}: {item.description}
                                    </div>
                                    {item.evidence && (
                                      <div className="text-muted-foreground mt-1 italic">
                                        &quot;{item.evidence}&quot;
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Hallucinated Items */}
                          {result.review_data.hallucinated_items && result.review_data.hallucinated_items.length > 0 && (
                            <div>
                              <h5 className="text-sm font-medium text-red-600 mb-2 flex items-center gap-1">
                                <XCircle className="h-3 w-3" />
                                Hallucinated Items ({result.review_data.hallucinated_items.length})
                              </h5>
                              <div className="space-y-2">
                                {result.review_data.hallucinated_items.map((item: any, idx: number) => (
                                  <div key={idx} className="text-xs bg-red-50 dark:bg-red-950/20 p-2 rounded border border-red-200 dark:border-red-800">
                                    <div className="font-medium text-red-700 dark:text-red-400">
                                      {item.field_path}
                                    </div>
                                    {item.extracted_value && (
                                      <div className="text-muted-foreground mt-1">
                                        Value: {JSON.stringify(item.extracted_value)}
                                      </div>
                                    )}
                                    <div className="text-muted-foreground mt-1">
                                      {item.reasoning}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Other Issues */}
                          {result.review_data.issues && result.review_data.issues.length > 0 && (
                            <div>
                              <h5 className="text-sm font-medium text-blue-600 mb-2 flex items-center gap-1">
                                <Info className="h-3 w-3" />
                                Other Issues ({result.review_data.issues.length})
                              </h5>
                              <div className="space-y-2">
                                {result.review_data.issues.map((issue: any, idx: number) => (
                                  <div key={idx} className="text-xs bg-blue-50 dark:bg-blue-950/20 p-2 rounded border border-blue-200 dark:border-blue-800">
                                    <div className="font-medium text-blue-700 dark:text-blue-400">
                                      {issue.type}: {issue.field_path}
                                    </div>
                                    <div className="text-muted-foreground mt-1">
                                      {issue.description}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Show if no issues found */}
                          {(!result.review_data.missing_items || result.review_data.missing_items.length === 0) &&
                           (!result.review_data.hallucinated_items || result.review_data.hallucinated_items.length === 0) &&
                           (!result.review_data.issues || result.review_data.issues.length === 0) && (
                            <div className="text-sm text-muted-foreground flex items-center gap-2">
                              <CheckCircle2 className="h-4 w-4 text-green-600" />
                              No issues identified in review
                            </div>
                          )}
                        </div>
                      </div>
                    )}
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
