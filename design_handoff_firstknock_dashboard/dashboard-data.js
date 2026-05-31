// Sample data for the FirstKnock dashboard — modeled on the API_REFERENCE
// shapes. Same data could be fetched from GET /profile, /skills, /graph,
// /analytics. Kept in one file so tile components stay focused on rendering.

const PROFILE = {
  user_id: '01e46dca-8d5a-434f-8550-009a601a8c67',
  name: 'Aswinthraj Devaraj',
  email: 'iamaswinth@gmail.com',
  headline: 'Full Stack AI Engineer',
  location: 'Tirupur, TamilNadu',
  github_url: 'https://github.com/iamaswinth',
  linkedin_url: 'https://www.linkedin.com/in/aswinthraj-d-362a18291/',
  seniority: 'mid',
  total_experience_months: 18,
  github_followers: 12,
  public_repos: 18,
};

// Communities (from GET /graph.communities)
const COMMUNITIES = [
  { id: 1, name: 'Agent stack',     short: 'agents', skills: ['LangGraph', 'Google ADK', 'RAG', 'Gemini Live API', 'Agent State Machines', 'WebRTC'] },
  { id: 2, name: 'Web · React',     short: 'web',    skills: ['React', 'Next.js', 'TypeScript', 'JavaScript', 'Tailwind CSS'] },
  { id: 3, name: 'Data layer',      short: 'data',   skills: ['PostgreSQL', 'Pinecone', 'Neon', 'SQL', 'Pydantic'] },
  { id: 4, name: 'Backend · DevOps', short: 'ops',   skills: ['Python', 'FastAPI', 'Docker', 'GitHub Actions', 'Azure'] },
];

// All skills (from GET /skills). source: 'explicit' | 'inferred'
const SKILLS = [
  // explicit · web
  { name: 'React',           category: 'framework', source: 'explicit', confidence: 1.00, community: 2 },
  { name: 'Next.js',         category: 'framework', source: 'explicit', confidence: 1.00, community: 2 },
  { name: 'TypeScript',      category: 'language',  source: 'explicit', confidence: 1.00, community: 2 },
  { name: 'JavaScript',      category: 'language',  source: 'explicit', confidence: 1.00, community: 2 },
  { name: 'Tailwind CSS',    category: 'framework', source: 'explicit', confidence: 1.00, community: 2 },
  // explicit · agents
  { name: 'LangGraph',       category: 'framework', source: 'explicit', confidence: 1.00, community: 1 },
  { name: 'Google ADK',      category: 'framework', source: 'explicit', confidence: 1.00, community: 1 },
  { name: 'RAG',             category: 'concept',   source: 'explicit', confidence: 1.00, community: 1 },
  { name: 'Gemini Live API', category: 'tool',      source: 'explicit', confidence: 1.00, community: 1 },
  // explicit · backend
  { name: 'Python',          category: 'language',  source: 'explicit', confidence: 1.00, community: 4 },
  { name: 'FastAPI',         category: 'framework', source: 'explicit', confidence: 1.00, community: 4 },
  { name: 'Docker',          category: 'tool',      source: 'explicit', confidence: 1.00, community: 4 },
  { name: 'GitHub Actions',  category: 'tool',      source: 'explicit', confidence: 1.00, community: 4 },
  { name: 'Azure',           category: 'tool',      source: 'explicit', confidence: 1.00, community: 4 },
  // explicit · data
  { name: 'PostgreSQL',      category: 'database',  source: 'explicit', confidence: 1.00, community: 3 },
  { name: 'Pinecone',        category: 'database',  source: 'explicit', confidence: 1.00, community: 3 },
  { name: 'Neon',            category: 'database',  source: 'explicit', confidence: 1.00, community: 3 },
  { name: 'SQL',             category: 'language',  source: 'explicit', confidence: 1.00, community: 3 },
  // inferred (with reasons — these are the headliners)
  { name: 'WebRTC',                 category: 'tool',      source: 'inferred', confidence: 0.85, community: 1, inferred_by: 'llm',
    reason: 'Gemini Live API requires WebRTC for real-time audio streaming.',
    via: ['Gemini Live API'] },
  { name: 'Pydantic',               category: 'framework', source: 'inferred', confidence: 0.92, community: 3, inferred_by: 'graph_implies',
    reason: 'FastAPI is built on Pydantic for request/response validation.',
    via: ['FastAPI'] },
  { name: 'Agent State Machines',   category: 'concept',   source: 'inferred', confidence: 0.90, community: 1, inferred_by: 'graph_implies',
    reason: 'LangGraph models agents as state machines — the core abstraction.',
    via: ['LangGraph'] },
  { name: 'Server-Sent Events',     category: 'tool',      source: 'inferred', confidence: 0.72, community: 4, inferred_by: 'llm',
    reason: 'FastAPI + streaming LLM responses commonly use SSE.',
    via: ['FastAPI', 'Gemini Live API'] },
  { name: 'Async I/O',              category: 'concept',   source: 'inferred', confidence: 0.88, community: 4, inferred_by: 'graph_implies',
    reason: 'FastAPI and LangGraph both require async/await in Python.',
    via: ['FastAPI', 'LangGraph'] },
];

