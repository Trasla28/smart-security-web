"use client";

import { useRef, useState } from "react";
import { cn } from "@/lib/utils";

export interface MentionUser {
  id: string;
  full_name: string;
}

export interface MentionEntry {
  name: string;
  id: string;
}

interface MentionTextareaProps {
  value: string;
  onChange: (value: string) => void;
  onMentionInsert: (mention: MentionEntry) => void;
  users: MentionUser[];
  placeholder?: string;
  rows?: number;
  className?: string;
  onPaste?: (e: React.ClipboardEvent<HTMLTextAreaElement>) => void;
}

/**
 * El textarea almacena texto limpio: "Hola @Agente TI revisa esto".
 * Al seleccionar del dropdown se inserta "@Nombre " (sin UUID).
 * El padre recibe cada mención vía onMentionInsert y al enviar
 * llama a buildFullBody() para reconstruir el formato backend.
 */
export function MentionTextarea({
  value,
  onChange,
  onMentionInsert,
  users,
  placeholder,
  rows = 3,
  className,
  onPaste,
}: MentionTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [mentionQuery, setMentionQuery] = useState<string | null>(null);
  const [mentionStart, setMentionStart] = useState(0);
  const [selectedIndex, setSelectedIndex] = useState(0);

  const filteredUsers =
    mentionQuery !== null
      ? users
          .filter((u) => u.full_name.toLowerCase().includes(mentionQuery.toLowerCase()))
          .slice(0, 6)
      : [];

  function handleChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    const text = e.target.value;
    onChange(text);

    const cursor = e.target.selectionStart ?? text.length;
    const beforeCursor = text.slice(0, cursor);
    const match = beforeCursor.match(/@([^@\s]*)$/);
    if (match) {
      setMentionQuery(match[1]);
      setMentionStart(cursor - match[0].length);
      setSelectedIndex(0);
    } else {
      setMentionQuery(null);
    }
  }

  function insertMention(user: MentionUser) {
    const cursorPos =
      textareaRef.current?.selectionStart ??
      mentionStart + (mentionQuery?.length ?? 0) + 1;

    const before = value.slice(0, mentionStart);
    const after = value.slice(cursorPos);
    // Inserta solo "@Nombre " — sin UUID, texto completamente limpio
    const displayTag = `@${user.full_name} `;
    onChange(`${before}${displayTag}${after}`);
    onMentionInsert({ name: user.full_name, id: user.id });
    setMentionQuery(null);

    setTimeout(() => {
      if (!textareaRef.current) return;
      const pos = before.length + displayTag.length;
      textareaRef.current.setSelectionRange(pos, pos);
      textareaRef.current.focus();
    }, 0);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (mentionQuery === null || filteredUsers.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, filteredUsers.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" || e.key === "Tab") {
      e.preventDefault();
      insertMention(filteredUsers[selectedIndex]);
    } else if (e.key === "Escape") {
      setMentionQuery(null);
    }
  }

  return (
    <div className="relative">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={handleChange}
        onKeyDown={handleKeyDown}
        onPaste={onPaste}
        rows={rows}
        placeholder={placeholder}
        className={className}
      />

      {mentionQuery !== null && filteredUsers.length > 0 && (
        <div className="absolute z-20 bottom-full mb-1 left-0 bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden w-64">
          <p className="px-3 py-1.5 text-xs text-gray-400 border-b border-gray-100">
            Etiquetar persona
          </p>
          {filteredUsers.map((user, i) => (
            <button
              key={user.id}
              type="button"
              onMouseDown={(e) => {
                e.preventDefault();
                insertMention(user);
              }}
              className={cn(
                "w-full text-left px-3 py-2 text-sm flex items-center gap-2.5 hover:bg-gray-50 transition-colors",
                i === selectedIndex && "bg-blue-50 text-blue-700"
              )}
            >
              <div className="w-7 h-7 rounded-full bg-[#1a2c4e] flex items-center justify-center text-xs font-semibold text-white shrink-0">
                {user.full_name.charAt(0).toUpperCase()}
              </div>
              <span className="truncate">{user.full_name}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Convierte el texto limpio del textarea al formato backend.
 * Ejemplo: "Hola @Agente TI revisa" → "Hola @[Agente TI](uuid) revisa"
 * Las menciones no encontradas en el texto se ignoran sin error.
 */
export function buildFullBody(displayBody: string, mentions: MentionEntry[]): string {
  let body = displayBody;
  for (const m of mentions) {
    body = body.replaceAll(`@${m.name}`, `@[${m.name}](${m.id})`);
  }
  return body;
}

/**
 * Parsea el body guardado en DB (@[Nombre](uuid)) y renderiza
 * las menciones como chips azules en la lista de comentarios.
 */
export function renderMentions(body: string): React.ReactNode {
  const MENTION_RE =
    /@\[([^\]]+)\]\([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\)/g;
  const parts: React.ReactNode[] = [];
  let last = 0;
  let match: RegExpExecArray | null;

  while ((match = MENTION_RE.exec(body)) !== null) {
    if (match.index > last) parts.push(body.slice(last, match.index));
    parts.push(
      <span
        key={match.index}
        className="inline-flex items-center bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-md text-xs font-medium"
      >
        @{match[1]}
      </span>
    );
    last = match.index + match[0].length;
  }

  if (last < body.length) parts.push(body.slice(last));
  return <>{parts}</>;
}
