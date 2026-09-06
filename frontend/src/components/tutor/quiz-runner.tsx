'use client';

import React, { useState } from 'react';
import { useTutorStore } from '@/store/tutorStore';
import { useReaderStore } from '@/store/readerStore';
import { QuizQuestion } from '@/types';
import {
  HelpCircle,
  Sparkles,
  CheckCircle2,
  XCircle,
  Award,
  BookOpen,
  RotateCw,
  Send,
  ChevronRight,
} from 'lucide-react';

interface QuizRunnerProps {
  documentId: string;
}

export const QuizRunner: React.FC<QuizRunnerProps> = ({ documentId }) => {
  const { activeQuiz, isGeneratingQuiz, generateQuiz, submitQuiz, activeSession } = useTutorStore();
  const { setCurrentPage } = useReaderStore();

  const [answersMap, setAnswersMap] = useState<Record<string, string>>({});
  const [questionCountSelect, setQuestionCountSelect] = useState<number>(5);

  const handleGenerate = async () => {
    setAnswersMap({});
    await generateQuiz(documentId, questionCountSelect, activeSession?.id);
  };

  const handleOptionSelect = (qId: string, value: string) => {
    setAnswersMap((prev) => ({ ...prev, [qId]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeQuiz) return;
    await submitQuiz(activeQuiz.id, answersMap);
  };

  if (!activeQuiz) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-slate-900/60 rounded-xl border border-slate-800 backdrop-blur-md text-center max-w-lg mx-auto my-6 shadow-2xl">
        <div className="w-16 h-16 bg-gradient-to-tr from-emerald-500 to-teal-500 rounded-2xl flex items-center justify-center mb-4 shadow-lg shadow-emerald-500/20">
          <HelpCircle className="w-8 h-8 text-white" />
        </div>
        <h3 className="text-xl font-bold text-slate-100 mb-2">Comprehension Quiz Runner</h3>
        <p className="text-slate-400 text-sm mb-6 leading-relaxed">
          Test your comprehension with auto-generated grounded quizzes. Supports Multiple Choice, True/False, and Short Answer questions with immediate AI grading.
        </p>

        <div className="w-full bg-slate-800/80 p-4 rounded-lg border border-slate-700/60 mb-6 text-left">
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Number of Questions
          </label>
          <div className="grid grid-cols-3 gap-2">
            {[3, 5, 8].map((cnt) => (
              <button
                key={cnt}
                onClick={() => setQuestionCountSelect(cnt)}
                className={`py-2 px-3 text-xs font-medium rounded-md transition-all ${
                  questionCountSelect === cnt
                    ? 'bg-emerald-600 text-white shadow-md shadow-emerald-500/30'
                    : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
                }`}
              >
                {cnt} Questions
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={isGeneratingQuiz}
          className="w-full py-3 px-6 bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500 text-white font-medium text-sm rounded-lg shadow-lg hover:brightness-110 active:scale-[0.99] transition-all flex items-center justify-center gap-2"
        >
          <Sparkles className="w-4 h-4" />
          {isGeneratingQuiz ? 'Generating Quiz...' : 'Generate Comprehension Quiz'}
        </button>
      </div>
    );
  }

  const isEvaluated = activeQuiz.evaluation_results && Object.keys(activeQuiz.evaluation_results).length > 0;
  const questions = activeQuiz.questions || [];

  // Calculate score summary
  let totalScore = 0;
  let correctCount = 0;

  if (isEvaluated) {
    Object.values(activeQuiz.evaluation_results).forEach((res: any) => {
      totalScore += res.score || 0;
      if (res.is_correct) correctCount += 1;
    });
  }

  const scorePct = questions.length > 0 ? (totalScore / questions.length) * 100 : 0;

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 rounded-xl border border-slate-800 shadow-xl overflow-hidden p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-emerald-500/10 border border-emerald-500/30 rounded-lg flex items-center justify-center text-emerald-400">
            <HelpCircle className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100">{activeQuiz.title}</h4>
            <p className="text-xs text-slate-400">{questions.length} Grounded Questions</p>
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={isGeneratingQuiz}
          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-200 rounded-lg flex items-center gap-1.5 transition-colors"
        >
          <RotateCw className={`w-3.5 h-3.5 ${isGeneratingQuiz ? 'animate-spin' : ''}`} />
          <span>New Quiz</span>
        </button>
      </div>

      {/* Evaluated Score Summary Banner */}
      {isEvaluated && (
        <div className="p-4 bg-slate-900 border border-emerald-500/40 rounded-xl flex items-center justify-between shadow-lg">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-500/20 text-emerald-400 rounded-lg flex items-center justify-center">
              <Award className="w-6 h-6" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-slate-100">Quiz Completed</h4>
              <p className="text-xs text-slate-400">
                You answered {correctCount} out of {questions.length} questions correctly.
              </p>
            </div>
          </div>
          <div className="text-right">
            <span className="text-2xl font-bold font-mono text-emerald-400">{scorePct.toFixed(0)}%</span>
            <span className="block text-[10px] text-slate-500 uppercase tracking-wider">Total Score</span>
          </div>
        </div>
      )}

      {/* Questions List Form */}
      <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto space-y-6 pr-1">
        {questions.map((q: QuizQuestion, index: number) => {
          const evalRes = isEvaluated ? activeQuiz.evaluation_results[q.id] : null;

          return (
            <div
              key={q.id || index}
              className={`p-5 bg-slate-900/80 border rounded-xl space-y-4 ${
                evalRes
                  ? evalRes.is_correct
                    ? 'border-emerald-500/40 bg-emerald-950/10'
                    : 'border-rose-500/40 bg-rose-950/10'
                  : 'border-slate-800'
              }`}
            >
              {/* Question Label */}
              <div className="flex items-start justify-between gap-3">
                <h5 className="text-sm font-medium text-slate-200 leading-relaxed">
                  <span className="font-mono text-emerald-400 mr-2 font-bold">{index + 1}.</span>
                  {q.question}
                </h5>

                {evalRes && (
                  <span className="shrink-0">
                    {evalRes.is_correct ? (
                      <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                    ) : (
                      <XCircle className="w-5 h-5 text-rose-400" />
                    )}
                  </span>
                )}
              </div>

              {/* Options: MCQ / True-False */}
              {(q.type === 'MCQ' || q.type === 'TRUE_FALSE') && q.options && (
                <div className="space-y-2 pl-4">
                  {q.options.map((opt, oIdx) => {
                    const isSelected = answersMap[q.id] === opt;

                    return (
                      <label
                        key={oIdx}
                        className={`flex items-center gap-3 p-3 rounded-lg border text-xs cursor-pointer transition-all ${
                          isSelected
                            ? 'bg-emerald-600/20 border-emerald-500/50 text-emerald-100 font-medium'
                            : 'bg-slate-950/60 border-slate-800 text-slate-300 hover:bg-slate-800/60'
                        }`}
                      >
                        <input
                          type="radio"
                          name={`q_${q.id}`}
                          value={opt}
                          disabled={isEvaluated}
                          checked={isSelected}
                          onChange={() => handleOptionSelect(q.id, opt)}
                          className="accent-emerald-500"
                        />
                        <span>{opt}</span>
                      </label>
                    );
                  })}
                </div>
              )}

              {/* Short Answer Input */}
              {q.type === 'SHORT_ANSWER' && (
                <div className="pl-4">
                  <input
                    type="text"
                    disabled={isEvaluated}
                    value={answersMap[q.id] || ''}
                    onChange={(e) => handleOptionSelect(q.id, e.target.value)}
                    placeholder="Type your brief answer here..."
                    className="w-full px-4 py-2.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              )}

              {/* Evaluated Explanation & Source Page */}
              {evalRes && (
                <div className="p-3 bg-slate-950 border border-slate-800/80 rounded-lg text-xs space-y-1.5 mt-2">
                  <div className="flex items-center justify-between text-slate-400">
                    <span>
                      Correct Answer:{' '}
                      <strong className="text-emerald-400 font-semibold">{q.correct_answer}</strong>
                    </span>

                    {q.citation_page && (
                      <button
                        type="button"
                        onClick={() => setCurrentPage(q.citation_page!)}
                        className="text-[11px] text-cyan-400 hover:underline flex items-center gap-1"
                      >
                        <BookOpen className="w-3 h-3" />
                        Page {q.citation_page}
                      </button>
                    )}
                  </div>
                  <p className="text-slate-300 leading-relaxed italic">{q.explanation}</p>
                </div>
              )}
            </div>
          );
        })}

        {/* Submit Button */}
        {!isEvaluated && (
          <div className="pt-4 border-t border-slate-800 flex justify-end">
            <button
              type="submit"
              disabled={Object.keys(answersMap).length === 0}
              className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-semibold rounded-lg shadow-md transition-all flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              Submit Quiz for Evaluation
            </button>
          </div>
        )}
      </form>
    </div>
  );
};