// Bridge skills (from GET /analytics.bridge_skills) — high centrality
const BRIDGES = [
  { name: 'FastAPI',    centrality: 0.87, category: 'framework',
    note: 'Connects backend, agent and data clusters. Your strongest hub.' },
  { name: 'Python',     centrality: 0.74, category: 'language',
    note: 'Underlies almost every project · 4 clusters touched.' },
  { name: 'Docker',     centrality: 0.42, category: 'tool',
    note: 'Joins shipping flow across web + agent stacks.' },
  { name: 'TypeScript', centrality: 0.38, category: 'language',
    note: 'Bridges frontend work into LangGraph orchestration UIs.' },
];

const TIMELINE = [
  { company: 'TechKareer',          title: 'Software Engineering Intern', start: '2026-01', end: null,      months: 5,  is_current: true,  stage: 'seed',  industry: 'EdTech',
    stack: ['Google ADK','FastAPI','Next.js','LangGraph'] },
  { company: 'Praskla Technology',  title: 'Software Engineering Intern', start: '2025-07', end: '2025-12', months: 6,  is_current: false, stage: 'seed',  industry: 'AI',
    stack: ['Python','FastAPI','PostgreSQL','Docker'] },
];

const EDUCATION = [
  { institution: 'KSR College of Engineering, Tiruchengode', degree: 'B.E.', field: 'Computer Science Engineering', start: '2022', end: '2026', tier: 'other' },
];

// Pinned repos (from /resume.enriched.github.pinned_repos)
const PROJECTS = [
  { name: 'the-mind-surf', stars: 4, forks: 1, language: 'TypeScript', is_new: false,
    topics: ['rag','nextjs','pinecone'],
    summary: 'RAG-based knowledge management — drop docs, ask, get cited answers.',
    stack: ['Next.js','Pinecone','FastAPI','OpenAI'] },
  { name: 'firstknock',    stars: 7, forks: 0, language: 'Python', is_new: true,
    topics: ['resume','graph','memgraph'],
    summary: 'Resume → knowledge graph. Same backend powering this dashboard.',
    stack: ['FastAPI','Memgraph','Neon','Celery'] },
  { name: 'live-voice-tutor', stars: 2, forks: 0, language: 'TypeScript', is_new: false,
    topics: ['gemini','webrtc'],
    summary: 'Voice-first tutor built on Gemini Live API.',
    stack: ['Next.js','Gemini Live','WebRTC'] },
  { name: 'agent-state-viz', stars: 1, forks: 0, language: 'Python', is_new: false,
    topics: ['langgraph','visualization'],
    summary: 'Visualize LangGraph state transitions as they happen.',
    stack: ['LangGraph','D3','FastAPI'] },
];

