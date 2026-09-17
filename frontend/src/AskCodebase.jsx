import { useState } from "react";
import {
  MessageSquare,
  Send,
  Sparkles,
  FileCode2,
} from "lucide-react";

export default function AskCodebase() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);

  async function askQuestion() {
    if (!question.trim()) return;

    setLoading(true);
    setAnswer(null);

    try {
      const response = await fetch("/api/ask", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: question.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Ask API is not available yet.");
      }

      setAnswer(data);
    } catch (error) {
      setAnswer({
        answer:
          "RAG integration is not connected yet. we will connect the AI model here.",
        sources: [],
        pending: true,
      });
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      askQuestion();
    }
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">

      {/* Header */}
      <div className="mb-8">

        <div className="flex items-center gap-3">

          <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
            <MessageSquare size={20} className="text-zinc-300" />
          </div>

          <div>
            <h1 className="text-2xl font-semibold">
              Ask Codebase
            </h1>

            <p className="text-sm text-zinc-500 mt-1">
              Ask questions about your repository using code and graph context.
            </p>
          </div>

        </div>

      </div>


      {/* Chat area */}
      <div className="border border-white/10 rounded-2xl bg-[#0d0d0f] min-h-[560px] flex flex-col">

        {/* Empty state */}
        {!answer && !loading && (
          <div className="flex-1 flex items-center justify-center">

            <div className="text-center max-w-md">

              <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/10 flex items-center justify-center mx-auto mb-5">

                <Sparkles
                  size={24}
                  className="text-zinc-400"
                />

              </div>

              <h2 className="text-lg font-medium">
                Understand your codebase
              </h2>

              <p className="text-sm text-zinc-500 mt-2">
                Ask questions about functions, dependencies,
                architecture or how different parts of the code work.
              </p>

              <div className="flex flex-wrap justify-center gap-2 mt-6">

                {[
                  "How does authentication work?",
                  "What calls login()?",
                  "Which functions are risky?",
                ].map((item) => (
                  <button
                    key={item}
                    onClick={() => setQuestion(item)}
                    className="text-xs border border-white/10 bg-white/[0.02] hover:bg-white/5 text-zinc-400 px-3 py-2 rounded-lg"
                  >
                    {item}
                  </button>
                ))}

              </div>

            </div>

          </div>
        )}


        {/* Loading */}
        {loading && (
          <div className="flex-1 flex items-center justify-center">

            <div className="text-center">

              <Sparkles
                size={24}
                className="text-zinc-500 mx-auto mb-3 animate-pulse"
              />

              <p className="text-sm text-zinc-400">
                Analyzing your codebase...
              </p>

            </div>

          </div>
        )}


        {/* Answer */}
        {answer && !loading && (
          <div className="flex-1 p-6 overflow-auto">

            <div className="mb-6">

              <p className="text-xs text-zinc-600 uppercase tracking-wider mb-2">
                You asked
              </p>

              <p className="text-sm text-zinc-300">
                {question}
              </p>

            </div>


            <div className="border border-white/10 rounded-xl bg-white/[0.02] p-5">

              <div className="flex items-center gap-2 mb-4">

                <div className="w-7 h-7 rounded-lg bg-white/10 flex items-center justify-center">
                  <Sparkles size={14} />
                </div>

                <span className="text-sm font-medium">
                  CodeAtlas
                </span>

              </div>

              <p className="text-sm text-zinc-300 leading-7 whitespace-pre-wrap">
                {answer.answer}
              </p>

            </div>


            {answer.sources?.length > 0 && (
              <div className="mt-6">

                <p className="text-xs text-zinc-600 uppercase tracking-wider mb-3">
                  Sources
                </p>

                <div className="space-y-2">

                  {answer.sources.map((source, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-3 border border-white/10 rounded-lg px-3 py-2.5"
                    >

                      <FileCode2
                        size={15}
                        className="text-zinc-500"
                      />

                      <span className="text-sm text-zinc-400">
                        {typeof source === "string"
                          ? source
                          : source.file || source.node_id}
                      </span>

                    </div>
                  ))}

                </div>

              </div>
            )}

          </div>
        )}


        {/* Input */}
        <div className="p-4 border-t border-white/10">

          <div className="flex items-end gap-3 border border-white/10 bg-black/20 rounded-xl p-2">

            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about your codebase..."
              rows={1}
              className="flex-1 resize-none bg-transparent outline-none text-sm text-zinc-300 placeholder:text-zinc-600 px-2 py-2"
            />

            <button
              onClick={askQuestion}
              disabled={!question.trim() || loading}
              className="w-9 h-9 rounded-lg bg-white text-black flex items-center justify-center disabled:opacity-30 hover:bg-zinc-200 transition"
            >
              <Send size={16} />
            </button>

          </div>

          <p className="text-[11px] text-zinc-700 mt-2 px-1">
            Enter to ask · Shift + Enter for new line
          </p>

        </div>

      </div>

    </div>
  );
}