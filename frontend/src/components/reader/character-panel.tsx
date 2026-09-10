'use client';

import React, { useState, useEffect } from 'react';
import {
  Users,
  User,
  Search,
  X,
  ChevronRight,
  ShieldAlert,
  Sparkles,
  BookOpen,
  Calendar,
  Network,
  MessageSquare,
  ArrowLeft,
  Loader2,
  Lock,
  Eye,
  MapPin,
  Building2
} from 'lucide-react';
import { useReaderStore } from '@/store/readerStore';
import {
  EntityItem,
  CharacterProfile,
  NarrativeEventItem,
  NarrativeAskResponse
} from '@/types';
import { narrativeApi } from '@/services/narrativeApi';

interface CharacterPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export const CharacterPanel: React.FC<CharacterPanelProps> = ({ isOpen, onClose }) => {
  const { documentId, currentPage, setCurrentPage } = useReaderStore();

  const [entities, setEntities] = useState<EntityItem[]>([]);
  const [timeline, setTimeline] = useState<NarrativeEventItem[]>([]);
  const [selectedEntity, setSelectedEntity] = useState<EntityItem | null>(null);
  const [entityProfile, setEntityProfile] = useState<CharacterProfile | null>(null);

  const [activeTab, setActiveTab] = useState<'ROSTER' | 'TIMELINE'>('ROSTER');
  const [importanceFilter, setImportanceFilter] = useState<'ALL' | 'MAJOR' | 'MINOR'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [spoilerMode, setSpoilerMode] = useState<'spoiler_free' | 'full_book'>('spoiler_free');