// Edges for the graph — co-occurs + structural (project→tech, company→tech).
// Source/target are skill names or special prefixed ids.
const EDGES = [
  // YOU → all explicit skills (HAS_SKILL)
  ...SKILLS.filter(s => s.source === 'explicit').map(s => ['YOU', s.name, 'HAS_SKILL']),
  // YOU → inferred (HAS_SKILL inferred)
  ...SKILLS.filter(s => s.source === 'inferred').map(s => ['YOU', s.name, 'HAS_SKILL_INFERRED']),
  // YOU → companies/projects
  ['YOU','co:TechKareer','WORKED_AT'],
  ['YOU','co:Praskla Technology','WORKED_AT'],
  ['YOU','proj:the-mind-surf','BUILT'],
  ['YOU','proj:firstknock','BUILT'],
  ['YOU','proj:live-voice-tutor','BUILT'],
  ['YOU','proj:agent-state-viz','BUILT'],
  ['YOU','edu:KSR','STUDIED_AT'],
  // CO_OCCURS within agent cluster
  ['LangGraph','Google ADK','CO_OCCURS'],
  ['LangGraph','RAG','CO_OCCURS'],
  ['LangGraph','Gemini Live API','CO_OCCURS'],
  ['Google ADK','RAG','CO_OCCURS'],
  ['Gemini Live API','WebRTC','IMPLIES'],
  ['LangGraph','Agent State Machines','IMPLIES'],
  // CO_OCCURS within web cluster
  ['React','Next.js','CO_OCCURS'],
  ['Next.js','TypeScript','CO_OCCURS'],
  ['React','TypeScript','CO_OCCURS'],
  ['Next.js','Tailwind CSS','CO_OCCURS'],
  ['TypeScript','JavaScript','CO_OCCURS'],
  // CO_OCCURS within backend cluster
  ['Python','FastAPI','CO_OCCURS'],
  ['FastAPI','Docker','CO_OCCURS'],
  ['FastAPI','Pydantic','IMPLIES'],
  ['FastAPI','Server-Sent Events','IMPLIES'],
  ['FastAPI','Async I/O','IMPLIES'],
  ['LangGraph','Async I/O','IMPLIES'],
  ['Python','GitHub Actions','CO_OCCURS'],
  ['Docker','Azure','CO_OCCURS'],
  // CO_OCCURS within data
  ['PostgreSQL','Neon','CO_OCCURS'],
  ['SQL','PostgreSQL','CO_OCCURS'],
  ['Pinecone','RAG','CO_OCCURS'],
  // Bridge edges between clusters
  ['FastAPI','LangGraph','CO_OCCURS'],
  ['FastAPI','Next.js','CO_OCCURS'],
  ['FastAPI','PostgreSQL','CO_OCCURS'],
  ['Next.js','FastAPI','CO_OCCURS'],
  ['TypeScript','LangGraph','CO_OCCURS'],
  // Companies → tech (USES)
  ['co:TechKareer','Google ADK','USES'],
  ['co:TechKareer','FastAPI','USES'],
  ['co:TechKareer','Next.js','USES'],
  ['co:TechKareer','LangGraph','USES'],
  ['co:Praskla Technology','Python','USES'],
  ['co:Praskla Technology','FastAPI','USES'],
  ['co:Praskla Technology','PostgreSQL','USES'],
  ['co:Praskla Technology','Docker','USES'],
  // Projects → tech (USES)
  ['proj:the-mind-surf','Next.js','USES'],
  ['proj:the-mind-surf','Pinecone','USES'],
  ['proj:the-mind-surf','FastAPI','USES'],
  ['proj:firstknock','FastAPI','USES'],
  ['proj:firstknock','Python','USES'],
  ['proj:live-voice-tutor','Next.js','USES'],
  ['proj:live-voice-tutor','Gemini Live API','USES'],
  ['proj:live-voice-tutor','WebRTC','USES'],
  ['proj:agent-state-viz','LangGraph','USES'],
  ['proj:agent-state-viz','Python','USES'],
];

window.DATA = { PROFILE, COMMUNITIES, SKILLS, BRIDGES, TIMELINE, EDUCATION, PROJECTS, EDGES };
