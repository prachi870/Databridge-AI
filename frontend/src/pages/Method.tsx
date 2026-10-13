export default function Method() {
  const sections = [
    {
      title: 'System Architecture',
      icon: '🏗️',
      color: 'from-blue-600 to-cyan-600',
      content: (
        <>
          <p className="text-gray-300 mb-6">
            The SQL Router uses a two-tier architecture that intelligently routes natural language
            queries between a local fine-tuned model and a more expensive API-based model.
          </p>
          
          <div className="glass rounded-2xl p-8 space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-center">
              <div className="space-y-2">
                <div className="text-5xl mb-3">📝</div>
                <div className="font-semibold text-purple-300">User Query</div>
                <div className="text-sm text-gray-400">Natural language</div>
              </div>
              <div className="flex items-center justify-center text-4xl text-gray-400">→</div>
              <div className="space-y-2">
                <div className="text-5xl mb-3">🎯</div>
                <div className="font-semibold text-purple-300">Router</div>
                <div className="text-sm text-gray-400">Confidence check</div>
              </div>
            </div>
            <div className="flex items-center justify-center text-4xl text-gray-400">↓</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="glass rounded-xl p-6 text-center space-y-2">
                <div className="text-4xl mb-2">💻</div>
                <div className="font-semibold text-green-400">Local Model</div>
                <div className="text-xs text-gray-400">Fast & cheap</div>
              </div>
              <div className="glass rounded-xl p-6 text-center space-y-2">
                <div className="text-4xl mb-2">☁️</div>
                <div className="font-semibold text-orange-400">API Model</div>
                <div className="text-xs text-gray-400">Powerful & accurate</div>
              </div>
            </div>
          </div>
        </>
      )
    },
    {
      title: 'QLoRA Fine-Tuning',
      icon: '⚡',
      color: 'from-green-600 to-emerald-600',
      content: (
        <>
          <p className="text-gray-300 mb-6">
            We fine-tune a small local model using <strong className="text-green-400">QLoRA (Quantized Low-Rank Adaptation)</strong> on
            natural language to SQL examples.
          </p>
          
          <div className="glass rounded-2xl p-6 border-l-4 border-green-500 space-y-3">
            <div className="font-semibold text-green-400 text-lg mb-3">Key Benefits:</div>
            <ul className="space-y-2 text-gray-300">
              <li className="flex items-start gap-3">
                <span className="text-green-400">✓</span>
                <span>Efficient training with 4-bit quantization</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-400">✓</span>
                <span>Low-rank adapters reduce parameter count</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-400">✓</span>
                <span>Can run on consumer GPUs</span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-green-400">✓</span>
                <span>Fast inference for simple queries</span>
              </li>
            </ul>
          </div>
        </>
      )
    },
    {
      title: 'Execution-Entropy Probes',
      icon: '🔬',
      color: 'from-purple-600 to-pink-600',
      content: (
        <>
          <p className="text-gray-300 mb-6">
            To determine when the local model is confident, we train <strong className="text-purple-400">probe classifiers</strong> that
            analyze the model's internal states during SQL generation.
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="glass rounded-2xl p-6 space-y-3">
              <div className="font-semibold text-purple-400 mb-3">📊 Features Extracted:</div>
              <ul className="space-y-2 text-sm text-gray-300">
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                  Token-level entropy
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                  Hidden state activations
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                  Attention patterns
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                  Layer-wise representations
                </li>
              </ul>
            </div>
            
            <div className="glass rounded-2xl p-6 space-y-3">
              <div className="font-semibold text-pink-400 mb-3">🎯 Probe Training:</div>
              <ul className="space-y-2 text-sm text-gray-300">
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-pink-500"></div>
                  Logistic regression classifier
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-pink-500"></div>
                  Trained to predict correctness
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-pink-500"></div>
                  Calibrated confidence scores
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-pink-500"></div>
                  Fast inference (ms-level)
                </li>
              </ul>
            </div>
          </div>
        </>
      )
    },
    {
      title: 'Routing Decision',
      icon: '🧠',
      color: 'from-orange-600 to-red-600',
      content: (
        <>
          <p className="text-gray-300 mb-6">
            At inference time, the router uses the probe's confidence score to make a routing decision:
          </p>
          
          <div className="glass rounded-2xl p-6 font-mono text-sm space-y-2 mb-6 border border-orange-500/20">
            <div className="text-green-400 mb-3">// Pseudocode</div>
            <div className="text-blue-400">if <span className="text-white">confidence</span> &gt; <span className="text-yellow-400">threshold</span>:</div>
            <div className="ml-6 text-purple-400">return <span className="text-green-400">local_model_result</span></div>
            <div className="text-blue-400">else:</div>
            <div className="ml-6 text-purple-400">return <span className="text-orange-400">api_model_result</span></div>
          </div>
          
          <div className="glass rounded-2xl p-6 border-l-4 border-yellow-500 space-y-3">
            <div className="font-semibold text-yellow-400 text-lg mb-3">⚖️ Trade-offs:</div>
            <div className="space-y-3 text-gray-300">
              <div className="flex items-start gap-3">
                <span className="text-yellow-400 font-bold">↑</span>
                <div>
                  <strong className="text-yellow-400">Higher threshold:</strong>
                  <span className="text-sm text-gray-400 block">More API calls, higher accuracy, higher cost</span>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-yellow-400 font-bold">↓</span>
                <div>
                  <strong className="text-yellow-400">Lower threshold:</strong>
                  <span className="text-sm text-gray-400 block">More local calls, lower cost, may reduce accuracy</span>
                </div>
              </div>
            </div>
          </div>
        </>
      )
    }
  ];

  return (
    <main className="mx-auto max-w-5xl px-6 py-10 space-y-8">
      {/* Hero Section */}
      <div className="text-center space-y-4 mb-12">
        <div className="inline-block">
          <h1 className="text-6xl font-bold mb-2">
            <span className="gradient-text">Method</span>
            <span className="text-white"> Overview</span>
          </h1>
          <div className="h-1 bg-gradient-to-r from-violet-600 via-purple-600 to-pink-600 rounded-full"></div>
        </div>
        <p className="text-xl text-gray-300 max-w-2xl mx-auto">
          How the SQL Router works under the hood 🧠
        </p>
      </div>

      {/* Sections */}
      <div className="space-y-8">
        {sections.map((section, idx) => (
          <div
            key={idx}
            className="glass rounded-3xl p-8 card-3d relative overflow-hidden"
            style={{ animationDelay: `${idx * 100}ms` }}
          >
            {/* Glow effect */}
            <div className={`absolute top-0 right-0 w-64 h-64 bg-gradient-to-br ${section.color} opacity-10 rounded-full blur-3xl`}></div>
            
            {/* Content */}
            <div className="relative z-10 space-y-6">
              <div className="flex items-center gap-4 mb-6">
                <div className={`text-5xl p-4 glass rounded-2xl bg-gradient-to-br ${section.color}`}>
                  {section.icon}
                </div>
                <h2 className={`text-3xl font-bold bg-gradient-to-r ${section.color} bg-clip-text text-transparent`}>
                  {section.title}
                </h2>
              </div>
              
              {section.content}
            </div>
          </div>
        ))}
      </div>

      {/* Performance Stats */}
      <div className="glass rounded-3xl p-8 card-3d">
        <h2 className="text-3xl font-bold gradient-text mb-8">Performance Highlights</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="text-center p-6 glass rounded-2xl">
            <div className="text-5xl font-bold text-green-400 mb-2">60-80%</div>
            <div className="text-sm text-gray-400">Cost Reduction</div>
          </div>
          <div className="text-center p-6 glass rounded-2xl">
            <div className="text-5xl font-bold text-blue-400 mb-2">95%+</div>
            <div className="text-sm text-gray-400">Accuracy Maintained</div>
          </div>
          <div className="text-center p-6 glass rounded-2xl">
            <div className="text-5xl font-bold text-purple-400 mb-2">&lt;50ms</div>
            <div className="text-sm text-gray-400">Routing Overhead</div>
          </div>
        </div>
      </div>
    </main>
  );
}
