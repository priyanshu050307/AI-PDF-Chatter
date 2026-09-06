'use client';

import React, { useState } from 'react';
import { useTutorStore } from '@/store/tutorStore';
import { useReaderStore } from '@/store/readerStore';
import { Flashcard, FlashcardRating } from '@/types';
import {
  Layers,
  Sparkles,
  RotateCw,
  ChevronLeft,
  ChevronRight,
  BookOpen,
  CheckCircle,
  HelpCircle,
} from 'lucide-react';

interface FlashcardDeckProps {
  documentId: string;
}

export const FlashcardDeck: React.FC<FlashcardDeckProps> = ({ documentId }) => {
  const { flashcards, isGeneratingDeck, generateFlashcards, rateFlashcard, activeSession } = useTutorStore();
  const { setCurrentPage } = useReaderStore();

  const [currentIndex, setCurrentIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);
  const [cardCountSelect, setCardCountSelect] = useState<number>(5);

  const currentCard: Flashcard | undefined = flashcards[currentIndex];

  const handleNext = () => {
    if (currentIndex < flashcards.length - 1) {
      setIsFlipped(false);
      setCurrentIndex((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      setIsFlipped(false);
      setCurrentIndex((prev) => prev - 1);
    }
  };

  const handleRate = async (rating: FlashcardRating) => {
    if (!currentCard) return;
    await rateFlashcard(currentCard.id, rating);
    handleNext();
  };

  const handleGenerate = async () => {
    await generateFlashcards(documentId, cardCountSelect, activeSession?.id);
    setCurrentIndex(0);
    setIsFlipped(false);
  };

  if (flashcards.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-slate-900/60 rounded-xl border border-slate-800 backdrop-blur-md text-center max-w-lg mx-auto my-6 shadow-2xl">
        <div className="w-16 h-16 bg-gradient-to-tr from-cyan-500 to-blue-500 rounded-2xl flex items-center justify-center mb-4 shadow-lg shadow-cyan-500/20">
          <Layers className="w-8 h-8 text-white" />
        </div>
        <h3 className="text-xl font-bold text-slate-100 mb-2">AI Flashcards Deck</h3>
        <p className="text-slate-400 text-sm mb-6 leading-relaxed">
          Generate grounded AI flashcards directly from this document. Each flashcard cites the exact source page so you can verify facts and test your recall.
        </p>

        <div className="w-full bg-slate-800/80 p-4 rounded-lg border border-slate-700/60 mb-6 text-left">
          <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
            Number of Flashcards
          </label>
          <div className="grid grid-cols-3 gap-2">
            {[5, 10, 15].map((cnt) => (
              <button
                key={cnt}
                onClick={() => setCardCountSelect(cnt)}
                className={`py-2 px-3 text-xs font-medium rounded-md transition-all ${
                  cardCountSelect === cnt
                    ? 'bg-cyan-600 text-white shadow-md shadow-cyan-500/30'
                    : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
                }`}
              >
                {cnt} Cards
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={isGeneratingDeck}
          className="w-full py-3 px-6 bg-gradient-to-r from-cyan-500 via-blue-500 to-indigo-500 text-white font-medium text-sm rounded-lg shadow-lg hover:brightness-110 active:scale-[0.99] transition-all flex items-center justify-center gap-2"
        >
          <Sparkles className="w-4 h-4" />
          {isGeneratingDeck ? 'Generating Cards...' : 'Generate Flashcard Deck'}
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-100 rounded-xl border border-slate-800 shadow-xl overflow-hidden p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-cyan-500/10 border border-cyan-500/30 rounded-lg flex items-center justify-center text-cyan-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-100">Study Flashcards</h4>
            <p className="text-xs text-slate-400">
              Card {currentIndex + 1} of {flashcards.length}
            </p>
          </div>
        </div>

        <button
          onClick={handleGenerate}
          disabled={isGeneratingDeck}
          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-xs text-slate-200 rounded-lg flex items-center gap-1.5 transition-colors"
        >
          <RotateCw className={`w-3.5 h-3.5 ${isGeneratingDeck ? 'animate-spin' : ''}`} />
          <span>Regenerate Deck</span>
        </button>
      </div>

      {/* 3D Flip Card Container */}
      <div className="flex-1 flex items-center justify-center min-h-[320px] perspective-1000">
        <div
          onClick={() => setIsFlipped(!isFlipped)}
          className={`w-full max-w-xl min-h-[280px] bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl cursor-pointer transition-all duration-500 flex flex-col justify-between hover:border-slate-700 relative ${
            isFlipped ? 'bg-slate-900/90 border-cyan-500/40 shadow-cyan-500/10' : ''
          }`}
        >
          {/* Card Side Badge */}
          <div className="flex items-center justify-between text-xs text-slate-400 border-b border-slate-800/80 pb-3">
            <span className="font-mono text-cyan-400 uppercase tracking-wider font-semibold">
              {isFlipped ? 'Back — Answer / Explanation' : 'Front — Prompt / Question'}
            </span>
            <span className="text-[11px] text-slate-500">Click card to flip</span>
          </div>

          {/* Card Content */}
          <div className="my-6 text-center text-base md:text-lg text-slate-100 leading-relaxed font-medium">
            {isFlipped ? currentCard?.back : currentCard?.front}
          </div>

          {/* Source Citations Footer */}
          {currentCard?.source_citations && currentCard.source_citations.length > 0 && (
            <div className="pt-3 border-t border-slate-800/80 flex items-center justify-center gap-2">
              {currentCard.source_citations.map((cite, idx) => (
                <button
                  key={idx}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (cite.page_number) setCurrentPage(cite.page_number);
                  }}
                  className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-xs rounded-md flex items-center gap-1 transition-colors"
                >
                  <BookOpen className="w-3 h-3 text-cyan-400" />
                  <span>Page {cite.page_number || 'Source'}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Review Rating & Navigation Controls */}
      <div className="space-y-4 pt-2 border-t border-slate-800">
        {isFlipped && (
          <div className="flex items-center justify-center gap-3">
            <span className="text-xs text-slate-400 font-medium mr-2">Rate Difficulty:</span>
            <button
              onClick={() => handleRate('AGAIN')}
              className="px-3.5 py-1.5 bg-rose-500/10 border border-rose-500/30 hover:bg-rose-500/20 text-rose-400 text-xs font-semibold rounded-lg transition-colors"
            >
              Again (Hardest)
            </button>
            <button
              onClick={() => handleRate('HARD')}
              className="px-3.5 py-1.5 bg-amber-500/10 border border-amber-500/30 hover:bg-amber-500/20 text-amber-400 text-xs font-semibold rounded-lg transition-colors"
            >
              Hard
            </button>
            <button
              onClick={() => handleRate('GOOD')}
              className="px-3.5 py-1.5 bg-blue-500/10 border border-blue-500/30 hover:bg-blue-500/20 text-blue-400 text-xs font-semibold rounded-lg transition-colors"
            >
              Good
            </button>
            <button
              onClick={() => handleRate('EASY')}
              className="px-3.5 py-1.5 bg-emerald-500/10 border border-emerald-500/30 hover:bg-emerald-500/20 text-emerald-400 text-xs font-semibold rounded-lg transition-colors"
            >
              Easy
            </button>
          </div>
        )}

        {/* Deck Navigation Buttons */}
        <div className="flex items-center justify-between">
          <button
            onClick={handlePrev}
            disabled={currentIndex === 0}
            className="px-4 py-2 bg-slate-900 border border-slate-800 disabled:opacity-40 text-slate-300 rounded-lg text-xs font-medium hover:bg-slate-800 flex items-center gap-1.5 transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            Previous
          </button>

          <span className="text-xs text-slate-500 font-mono">
            {currentIndex + 1} / {flashcards.length}
          </span>

          <button
            onClick={handleNext}
            disabled={currentIndex === flashcards.length - 1}
            className="px-4 py-2 bg-slate-900 border border-slate-800 disabled:opacity-40 text-slate-300 rounded-lg text-xs font-medium hover:bg-slate-800 flex items-center gap-1.5 transition-colors"
          >
            Next
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
