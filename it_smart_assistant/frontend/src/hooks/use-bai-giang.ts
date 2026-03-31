"use client";

import { useCallback, useState } from "react";
import { useAuthStore } from "@/stores";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface Subject {
  name: string;
  chunk_count: number;
}

export interface LectureResult {
  rank: number;
  chunk_id: string;
  content: string;
  subject: string;
  chapter: string;
  style_hint: string;
}

export interface SolveExerciseResponse {
  success: boolean;
  exercise: string;
  subject: string | null;
  solution: string;
  lecture_references: number;
  style_applied: string | null;
  error: string | null;
}

export interface UseBaiGiangReturn {
  // State
  subjects: Subject[];
  isLoadingSubjects: boolean;
  isSolving: boolean;
  searchResults: LectureResult[];
  isSearching: boolean;
  solution: SolveExerciseResponse | null;

  // Actions
  fetchSubjects: () => Promise<void>;
  searchLecture: (query: string, subject?: string, chapter?: string) => Promise<void>;
  solveExercise: (exercise: string, subject?: string, chapter?: string) => Promise<void>;
  clearSolution: () => void;
}

export function useBaiGiang(): UseBaiGiangReturn {
  const { token } = useAuthStore();

  // State
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [isLoadingSubjects, setIsLoadingSubjects] = useState(false);
  const [isSolving, setIsSolving] = useState(false);
  const [searchResults, setSearchResults] = useState<LectureResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [solution, setSolution] = useState<SolveExerciseResponse | null>(null);

  // Fetch available subjects
  const fetchSubjects = useCallback(async () => {
    setIsLoadingSubjects(true);
    try {
      const headers: Record<string, string> = {};
      if (token) {
        headers.Authorization = `Bearer ${token}`;
      }

      const response = await fetch(`${API_BASE}/bai-giang/subjects`, {
        headers,
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setSubjects(data.subjects || []);
    } catch (error) {
      console.error("Failed to fetch subjects:", error);
      // Set default subjects if API fails
      setSubjects([
        { name: "Toán", chunk_count: 0 },
        { name: "Vật lý", chunk_count: 0 },
        { name: "Hóa học", chunk_count: 0 },
        { name: "Lập trình", chunk_count: 0 },
        { name: "Cơ sở dữ liệu", chunk_count: 0 },
        { name: "Mạng máy tính", chunk_count: 0 },
        { name: "Trí tuệ nhân tạo", chunk_count: 0 },
        { name: "Phát triển Web", chunk_count: 0 },
      ]);
    } finally {
      setIsLoadingSubjects(false);
    }
  }, [token]);

  // Search lecture content
  const searchLecture = useCallback(
    async (query: string, subject?: string, chapter?: string) => {
      if (!query.trim()) return;

      setIsSearching(true);
      try {
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (token) {
          headers.Authorization = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE}/bai-giang/search`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            query,
            subject,
            chapter,
            top_k: 4,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        setSearchResults(data.results || []);
      } catch (error) {
        console.error("Failed to search lecture:", error);
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    },
    [token]
  );

  // Solve exercise with lecture style
  const solveExercise = useCallback(
    async (exercise: string, subject?: string, chapter?: string) => {
      if (!exercise.trim()) return;

      setIsSolving(true);
      setSolution(null);

      try {
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
        };
        if (token) {
          headers.Authorization = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE}/bai-giang/solve`, {
          method: "POST",
          headers,
          body: JSON.stringify({
            exercise,
            subject,
            chapter,
            use_lecture_context: true,
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data: SolveExerciseResponse = await response.json();
        setSolution(data);
      } catch (error) {
        console.error("Failed to solve exercise:", error);
        setSolution({
          success: false,
          exercise: exercise.slice(0, 500),
          subject: subject || null,
          solution: "",
          lecture_references: 0,
          style_applied: null,
          error: error instanceof Error ? error.message : "Unknown error",
        });
      } finally {
        setIsSolving(false);
      }
    },
    [token]
  );

  // Clear solution
  const clearSolution = useCallback(() => {
    setSolution(null);
    setSearchResults([]);
  }, []);

  return {
    subjects,
    isLoadingSubjects,
    isSolving,
    searchResults,
    isSearching,
    solution,
    fetchSubjects,
    searchLecture,
    solveExercise,
    clearSolution,
  };
}
