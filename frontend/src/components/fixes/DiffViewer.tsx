import React, { useState, useMemo } from 'react';

interface DiffLine {
  type: 'add' | 'del' | 'hunk' | 'normal';
  oldLineNumber?: number;
  newLineNumber?: number;
  content: string;
}

interface DiffHunk {
  header: string;
  lines: DiffLine[];
}

interface DiffViewerProps {
  patch: string;
  filePath: string;
  explanation?: string;
}

export const parseUnifiedDiff = (rawPatch: string): DiffHunk[] => {
  if (!rawPatch) return [];

  const lines = rawPatch.split('\n');
  const hunks: DiffHunk[] = [];
  let currentHunk: DiffHunk | null = null;

  let oldCounter = 0;
  let newCounter = 0;

  for (const line of lines) {
    if (line.startsWith('@@')) {
      const match = /@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/.exec(line);
      if (match) {
        oldCounter = parseInt(match[1], 10);
        newCounter = parseInt(match[2], 10);
      }
      currentHunk = {
        header: line,
        lines: [
          {
            type: 'hunk',
            content: line,
          },
        ],
      };
      hunks.push(currentHunk);
      continue;
    }

    if (!currentHunk) continue;

    if (line.startsWith('+') && !line.startsWith('+++')) {
      currentHunk.lines.push({
        type: 'add',
        newLineNumber: newCounter++,
        content: line.slice(1),
      });
    } else if (line.startsWith('-') && !line.startsWith('---')) {
      currentHunk.lines.push({
        type: 'del',
        oldLineNumber: oldCounter++,
        content: line.slice(1),
      });
    } else if (!line.startsWith('---') && !line.startsWith('+++')) {
      currentHunk.lines.push({
        type: 'normal',
        oldLineNumber: oldCounter++,
        newLineNumber: newCounter++,
        content: line.startsWith(' ') ? line.slice(1) : line,
      });
    }
  }

  return hunks;
};

