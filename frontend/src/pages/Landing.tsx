import { useEffect, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ACCESS_TOKEN_KEY } from '../lib/api';

const steps = [
  {
    number: '01',
    title: 'Connect your data',
    description: 'Bring a SQLite database or turn one or more CSV files into a queryable dataset.',
    icon: '▤',
  },
  {
    number: '02',
    title: 'Ask in plain English',
    description: 'Describe what you need. The router checks uncertainty and chooses a model path.',
    icon: '✳',
  },
  {
    number: '03',
    title: 'Review, then run',
    description: 'Inspect generated SQL, confirm the read-only query, and explore the result.',
    icon: '⌁',
  },
];

const capabilities = [
  {
    icon: '⌘',
    title: 'Understand the dataset',
    description: 'Inspect tables, column types, missing values, ranges, and sample records before asking.',
    tone: 'violet',
  },
  {
    icon: '▱',
    title: 'Keep SQL in view',
    description: 'Review the generated statement first. Queries run in read-only mode only after confirmation.',
    tone: 'cyan',
  },
  {
    icon: '▥',
    title: 'Explore the answer',
    description: 'Read result tables, download data, and visualize suitable numeric results.',
    tone: 'teal',
  },
  {
    icon: '◎',
    title: 'Measure the system',
    description: 'Compare saved benchmark outcomes and use answer feedback to build an evaluation set.',
    tone: 'amber',
  },
];

