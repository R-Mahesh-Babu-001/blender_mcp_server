export type ChatMessage = {
  id: string;
  role: "user" | "agent" | "system";
  content: string;
  meta?: string;
  tone?: "default" | "success" | "error";
};

type ChatPanelProps = {
  messages: ChatMessage[];
};

export function ChatPanel({ messages }: ChatPanelProps) {
  return (
    <section className="chat-panel">
      {messages.map((message) => (
        <article key={message.id} className={`chat-row role-${message.role}`}>
          <div className={`chat-bubble tone-${message.tone ?? "default"}`}>
            {message.meta ? <p className="chat-meta">{message.meta}</p> : null}
            <p className="chat-content">{message.content}</p>
          </div>
        </article>
      ))}
    </section>
  );
}