export const DiffViewer: React.FC<DiffViewerProps> = ({
  patch,
  filePath,
  explanation,
}) => {
  const [viewMode, setViewMode] = useState<'unified' | 'split'>('unified');

  const hunks = useMemo(() => parseUnifiedDiff(patch), [patch]);

  return (
    <div className="space-y-3 font-mono text-xs">
      {/* Header controls bar */}
      <div className="flex items-center justify-between bg-slate-950 px-4 py-2.5 border border-slate-800 rounded-t-lg">
        <div className="flex items-center space-x-2 truncate">
          <span className="text-slate-500">File:</span>
          <span className="font-semibold text-slate-200 truncate">{filePath}</span>
        </div>

        <div className="flex items-center space-x-2">
          <div className="flex bg-slate-900 border border-slate-800 rounded p-0.5">
            <button
              onClick={() => setViewMode('unified')}
              className={`px-2.5 py-1 text-xs rounded font-sans transition-colors ${
                viewMode === 'unified'
                  ? 'bg-purple-600 text-white font-medium'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Unified
            </button>
            <button
              onClick={() => setViewMode('split')}
              className={`px-2.5 py-1 text-xs rounded font-sans transition-colors ${
                viewMode === 'split'
                  ? 'bg-purple-600 text-white font-medium'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Split View
            </button>
          </div>
        </div>
      </div>

      {explanation && (
        <div className="bg-purple-950/20 border border-purple-800/30 text-purple-300 p-3 rounded-lg font-sans text-xs flex items-start space-x-2">
          <span className="text-base">💡</span>
          <span className="leading-relaxed">{explanation}</span>
        </div>
      )}

      {/* Diff Table View */}
      <div className="bg-slate-950 border border-slate-800 rounded-b-lg overflow-x-auto max-h-96">
        {viewMode === 'unified' ? (
          <table className="w-full text-left border-collapse font-mono">
            <tbody>
              {hunks.map((hunk, hIdx) => (
                <React.Fragment key={hIdx}>
                  {hunk.lines.map((line, lIdx) => {
                    if (line.type === 'hunk') {
                      return (
                        <tr key={lIdx} className="bg-purple-950/40 text-purple-300 border-y border-purple-900/40">
                          <td colSpan={3} className="px-4 py-1.5 font-bold text-xs select-none">
                            {line.content}
                          </td>
                        </tr>
                      );
                    }

                    const isAdd = line.type === 'add';
                    const isDel = line.type === 'del';

                    return (
                      <tr
                        key={lIdx}
                        className={`${
                          isAdd
                            ? 'bg-emerald-950/40 text-emerald-300'
                            : isDel
                            ? 'bg-rose-950/40 text-rose-300'
                            : 'text-slate-400 hover:bg-slate-900/40'
                        }`}
                      >
                        <td className="w-12 py-0.5 px-2 text-right text-slate-600 select-none border-r border-slate-900">
                          {line.oldLineNumber || ''}
                        </td>
                        <td className="w-12 py-0.5 px-2 text-right text-slate-600 select-none border-r border-slate-900">
                          {line.newLineNumber || ''}
                        </td>
                        <td className="py-0.5 px-3 whitespace-pre">
                          <span className="select-none mr-2 font-bold">
                            {isAdd ? '+' : isDel ? '-' : ' '}
                          </span>
                          {line.content}
                        </td>
                      </tr>
                    );
                  })}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        ) : (
          /* Split View Mode */
          <table className="w-full text-left border-collapse font-mono">
            <tbody>
              {hunks.map((hunk, hIdx) => (
                <React.Fragment key={hIdx}>
                  {hunk.lines.map((line, lIdx) => {
                    if (line.type === 'hunk') {
                      return (
                        <tr key={lIdx} className="bg-purple-950/40 text-purple-300 border-y border-purple-900/40">
                          <td colSpan={4} className="px-4 py-1.5 font-bold text-xs select-none">
                            {line.content}
                          </td>
                        </tr>
                      );
                    }

                    if (line.type === 'del') {
                      return (
                        <tr key={lIdx} className="bg-rose-950/40 text-rose-300">
                          <td className="w-12 py-0.5 px-2 text-right text-slate-600 select-none border-r border-slate-900">
                            {line.oldLineNumber}
                          </td>
                          <td className="w-1/2 py-0.5 px-3 whitespace-pre border-r border-slate-900">
                            <span className="select-none mr-2 font-bold">-</span>
                            {line.content}
                          </td>
                          <td className="w-12 py-0.5 px-2 text-right text-slate-600 select-none border-r border-slate-900 bg-slate-950"></td>
                          <td className="w-1/2 py-0.5 px-3 whitespace-pre bg-slate-950"></td>
                        </tr>
                      );
                    }

                    if (line.type === 'add') {
                      return (
                        <tr key={lIdx} className="bg-emerald-950/40 text-emerald-300">
                          <td className="w-12 py-0.5 px-2 text-right text-slate-600 select-none border-r border-slate-900 bg-slate-950"></td>
                          <td className="w-1/2 py-0.5 px-3 whitespace-pre border-r border-slate-900 bg-slate-950"></td>
                          <td className="w-12 py-0.5 px-2 text-right text-slate-600 select-none border-r border-slate-900">
                            {line.newLineNumber}
                          </td>
                          <td className="w-1/2 py-0.5 px-3 whitespace-pre">
                            <span className="select-none mr-2 font-bold">+</span>
                            {line.content}
                          </td>
                        </tr>
                      );
                    }

                    return (
                      <tr key={lIdx} className="text-slate-400 hover:bg-slate-900/40">
                        <td className="w-12 py-0.5 px-2 text-right text-slate-600 select-none border-r border-slate-900">
                          {line.oldLineNumber}
                        </td>
                        <td className="w-1/2 py-0.5 px-3 whitespace-pre border-r border-slate-900">
                          {line.content}
                        </td>
                        <td className="w-12 py-0.5 px-2 text-right text-slate-600 select-none border-r border-slate-900">
                          {line.newLineNumber}
                        </td>
                        <td className="w-1/2 py-0.5 px-3 whitespace-pre">
                          {line.content}
                        </td>
                      </tr>
                    );
                  })}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
