"use client";

import React, { useEffect, useState } from "react";
import { useBaiGiang } from "@/hooks/use-bai-giang";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { BookOpen, Calculator, CheckCircle, ChevronDown, ChevronUp, GraduationCap, Lightbulb, Loader2, Search, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface SolveExerciseProps {
  className?: string;
  initialSubject?: string;
}

export function SolveExercise({ className, initialSubject }: SolveExerciseProps) {
  const {
    subjects,
    isLoadingSubjects,
    isSolving,
    solution,
    searchResults,
    isSearching,
    fetchSubjects,
    solveExercise,
    clearSolution,
  } = useBaiGiang();

  const [exercise, setExercise] = useState("");
  const [selectedSubject, setSelectedSubject] = useState(initialSubject || "");
  const [chapter, setChapter] = useState("");
  const [showReferences, setShowReferences] = useState(false);

  // Load subjects on mount
  useEffect(() => {
    fetchSubjects();
  }, [fetchSubjects]);

  // Set initial subject when subjects loaded
  useEffect(() => {
    if (initialSubject && subjects.some((s) => s.name === initialSubject)) {
      setSelectedSubject(initialSubject);
    }
  }, [initialSubject, subjects]);

  const handleSolve = async () => {
    if (!exercise.trim()) return;
    await solveExercise(exercise, selectedSubject || undefined, chapter || undefined);
  };

  const handleClear = () => {
    setExercise("");
    setChapter("");
    clearSolution();
  };

  const formatSolution = (text: string) => {
    // Split by numbered steps or bullet points
    return text
      .replace(/^(\d+)[.):]\s*/gm, "**$1.** ") // Numbered steps
      .replace(/^[-*]\s*/gm, "• ") // Bullet points
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>"); // Bold
  };

  return (
    <div className={cn("space-y-6", className)}>
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-gradient-to-br from-violet-500 to-purple-600 rounded-lg">
          <GraduationCap className="w-6 h-6 text-white" />
        </div>
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-slate-100">
            Giải bài theo bài giảng
          </h2>
          <p className="text-slate-500 dark:text-slate-400">
            Nhập bài tập và nhận lời giải theo phong cách giảng dạy của thầy/cô
          </p>
        </div>
      </div>

      {/* Input Section */}
      <Card className="border-2 border-slate-100 dark:border-slate-800">
        <CardHeader className="pb-4">
          <CardTitle className="flex items-center gap-2 text-lg">
            <Calculator className="w-5 h-5 text-violet-500" />
            Bài tập cần giải
          </CardTitle>
          <CardDescription>
            Mô tả bài toán hoặc dán nội dung bài tập vào đây
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Subject & Chapter Selection */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="subject">Môn học</Label>
              <Select
                value={selectedSubject}
                onValueChange={setSelectedSubject}
                disabled={isLoadingSubjects}
              >
                <SelectTrigger id="subject" className="w-full">
                  <SelectValue placeholder="Chọn môn học" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Tất cả môn</SelectItem>
                  {subjects.map((subject) => (
                    <SelectItem key={subject.name} value={subject.name}>
                      <div className="flex items-center justify-between w-full gap-4">
                        <span>{subject.name}</span>
                        {subject.chunk_count > 0 && (
                          <Badge variant="secondary" className="text-xs">
                            {subject.chunk_count} tài liệu
                          </Badge>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="chapter">Chương/Bài (tùy chọn)</Label>
              <Input
                id="chapter"
                placeholder="Ví dụ: Chương 3 - Đạo hàm"
                value={chapter}
                onChange={(e) => setChapter(e.target.value)}
              />
            </div>
          </div>

          {/* Exercise Input */}
          <div className="space-y-2">
            <Label htmlFor="exercise">Nội dung bài tập</Label>
            <Textarea
              id="exercise"
              placeholder={`Ví dụ:
Tính đạo hàm của hàm số f(x) = x³ + 2x² - 5x + 3 tại điểm x = 2.

Hoặc dán bài toán phức tạp hơn với các bước giải...`}
              value={exercise}
              onChange={(e) => setExercise(e.target.value)}
              rows={6}
              className="font-mono text-sm resize-y min-h-[150px]"
            />
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Button
              onClick={handleSolve}
              disabled={!exercise.trim() || isSolving}
              className="bg-gradient-to-r from-violet-500 to-purple-600 hover:from-violet-600 hover:to-purple-700 text-white"
            >
              {isSolving ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Đang giải...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Giải bài
                </>
              )}
            </Button>

            <Button
              variant="outline"
              onClick={handleClear}
              disabled={!exercise && !solution}
            >
              Xóa
            </Button>

            {solution?.lecture_references !== undefined && (
              <Badge variant="outline" className="ml-auto">
                <BookOpen className="w-3 h-3 mr-1" />
                {solution.lecture_references} tài liệu tham khảo
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Solution Display */}
      {isSolving && (
        <Card className="border-2 border-slate-100 dark:border-slate-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Loader2 className="w-5 h-5 animate-spin text-violet-500" />
              Đang phân tích và giải bài...
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-5/6" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
          </CardContent>
        </Card>
      )}

      {solution && !isSolving && (
        <Card className="border-2 border-violet-100 dark:border-violet-900/50 bg-gradient-to-br from-white to-violet-50/30 dark:from-slate-950 dark:to-violet-950/10">
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="flex items-center gap-2 text-lg text-violet-700 dark:text-violet-300">
                  <CheckCircle className="w-5 h-5" />
                  Lời giải
                </CardTitle>
                {solution.style_applied && (
                  <CardDescription className="mt-1 flex items-center gap-2">
                    <Lightbulb className="w-4 h-4 text-amber-500" />
                    Phong cách: {solution.style_applied}
                  </CardDescription>
                )}
              </div>
              {solution.subject && (
                <Badge variant="secondary" className="bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-300">
                  {solution.subject}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-auto max-h-[600px]">
              <div className="prose prose-slate dark:prose-invert max-w-none">
                <div className="whitespace-pre-wrap font-sans leading-relaxed text-slate-700 dark:text-slate-300">
                  {solution.solution.split("\n").map((line, index) => {
                    // Check if line is a step header (numbered or bold)
                    const isStep = /^\*\*\d+\.\*\*/.test(line) || /^Bước \d+:/.test(line);
                    const isHeader = /^#{1,3}\s/.test(line) || /^(Phân tích|Lời giải|Kết luận|Đáp số)/.test(line);

                    if (isStep || isHeader) {
                      return (
                        <div
                          key={index}
                          className="font-semibold text-violet-700 dark:text-violet-300 mt-4 mb-2"
                        >
                          {line.replace(/\*\*/g, "")}
                        </div>
                      );
                    }

                    if (line.trim() === "") {
                      return <div key={index} className="h-2" />;
                    }

                    return (
                      <div key={index} className="mb-1">
                        {line}
                      </div>
                    );
                  })}
                </div>
              </div>
            </ScrollArea>

            {solution.error && (
              <div className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md text-red-700 dark:text-red-300 text-sm">
                Lỗi: {solution.error}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Search Results / References */}
      {searchResults.length > 0 && (
        <Card className="border-slate-200 dark:border-slate-700">
          <CardHeader
            className="pb-2 cursor-pointer"
            onClick={() => setShowReferences(!showReferences)}
          >
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2 text-base">
                <Search className="w-4 h-4 text-slate-500" />
                Tài liệu tham khảo
                <Badge variant="outline" className="ml-2">
                  {searchResults.length}
                </Badge>
              </CardTitle>
              <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
                {showReferences ? (
                  <ChevronUp className="w-4 h-4" />
                ) : (
                  <ChevronDown className="w-4 h-4" />
                )}
              </Button>
            </div>
          </CardHeader>

          {showReferences && (
            <CardContent>
              <div className="space-y-3">
                {searchResults.map((result, index) => (
                  <div
                    key={result.chunk_id}
                    className="p-3 bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-700"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline" className="text-xs">
                        #{index + 1}
                      </Badge>
                      <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                        {result.subject}
                      </span>
                      {result.chapter && (
                        <>
                          <Separator orientation="vertical" className="h-3" />
                          <span className="text-xs text-slate-500">
                            {result.chapter}
                          </span>
                        </>
                      )}
                    </div>
                    <p className="text-sm text-slate-600 dark:text-slate-400 line-clamp-3">
                      {result.content}
                    </p>
                    {result.style_hint && (
                      <div className="mt-2 flex items-center gap-1">
                        <Lightbulb className="w-3 h-3 text-amber-500" />
                        <span className="text-xs text-slate-500">
                          {result.style_hint}
                        </span>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          )}
        </Card>
      )}
    </div>
  );
}