  // Interactive AI Q&A State
  const [aiQuestion, setAiQuestion] = useState('');
  const [aiResponse, setAiResponse] = useState<NarrativeAskResponse | null>(null);
  const [isLoadingEntities, setIsLoadingEntities] = useState(false);
  const [isLoadingProfile, setIsLoadingProfile] = useState(false);
  const [isAskingAi, setIsAskingAi] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);

  // Load Entities and Timeline on open
  useEffect(() => {
    if (!isOpen || !documentId) return;

    const loadData = async () => {
      setIsLoadingEntities(true);
      setApiError(null);
      try {
        const ents = await narrativeApi.getEntities(documentId).catch(() => []);
        const evts = await narrativeApi.getTimeline(documentId, spoilerMode === 'spoiler_free' ? currentPage : undefined).catch(() => []);
        setEntities(ents);
        setTimeline(evts);
      } catch (err: any) {
        console.error('Failed to load narrative entities:', err);
        setEntities([]);
        setTimeline([]);
      } finally {
        setIsLoadingEntities(false);
      }
    };

    loadData();
  }, [isOpen, documentId, currentPage, spoilerMode]);

  // Load Entity Profile when selected
  useEffect(() => {
    if (!documentId || !selectedEntity) {
      setEntityProfile(null);
      return;
    }

    const loadProfile = async () => {
      setIsLoadingProfile(true);
      try {
        const maxPage = spoilerMode === 'spoiler_free' ? currentPage : undefined;
        const prof = await narrativeApi.getEntityProfile(documentId, selectedEntity.id, maxPage);
        setEntityProfile(prof);
      } catch (err) {
        console.error('Failed to load entity profile:', err);
      } finally {
        setIsLoadingProfile(false);
      }
    };

    loadProfile();
  }, [documentId, selectedEntity, currentPage, spoilerMode]);

  if (!isOpen) return null;

  const handleAskAi = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!documentId || !aiQuestion.trim() || isAskingAi) return;

    setIsAskingAi(true);
    setAiResponse(null);
    try {
      const prompt = selectedEntity
        ? `Regarding ${selectedEntity.name}: ${aiQuestion}`
        : aiQuestion;

      const res = await narrativeApi.askQuestion(documentId, {
        query: prompt,
        spoiler_mode: spoilerMode,
        current_page: currentPage,
      });
      setAiResponse(res);
    } catch (err: any) {
      console.error('Failed to query narrative AI:', err);
    } finally {
      setIsAskingAi(false);
    }
  };

  const filteredEntities = entities.filter((ent) => {
    if (importanceFilter === 'MAJOR' && ent.importance !== 'major') return false;
    if (importanceFilter === 'MINOR' && ent.importance !== 'minor') return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = ent.name.toLowerCase().includes(q);
      const matchAlias = ent.aliases?.some((a) => a.toLowerCase().includes(q));
      if (!matchName && !matchAlias) return false;
    }
    return true;
  });

  const getEntityIcon = (type: string) => {
    switch (type.toUpperCase()) {
      case 'LOCATION':
        return <MapPin className="w-4 h-4 text-emerald-400" />;
      case 'ORGANIZATION':
        return <Building2 className="w-4 h-4 text-amber-400" />;
      default:
        return <User className="w-4 h-4 text-indigo-400" />;
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 w-80 sm:w-96 bg-slate-900/95 backdrop-blur-xl border-l border-slate-800 z-50 flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3.5 border-b border-slate-800 bg-slate-950/60">
        <div className="flex items-center gap-2">
          <Users className="w-4 h-4 text-indigo-400" />
          <h2 className="text-sm font-bold text-slate-100">Narrative Intelligence</h2>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Control Bar: Spoiler Toggle & Mode Tabs */}
      <div className="p-3 border-b border-slate-800/80 space-y-3 bg-slate-900/40">
        {/* Spoiler Protection Toggle */}
        <div className="flex items-center justify-between p-2 rounded-lg bg-slate-950/80 border border-slate-800 text-xs">
          <div className="flex items-center gap-1.5 text-slate-300">
            {spoilerMode === 'spoiler_free' ? (
              <Lock className="w-3.5 h-3.5 text-amber-400" />
            ) : (
              <Eye className="w-3.5 h-3.5 text-rose-400" />
            )}
            <span className="font-semibold">
              {spoilerMode === 'spoiler_free' ? `Capped at Page ${currentPage}` : 'Full Book View'}
            </span>
          </div>
          <button
            onClick={() =>
              setSpoilerMode(spoilerMode === 'spoiler_free' ? 'full_book' : 'spoiler_free')
            }
            className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase transition-colors ${
              spoilerMode === 'spoiler_free'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-amber-500/30'
                : 'bg-rose-500/20 text-rose-300 border border-rose-500/30 hover:bg-rose-500/30'
            }`}
          >
            {spoilerMode === 'spoiler_free' ? 'Spoiler-Free' : 'Full Book'}
          </button>
        </div>

        {/* Navigation Tabs */}
        {!selectedEntity && (
          <div className="grid grid-cols-2 gap-1 p-1 bg-slate-950/80 rounded-lg text-xs font-medium border border-slate-800">
            <button
              onClick={() => setActiveTab('ROSTER')}
              className={`py-1.5 rounded-md transition-colors ${
                activeTab === 'ROSTER'
                  ? 'bg-indigo-600 text-white font-semibold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Characters & Entities
            </button>
            <button
              onClick={() => setActiveTab('TIMELINE')}
              className={`py-1.5 rounded-md transition-colors ${
                activeTab === 'TIMELINE'
                  ? 'bg-indigo-600 text-white font-semibold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Timeline Events
            </button>
          </div>
        )}
      </div>

      {/* Selected Entity Detailed Profile View */}
      {selectedEntity ? (
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Back Button */}
          <button
            onClick={() => setSelectedEntity(null)}
            className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 font-semibold mb-2"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Roster</span>
          </button>

          {/* Entity Profile Card */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
                  {getEntityIcon(selectedEntity.entity_type)}
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">{selectedEntity.name}</h3>
                  <p className="text-xs text-slate-400 capitalize">{selectedEntity.entity_type.toLowerCase()}</p>
                </div>
              </div>
              <span
                className={`px-2 py-0.5 text-[10px] font-bold rounded-full uppercase ${
                  selectedEntity.importance === 'major'
                    ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                    : 'bg-slate-800 text-slate-400'
                }`}
              >
                {selectedEntity.importance}
              </span>
            </div>

            {selectedEntity.description && (
              <p className="text-xs text-slate-300 leading-relaxed">{selectedEntity.description}</p>
            )}

            {selectedEntity.aliases && selectedEntity.aliases.length > 0 && (
              <div className="flex flex-wrap gap-1 pt-1">
                <span className="text-[11px] text-slate-500 font-medium">Known as:</span>
                {selectedEntity.aliases.map((alias, idx) => (
                  <span
                    key={idx}
                    className="px-1.5 py-0.5 text-[10px] rounded bg-slate-800 text-slate-300 border border-slate-700"
                  >
                    {alias}
                  </span>
                ))}
              </div>
            )}

            <div className="flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-800/80 pt-2">
              <span>First appeared: Page {selectedEntity.first_appeared_page}</span>
              <span>Mentions: {selectedEntity.mention_count}</span>
            </div>
          </div>

          {/* Relationships Graph Web Section */}
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-200">
              <Network className="w-3.5 h-3.5 text-indigo-400" />
              <span>Relationship Web</span>
            </div>

            {isLoadingProfile ? (
              <div className="flex items-center justify-center py-6 text-slate-500 text-xs">
                <Loader2 className="w-4 h-4 animate-spin mr-2 text-indigo-400" />
                <span>Loading relationships...</span>
              </div>
            ) : entityProfile?.relationships && entityProfile.relationships.length > 0 ? (
              <div className="space-y-2">
                {entityProfile.relationships.map((rel) => (
                  <div
                    key={rel.id}
                    className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-200">
                        {rel.source_entity_name || 'Character'} → {rel.target_entity_name || 'Character'}
                      </span>
                      <span className="px-1.5 py-0.5 rounded bg-indigo-500/10 text-indigo-300 text-[10px] font-bold uppercase">
                        {rel.relationship_type.replace('_', ' ')}
                      </span>
                    </div>
                    {rel.description && (
                      <p className="text-[11px] text-slate-400">{rel.description}</p>
                    )}
                    <div className="text-[10px] text-slate-500 text-right">
                      Observed Page {rel.observed_page}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic p-2 bg-slate-950/40 rounded-lg">
                No explicit relationships observed up to page {currentPage}.
              </p>
            )}
          </div>

          {/* Character Timeline Section */}
          <div className="space-y-2">
            <div className="flex items-center gap-1.5 text-xs font-bold text-slate-200">
              <Calendar className="w-3.5 h-3.5 text-amber-400" />
              <span>Key Events</span>
            </div>

            {isLoadingProfile ? (
              <div className="flex items-center justify-center py-6 text-slate-500 text-xs">
                <Loader2 className="w-4 h-4 animate-spin mr-2 text-amber-400" />
                <span>Loading events...</span>
              </div>
            ) : entityProfile?.events && entityProfile.events.length > 0 ? (
              <div className="space-y-2">
                {entityProfile.events.map((ev) => (
                  <div
                    key={ev.id}
                    onClick={() => setCurrentPage(ev.page_number)}
                    className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 hover:border-indigo-500/50 transition-colors cursor-pointer text-xs space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-slate-200">{ev.title}</span>
                      <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-bold">
                        Page {ev.page_number}
                      </span>
                    </div>
                    {ev.description && (
                      <p className="text-[11px] text-slate-400 leading-normal">{ev.description}</p>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 italic p-2 bg-slate-950/40 rounded-lg">
                No events recorded for this character yet.
              </p>
            )}
          </div>
        </div>
      ) : activeTab === 'ROSTER' ? (
        /* Roster View */
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {/* Filters */}
          <div className="space-y-2">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search characters, entities, aliases..."
                className="w-full pl-8 pr-3 py-1.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center justify-between text-xs px-1">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Importance</span>
              <div className="flex gap-1">
                {(['ALL', 'MAJOR', 'MINOR'] as const).map((filter) => (
                  <button
                    key={filter}
                    onClick={() => setImportanceFilter(filter)}
                    className={`px-2 py-0.5 rounded text-[10px] font-bold transition-colors ${
                      importanceFilter === filter
                        ? 'bg-indigo-600 text-white'
                        : 'bg-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {filter}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Roster Cards */}
          {isLoadingEntities ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-400">
              <Loader2 className="w-8 h-8 text-indigo-500 animate-spin mb-2" />
              <p className="text-xs font-medium">Extracting narrative entities...</p>
            </div>
          ) : apiError ? (
            <div className="p-3 text-xs bg-rose-500/10 border border-rose-500/20 text-rose-300 rounded-lg">
              {apiError}
            </div>
          ) : filteredEntities.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center text-slate-500">
              <User className="w-8 h-8 text-slate-600 mb-2" />
              <p className="text-xs font-medium">No characters found</p>
            </div>
          ) : (
            filteredEntities.map((ent) => (
              <div
                key={ent.id}
                onClick={() => setSelectedEntity(ent)}
                className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-indigo-500/50 hover:bg-slate-950 transition-all cursor-pointer group space-y-2"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
                      {getEntityIcon(ent.entity_type)}
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-100 group-hover:text-indigo-300 transition-colors">
                        {ent.name}
                      </h4>
                      <p className="text-[10px] text-slate-400 capitalize">{ent.entity_type.toLowerCase()}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1">
                    <span
                      className={`px-1.5 py-0.5 text-[9px] font-bold rounded uppercase ${
                        ent.importance === 'major'
                          ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                          : 'bg-slate-800 text-slate-400'
                      }`}
                    >
                      {ent.importance}
                    </span>
                    <ChevronRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-slate-300 transition-colors" />
                  </div>
                </div>

                {ent.description && (
                  <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">{ent.description}</p>
                )}

                <div className="flex items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-800/60">
                  <span>First page: {ent.first_appeared_page}</span>
                  <span>Mentions: {ent.mention_count}</span>
                </div>
              </div>
            ))
          )}
        </div>
      ) : (
        /* Timeline Events View */
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {timeline.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center text-slate-500">
              <Calendar className="w-8 h-8 text-slate-600 mb-2" />
              <p className="text-xs font-medium">No narrative events recorded</p>
            </div>
          ) : (
            timeline.map((ev) => (
              <div
                key={ev.id}
                onClick={() => setCurrentPage(ev.page_number)}
                className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 hover:border-amber-500/50 transition-all cursor-pointer space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-100">{ev.title}</span>
                  <button className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-indigo-300 text-[10px] font-bold">
                    Page {ev.page_number}
                  </button>
                </div>
                {ev.description && (
                  <p className="text-xs text-slate-400 leading-relaxed">{ev.description}</p>
                )}
                {ev.participants && ev.participants.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {ev.participants.map((p, idx) => (
                      <span
                        key={idx}
                        className="px-1.5 py-0.5 text-[9px] rounded bg-slate-900 text-slate-300 border border-slate-800"
                      >
                        {p}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* Footer Interactive AI Prompt Bar */}
      <div className="p-3 border-t border-slate-800 bg-slate-950/80 space-y-2">
        {aiResponse && (
          <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-xs text-slate-200 space-y-2 max-h-48 overflow-y-auto">
            <div className="flex items-center justify-between font-bold text-indigo-300">
              <span className="flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5" />
                <span>Narrative AI Grounded Answer</span>
              </span>
              <button
                onClick={() => setAiResponse(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
            <p className="leading-relaxed whitespace-pre-wrap">{aiResponse.answer}</p>
          </div>
        )}

        <form onSubmit={handleAskAi} className="flex gap-2">
          <input
            type="text"
            value={aiQuestion}
            onChange={(e) => setAiQuestion(e.target.value)}
            placeholder={
              selectedEntity
                ? `Ask AI about ${selectedEntity.name}...`
                : 'Ask AI about character relationships or events...'
            }
            className="flex-1 px-3 py-2 text-xs bg-slate-900 border border-slate-800 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            disabled={isAskingAi || !aiQuestion.trim()}
            className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors"
          >
            {isAskingAi ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
