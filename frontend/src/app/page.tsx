import { Suspense } from 'react';
import { checkBackendHealth } from '@/lib/api';

async function BackendStatus() {
  try {
    const health = await checkBackendHealth();
    return (
      <div className="flex items-center gap-2 text-sm">
        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
        <span className="text-green-600 dark:text-green-400">
          Backend Connected
        </span>
        <span className="text-gray-500 text-xs">
          ({health.status})
        </span>
      </div>
    );
  } catch (error) {
    return (
      <div className="flex items-center gap-2 text-sm">
        <div className="w-2 h-2 bg-red-500 rounded-full" />
        <span className="text-red-600 dark:text-red-400">
          Backend Disconnected
        </span>
        <span className="text-gray-500 text-xs">
          (Check if FastAPI is running on port 8000)
        </span>
      </div>
    );
  }
}

export default function Home() {
  return (
    <div className="font-sans min-h-screen p-8 pb-20 sm:p-20">
      <main className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-12">
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent">
            🐘 Elephantasm
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300 mb-4">
            Long-Term Agentic Memory Framework
          </p>
          <Suspense
            fallback={
              <div className="flex items-center gap-2 text-sm">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-pulse" />
                <span className="text-gray-500">Checking backend...</span>
              </div>
            }
          >
            <BackendStatus />
          </Suspense>
        </div>

        {/* Introduction */}
        <section className="mb-12 p-6 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
          <h2 className="text-2xl font-semibold mb-3">What is Elephantasm?</h2>
          <p className="text-gray-700 dark:text-gray-300 mb-4">
            Elephantasm is a modular, open-source framework that gives AI agents
            the ability to <strong>remember, learn, and evolve</strong> over time.
          </p>
          <p className="text-gray-700 dark:text-gray-300">
            Unlike typical memory systems that simply log interactions, Elephantasm
            treats memory as a <strong>living cognitive substrate</strong> — a
            framework for how agents remember, learn, and become.
          </p>
        </section>

        {/* Memory Hierarchy */}
        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-6">Memory Hierarchy</h2>
          <div className="grid gap-4">
            {[
              {
                name: 'Events',
                icon: '⚡',
                description:
                  'Raw interactions and signals (user inputs, tool calls, API responses)',
                color: 'from-blue-500 to-cyan-500',
              },
              {
                name: 'Memories',
                icon: '🧠',
                description:
                  'Structured reflections and encodings of one or more events',
                color: 'from-purple-500 to-pink-500',
              },
              {
                name: 'Lessons',
                icon: '💡',
                description:
                  'Extracted insights and rules from patterns across memories',
                color: 'from-amber-500 to-orange-500',
              },
              {
                name: 'Knowledge',
                icon: '📚',
                description:
                  "Canonicalized truths — the agent's understanding of the world",
                color: 'from-emerald-500 to-teal-500',
              },
              {
                name: 'Identity',
                icon: '🎭',
                description:
                  "The agent's accumulated disposition, tone, and preferences",
                color: 'from-rose-500 to-red-500',
              },
            ].map((layer) => (
              <div
                key={layer.name}
                className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
              >
                <div className="flex items-start gap-3">
                  <div className="text-3xl">{layer.icon}</div>
                  <div className="flex-1">
                    <h3
                      className={`text-lg font-semibold bg-gradient-to-r ${layer.color} bg-clip-text text-transparent mb-1`}
                    >
                      {layer.name}
                    </h3>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {layer.description}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Getting Started */}
        <section className="mb-12">
          <h2 className="text-2xl font-semibold mb-4">Getting Started</h2>
          <div className="space-y-3">
            <div className="flex items-start gap-3 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <span className="font-mono font-semibold text-purple-600 dark:text-purple-400">
                1.
              </span>
              <div>
                <p className="text-gray-700 dark:text-gray-300">
                  Start the FastAPI backend:
                </p>
                <code className="block mt-2 p-2 bg-gray-100 dark:bg-gray-900 rounded text-sm font-mono">
                  cd backend && python3 main.py
                </code>
              </div>
            </div>
            <div className="flex items-start gap-3 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <span className="font-mono font-semibold text-purple-600 dark:text-purple-400">
                2.
              </span>
              <div>
                <p className="text-gray-700 dark:text-gray-300">
                  Install frontend dependencies:
                </p>
                <code className="block mt-2 p-2 bg-gray-100 dark:bg-gray-900 rounded text-sm font-mono">
                  sudo chown -R 501:20 &quot;~/.npm&quot; && npm install --legacy-peer-deps
                </code>
              </div>
            </div>
            <div className="flex items-start gap-3 p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
              <span className="font-mono font-semibold text-purple-600 dark:text-purple-400">
                3.
              </span>
              <div>
                <p className="text-gray-700 dark:text-gray-300">
                  Start the development server:
                </p>
                <code className="block mt-2 p-2 bg-gray-100 dark:bg-gray-900 rounded text-sm font-mono">
                  npm run dev
                </code>
              </div>
            </div>
          </div>
        </section>

        {/* Core Principles */}
        <section className="p-6 bg-gradient-to-br from-purple-50 to-blue-50 dark:from-gray-800 dark:to-gray-900 rounded-lg border border-purple-200 dark:border-purple-900">
          <h2 className="text-2xl font-semibold mb-4">Core Principles</h2>
          <ul className="space-y-2 text-gray-700 dark:text-gray-300">
            <li className="flex items-start gap-2">
              <span className="text-purple-600 dark:text-purple-400">▸</span>
              <span>
                <strong>Continuity + Context</strong> — Not just what the agent
                knows now, but what it has experienced before
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-purple-600 dark:text-purple-400">▸</span>
              <span>
                <strong>Structure + Similarity</strong> — Hybrid retrieval with
                both semantic and relational intelligence
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-purple-600 dark:text-purple-400">▸</span>
              <span>
                <strong>Accumulate, then Curate</strong> — Record everything
                first, refine reflectively through the Dreamer
              </span>
            </li>
            <li className="flex items-start gap-2">
              <span className="text-purple-600 dark:text-purple-400">▸</span>
              <span>
                <strong>Identity as Emergence</strong> — Who the agent becomes
                through accumulated experience
              </span>
            </li>
          </ul>
        </section>
      </main>
    </div>
  );
}