export default function Landing() {
  const pageRef = useRef<HTMLElement>(null);
  const navigate = useNavigate();
  const hasSession = Boolean(localStorage.getItem(ACCESS_TOKEN_KEY));

  useEffect(() => {
    if (
      !pageRef.current ||
      !('IntersectionObserver' in window) ||
      window.matchMedia('(prefers-reduced-motion: reduce)').matches
    ) {
      return;
    }

    const elements = pageRef.current.querySelectorAll<HTMLElement>('[data-scroll-reveal]');
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -5% 0px' },
    );

    elements.forEach((element) => {
      element.classList.add('landing-reveal');
      observer.observe(element);
    });

    return () => observer.disconnect();
  }, []);

  return (
    <main ref={pageRef} className="landing-page mx-auto max-w-7xl space-y-24 px-6 pb-24 pt-10 sm:pt-16">
      <section data-scroll-reveal className="landing-hero relative grid items-center gap-12 overflow-hidden rounded-[2rem] border border-white/10 px-6 py-14 sm:px-12 lg:grid-cols-[1.1fr_0.9fr] lg:px-16 lg:py-20">
        <div className="relative z-10 space-y-7">
          <div className="landing-eyebrow inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em]">
            <span className="h-2 w-2 rounded-full bg-cyan-300 shadow-[0_0_12px_#67e8f9]" />
            Deep learning · Text to SQL
          </div>
          <div className="space-y-4">
            <h1 className="max-w-3xl text-5xl font-bold leading-[1.02] tracking-tight text-white sm:text-6xl lg:text-7xl">
              Ask your data
              <span className="landing-headline block">a better question.</span>
            </h1>
            <p className="max-w-xl text-base leading-7 text-slate-300 sm:text-lg">
              SQL Router translates everyday language into SQL, then uses uncertainty-aware model routing
              to balance local inference with a stronger API model.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => navigate(hasSession ? '/playground' : '/login')}
              className="btn-primary landing-cta inline-flex items-center gap-2"
            >
              {hasSession ? 'Open playground' : 'Get started'} <span aria-hidden="true">→</span>
            </button>
            <a href="#how-it-works" className="btn-secondary inline-flex items-center gap-2">
              Explore the workflow <span aria-hidden="true">↓</span>
            </a>
          </div>
          <div className="flex flex-wrap gap-x-6 gap-y-2 pt-2 text-xs font-medium text-slate-400 sm:text-sm">
            <span>01 / Natural language</span>
            <span>02 / Uncertainty-aware routing</span>
            <span>03 / Read-only SQL</span>
          </div>
        </div>

        <div className="landing-visual relative mx-auto flex h-[310px] w-full max-w-[430px] items-center justify-center sm:h-[390px]" aria-label="Illustration of the SQL Router workflow" role="img">
          <div className="landing-orbit landing-orbit-one" />
          <div className="landing-orbit landing-orbit-two" />
          <div className="landing-data-card landing-card-back">
            <span className="landing-card-dot" />
            <span className="landing-card-line w-2/3" />
            <span className="landing-card-line w-1/2" />
            <div className="landing-card-bars"><i /><i /><i /><i /><i /></div>
          </div>
          <div className="landing-data-card landing-card-front">
            <div className="mb-5 flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300">QUERY ROUTER</span>
              <span className="rounded-full bg-emerald-400/10 px-2 py-1 text-[10px] text-emerald-200">READY</span>
            </div>
            <div className="landing-query-chip">“Show monthly sales”</div>
            <div className="landing-sql-line"><span>SELECT</span> month, SUM(sales)</div>
            <div className="landing-sql-line"><span>FROM</span> orders</div>
            <div className="landing-route-pills">
              <span>◈ Local model</span><b>→</b><span>✓ Review SQL</span>
            </div>
          </div>
          <div className="landing-float-label landing-float-top">Intent → SQL</div>
          <div className="landing-float-label landing-float-bottom">Uncertainty probe</div>
        </div>
      </section>

      <section data-scroll-reveal className="landing-purpose grid gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-end">
        <div>
          <p className="landing-eyebrow-text text-xs font-semibold uppercase tracking-[0.2em]">The project</p>
          <h2 className="mt-3 text-3xl font-bold tracking-tight text-white sm:text-4xl">A smarter path from question to query.</h2>
        </div>
        <p className="max-w-3xl text-base leading-7 text-slate-300">
          Text-to-SQL models can make mistakes—and sending every request to a large API can add latency and cost.
          This project explores a middle ground: a fine-tuned local model handles suitable questions, while a
          learned uncertainty probe can route harder cases to a more capable model. Generated SQL stays visible
          for review, and database queries run read-only.
        </p>
      </section>

      <section id="how-it-works" data-scroll-reveal className="space-y-8 scroll-mt-32">
        <div className="max-w-2xl space-y-3">
          <p className="landing-eyebrow-text text-xs font-semibold uppercase tracking-[0.2em]">How it works</p>
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">Three steps. One transparent workflow.</h2>
        </div>
        <div className="grid gap-5 md:grid-cols-3">
          {steps.map((step) => (
            <article key={step.number} data-scroll-reveal className="landing-step-card glass card-3d rounded-2xl p-6 sm:p-7">
              <div className="flex items-center justify-between">
                <span className="landing-step-icon">{step.icon}</span>
                <span className="text-xs font-semibold tracking-[0.2em] text-slate-500">{step.number}</span>
              </div>
              <h3 className="mt-6 text-xl font-semibold text-white">{step.title}</h3>
              <p className="mt-3 text-sm leading-6 text-slate-400">{step.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section data-scroll-reveal className="landing-router-section grid gap-8 overflow-hidden rounded-3xl border border-white/10 p-6 sm:p-10 lg:grid-cols-[0.78fr_1.22fr] lg:items-center">
        <div className="space-y-4">
          <p className="landing-eyebrow-text text-xs font-semibold uppercase tracking-[0.2em]">The routing idea</p>
          <h2 className="text-3xl font-bold leading-tight text-white sm:text-4xl">Use the right model for the question.</h2>
          <p className="text-sm leading-7 text-slate-300">
            A probe estimates uncertainty from the local model’s generation. The configured threshold helps
            decide whether the local answer is suitable or the request should escalate to the API model.
            The decision and generated SQL remain visible in the workspace.
          </p>
        </div>
        <div className="landing-routing-diagram grid gap-3 sm:grid-cols-3">
          <article data-scroll-reveal className="landing-route-card landing-route-local">
            <span className="landing-route-number">01</span>
            <span className="landing-route-icon">◈</span>
            <h3>Local model</h3>
            <p>Efficient first path for questions the router considers suitable.</p>
          </article>
          <article data-scroll-reveal className="landing-route-card landing-route-probe">
            <span className="landing-route-number">02</span>
            <span className="landing-route-icon">⌁</span>
            <h3>Uncertainty probe</h3>
            <p>Compares the estimated uncertainty with the routing threshold.</p>
          </article>
          <article data-scroll-reveal className="landing-route-card landing-route-api">
            <span className="landing-route-number">03</span>
            <span className="landing-route-icon">↗</span>
            <h3>API escalation</h3>
            <p>Uses the stronger configured model when uncertainty is above threshold.</p>
          </article>
        </div>
      </section>

      <section data-scroll-reveal className="space-y-8">
        <div className="max-w-2xl space-y-3">
          <p className="landing-eyebrow-text text-xs font-semibold uppercase tracking-[0.2em]">More than text-to-SQL</p>
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">Designed to make data work feel clear.</h2>
          <p className="text-sm leading-6 text-slate-400">
            From understanding a new dataset to evaluating model behavior, the tools stay connected to the same workflow.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {capabilities.map((capability, index) => (
            <article key={capability.title} data-scroll-reveal className={`landing-capability-card landing-capability-${capability.tone} card-3d rounded-2xl border p-5 sm:p-6`}>
              <div className="flex items-center justify-between">
                <span className="landing-capability-icon">{capability.icon}</span>
                <span className="text-[10px] font-semibold tracking-[0.18em] text-slate-500">0{index + 1}</span>
              </div>
              <h3 className="mt-5 text-lg font-semibold text-white">{capability.title}</h3>
              <p className="mt-2 text-sm leading-6 text-slate-400">{capability.description}</p>
            </article>
          ))}
        </div>
      </section>

      <section data-scroll-reveal className="landing-audience grid gap-8 lg:grid-cols-[1fr_1fr]">
        <div className="landing-audience-copy rounded-3xl border border-white/10 p-7 sm:p-9">
          <p className="landing-eyebrow-text text-xs font-semibold uppercase tracking-[0.2em]">Who it is for</p>
          <h2 className="mt-3 text-3xl font-bold text-white">A hands-on lab for data and AI.</h2>
          <p className="mt-4 text-sm leading-7 text-slate-300">
            Explore how language models translate questions into database queries, how model confidence can
            guide routing, and how to make the result inspectable. It is built for project demos, learning,
            and experimentation with your own tabular data.
          </p>
        </div>
        <div className="landing-principles grid gap-3 sm:grid-cols-2">
          {[
            ['Transparent', 'See the SQL and the route.'],
            ['Dataset-aware', 'Use your own structured data.'],
            ['Reviewable', 'Confirm before read-only execution.'],
            ['Measurable', 'Track benchmark and user feedback.'],
          ].map(([title, description], index) => (
            <div key={title} data-scroll-reveal className="landing-principle-card card-3d rounded-2xl border border-white/10 p-5">
              <span className="text-xs font-semibold tracking-[0.2em] text-violet-300">0{index + 1}</span>
              <h3 className="mt-3 font-semibold text-white">{title}</h3>
              <p className="mt-1 text-sm text-slate-400">{description}</p>
            </div>
          ))}
        </div>
      </section>

      <section data-scroll-reveal className="landing-quote-panel relative overflow-hidden rounded-3xl border border-white/10 px-7 py-10 sm:px-12 sm:py-14">
        <span className="landing-quote-mark" aria-hidden="true">“</span>
        <div className="relative max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-200">A guiding idea</p>
          <blockquote className="mt-4 text-2xl font-medium leading-snug text-white sm:text-3xl">
            The best interface to data is a question. The best answer is one you can inspect.
          </blockquote>
          <p className="mt-5 text-sm text-slate-400">An original project principle · SQL Router</p>
        </div>
      </section>

      <section data-scroll-reveal className="landing-bottom-cta flex flex-col justify-between gap-6 rounded-3xl border border-white/10 p-7 sm:flex-row sm:items-center sm:p-10">
        <div>
          <p className="landing-eyebrow-text text-xs font-semibold uppercase tracking-[0.2em]">Ready to explore?</p>
          <h2 className="mt-2 text-2xl font-bold text-white sm:text-3xl">Bring a dataset. Start with a question.</h2>
        </div>
        <Link to={hasSession ? '/playground' : '/login'} className="btn-primary inline-flex shrink-0 items-center justify-center gap-2">
          {hasSession ? 'Go to playground' : 'Sign in to continue'} <span aria-hidden="true">→</span>
        </Link>
      </section>
    </main>
  );
}
