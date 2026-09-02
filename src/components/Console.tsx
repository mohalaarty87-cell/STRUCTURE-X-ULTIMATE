import React, { useState, useRef, useEffect } from 'react';
import { ConsoleMessage, StructuralModel, LayerVisibilityState, DisplayMode, CameraPreset } from '../types/structure';
import { Terminal, Send, Trash2, ChevronUp, ChevronDown, CheckCircle, AlertTriangle, Info, Maximize2, Minimize2 } from 'lucide-react';

interface ConsoleProps {
  messages: ConsoleMessage[];
  onSendMessage: (msg: ConsoleMessage) => void;
  onClearMessages: () => void;
  onExecuteCommand?: (cmd: string) => void;
  isOpen: boolean;
  onToggleOpen: () => void;
  lang?: 'en' | 'ar';
}

export const Console: React.FC<ConsoleProps> = ({
  messages,
  onSendMessage,
  onClearMessages,
  onExecuteCommand,
  isOpen,
  onToggleOpen,
  lang = 'en'
}) => {
  const [commandInput, setCommandInput] = useState('');
  const [historyIndex, setHistoryIndex] = useState<number>(-1);
  const [commandHistory, setCommandHistory] = useState<string[]>([
    'zoom extents',
    'select C1',
    'display extruded',
    'view 3d'
  ]);
  const [isExpanded, setIsExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'console' | 'diagnostics' | 'health'>('console');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isOpen]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = commandInput.trim();
    if (!trimmed) return;

    // Log the user command
    const cmdMsg: ConsoleMessage = {
      id: `cmd-${Date.now()}`,
      timestamp: new Date().toLocaleTimeString(),
      type: 'command',
      text: `> ${trimmed}`,
      source: 'USER'
    };
    onSendMessage(cmdMsg);

    // Save to history
    setCommandHistory(prev => [...prev, trimmed]);
    setHistoryIndex(-1);

    // Execute through parent command processor
    if (onExecuteCommand) {
      onExecuteCommand(trimmed);
    }

    setCommandInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (commandHistory.length === 0) return;
      const nextIdx = historyIndex === -1 ? commandHistory.length - 1 : Math.max(0, historyIndex - 1);
      setHistoryIndex(nextIdx);
      setCommandInput(commandHistory[nextIdx]);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (historyIndex === -1) return;
      const nextIdx = historyIndex + 1;
      if (nextIdx >= commandHistory.length) {
        setHistoryIndex(-1);
        setCommandInput('');
      } else {
        setHistoryIndex(nextIdx);
        setCommandInput(commandHistory[nextIdx]);
      }
    }
  };

  if (!isOpen) {
    return (
      <div className="fixed bottom-[24px] left-[260px] z-40">
        <button
          onClick={onToggleOpen}
          className="flex items-center space-x-1.5 rtl:space-x-reverse px-2.5 py-1 bg-[#1e2022] hover:bg-[#282a2c] text-[#c1c7d0] hover:text-[#96ccff] border-t border-r border-[#41474f] rounded-tr text-[11px] font-mono shadow-lg transition-colors cursor-pointer"
        >
          <Terminal className="w-3.5 h-3.5 text-[#96ccff]" />
          <span>{lang === 'ar' ? 'وحدة التحكم والأوامر' : 'Console & CLI'}</span>
          <ChevronUp className="w-3 h-3 text-[#8b919a]" />
        </button>
      </div>
    );
  }

  return (
    <div
      className={`fixed bottom-[24px] left-[260px] right-[280px] z-40 bg-[#121416]/95 backdrop-blur-md border-t border-x border-[#41474f] shadow-2xl flex flex-col transition-all duration-200 font-mono text-[11px] ${
        isExpanded ? 'h-[320px]' : 'h-[160px]'
      }`}
    >
      {/* Console Header Bar */}
      <div className="h-[28px] bg-[#1a1c1e] border-b border-[#282a2c] px-3 flex items-center justify-between select-none">
        <div className="flex items-center space-x-2 rtl:space-x-reverse">
          <Terminal className="w-3.5 h-3.5 text-[#96ccff]" />
          <div className="flex space-x-1 rtl:space-x-reverse">
            <button
              onClick={() => setActiveTab('console')}
              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase transition-colors cursor-pointer ${
                activeTab === 'console' ? 'bg-[#96ccff]/20 text-[#96ccff] border border-[#96ccff]/30' : 'text-[#8b919a] hover:text-[#e2e2e5]'
              }`}
            >
              {lang === 'ar' ? 'موجه الأوامر' : 'CLI Prompt'}
            </button>
            <button
              onClick={() => setActiveTab('diagnostics')}
              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase transition-colors cursor-pointer ${
                activeTab === 'diagnostics' ? 'bg-[#7ed99e]/20 text-[#7ed99e] border border-[#7ed99e]/30' : 'text-[#8b919a] hover:text-[#e2e2e5]'
              }`}
            >
              {lang === 'ar' ? 'تشخيص المحرك' : 'Diagnostics'}
            </button>
            <button
              onClick={() => setActiveTab('health')}
              className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase transition-colors cursor-pointer ${
                activeTab === 'health' ? 'bg-[#ffad68]/20 text-[#ffad68] border border-[#ffad68]/30' : 'text-[#8b919a] hover:text-[#e2e2e5]'
              }`}
            >
              {lang === 'ar' ? 'سجل التدقيق' : 'Audit Logs'}
            </button>
          </div>
        </div>

        {/* Right Action Tools */}
        <div className="flex items-center space-x-2 rtl:space-x-reverse">
          <button
            onClick={onClearMessages}
            className="p-1 text-[#8b919a] hover:text-[#ff7070] transition-colors cursor-pointer"
            title="Clear Console Output"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1 text-[#8b919a] hover:text-[#e2e2e5] transition-colors cursor-pointer"
            title={isExpanded ? 'Minimize' : 'Maximize'}
          >
            {isExpanded ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={onToggleOpen}
            className="p-1 text-[#8b919a] hover:text-[#e2e2e5] transition-colors cursor-pointer"
            title="Close Console"
          >
            <ChevronDown className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Console Output Body */}
      <div ref={scrollRef} className="flex-1 p-2 overflow-y-auto space-y-1 bg-[#0c0e10]/80">
        {messages.length === 0 ? (
          <div className="text-[#60656c] text-[10px] italic py-2 px-1">
            STRUCTURE-X Command Prompt v4.2 Ready. Type 'help' to see all available CAD and viewport commands.
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} className="flex items-start space-x-2 rtl:space-x-reverse leading-tight">
              <span className="text-[#555a60] text-[10px] shrink-0 select-none">[{msg.timestamp}]</span>
              {msg.type === 'command' && (
                <span className="text-[#96ccff] font-bold">{msg.text}</span>
              )}
              {msg.type === 'info' && (
                <span className="text-[#c1c7d0] flex items-center gap-1">
                  <Info className="w-3 h-3 text-[#96ccff] inline shrink-0" />
                  {msg.text}
                </span>
              )}
              {msg.type === 'success' && (
                <span className="text-[#7ed99e] flex items-center gap-1">
                  <CheckCircle className="w-3 h-3 text-[#7ed99e] inline shrink-0" />
                  {msg.text}
                </span>
              )}
              {msg.type === 'warn' && (
                <span className="text-[#ffad68] flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3 text-[#ffad68] inline shrink-0" />
                  {msg.text}
                </span>
              )}
              {msg.type === 'error' && (
                <span className="text-[#ff7070] flex items-center gap-1 font-bold">
                  {msg.text}
                </span>
              )}
            </div>
          ))
        )}
      </div>

      {/* CLI Input Prompt Bar */}
      <form onSubmit={handleSubmit} className="h-[28px] border-t border-[#282a2c] bg-[#16181a] flex items-center px-2">
        <span className="text-[#96ccff] font-bold text-[12px] mr-2 rtl:mr-0 rtl:ml-2 select-none">❯</span>
        <input
          type="text"
          value={commandInput}
          onChange={(e) => setCommandInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Enter command (e.g. 'select C1', 'fit', 'view plan', 'layer grid on', 'help')..."
          className="flex-1 bg-transparent border-none outline-none text-[#e2e2e5] placeholder-[#555a60] text-[11px] font-mono"
        />
        <button
          type="submit"
          className="ml-2 rtl:ml-0 rtl:mr-2 p-1 text-[#96ccff] hover:text-white transition-colors cursor-pointer"
        >
          <Send className="w-3 h-3" />
        </button>
      </form>
    </div>
  );
};
