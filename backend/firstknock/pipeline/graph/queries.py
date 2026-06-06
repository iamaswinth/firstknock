MERGE_PERSON = """
MERGE (p:Person {person_id: $person_id})
ON CREATE SET p.name = $name, p.email = $email, p.headline = $headline,
              p.github_url = $github_url, p.linkedin_url = $linkedin_url, p.location = $location
ON MATCH SET  p.name = $name, p.email = $email, p.headline = $headline,
              p.github_url = $github_url, p.linkedin_url = $linkedin_url, p.location = $location
"""

# Removes stale explicit HAS_SKILL edges before re-writing from the latest extraction.
# Only touches source='explicit' — leaves future inferred/graph_algo edges untouched.
DELETE_STALE_EXPLICIT_SKILLS = """
MATCH (p:Person {person_id: $person_id})-[r:HAS_SKILL {source: 'explicit'}]->()
DELETE r
"""

MERGE_SKILL_AND_HAS_SKILL = """
MERGE (s:Skill {name: $name})
ON CREATE SET s.category = $category
WITH s
MATCH (p:Person {person_id: $person_id})
MERGE (p)-[r:HAS_SKILL]->(s)
ON CREATE SET r.confidence = 1.0, r.source = 'explicit'
"""

MERGE_COMPANY_AND_WORKED_AT = """
MERGE (c:Company {name: $company})
WITH c
MATCH (p:Person {person_id: $person_id})
MERGE (p)-[r:WORKED_AT {start_date: $start_date}]->(c)
ON CREATE SET r.title = $title, r.end_date = $end_date, r.months = $months,
              r.is_current = $is_current, r.location = $location,
              r.description = $description, r.skills_used = $skills_used
ON MATCH SET  r.title      = CASE WHEN $title <> '' THEN $title ELSE r.title END,
              r.end_date   = $end_date, r.months = $months, r.is_current = $is_current,
              r.location   = $location, r.description = $description, r.skills_used = $skills_used
"""

MERGE_PROJECT_AND_BUILT = """
MERGE (proj:Project {project_id: $project_id})
ON CREATE SET proj.name = $name, proj.description = $description,
              proj.url = $url, proj.github_url = $github_url
ON MATCH SET proj.name = $name, proj.description = $description,
             proj.url = $url, proj.github_url = $github_url
WITH proj
MATCH (p:Person {person_id: $person_id})
MERGE (p)-[:BUILT]->(proj)
"""

MERGE_PROJECT_USES_SKILL = """
MATCH (proj:Project {project_id: $project_id})
MERGE (s:Skill {name: $name})
ON CREATE SET s.category = $category
MERGE (proj)-[r:USES]->(s)
ON CREATE SET r.confidence = 1.0
"""

# Merge on (person, institution, degree) only — start_year is NOT in the key because
# null is not a valid MERGE property value in Memgraph, and the resume path stores
# years as strings while the LinkedIn path stores them as integers.
MERGE_INSTITUTION_AND_STUDIED_AT = """
MERGE (i:Institution {name: $institution})
WITH i
MATCH (p:Person {person_id: $person_id})
MERGE (p)-[r:STUDIED_AT {degree: $degree}]->(i)
ON CREATE SET r.field = $field, r.start_year = $start_year, r.end_year = $end_year
ON MATCH SET  r.field = $field, r.start_year = $start_year, r.end_year = $end_year
"""

# Uses UNWIND to process all pairs in a single query — avoids N²  round trips
MERGE_COMPANY_USED_SKILL = """
MATCH (c:Company {name: $company})
MERGE (s:Skill {name: $skill_name})
ON CREATE SET s.category = $category
MERGE (c)-[:USED_SKILL]->(s)
"""

MERGE_CO_OCCURS_BATCH = """
UNWIND $pairs AS pair
MATCH (s1:Skill {name: pair[0]})
MATCH (s2:Skill {name: pair[1]})
MERGE (s1)-[r:CO_OCCURS_WITH]->(s2)
ON CREATE SET r.coOccurrence = 1
ON MATCH SET r.coOccurrence = r.coOccurrence + 1
"""

COUNT_PERSON_RELS = """
MATCH (p:Person {person_id: $person_id})
OPTIONAL MATCH (p)-[r]-()
RETURN count(r) AS rel_count
"""

# ── Phase 4: Inference Engine queries ────────────────────────────────────────

DELETE_STALE_INFERRED_SKILLS = """
MATCH (p:Person {person_id: $person_id})-[r:HAS_SKILL {source: 'inferred'}]->()
DELETE r
"""

GET_EXPLICIT_SKILLS = """
MATCH (p:Person {person_id: $person_id})-[:HAS_SKILL {source: 'explicit'}]->(s:Skill)
RETURN s.name AS name, s.category AS category
"""  # DEPRECATED: pass explicit_skills directly to run_inference instead

# Skill-name-based equivalents — traverse Skill→Skill without a Person node.
# Used by the inference engine so the current user's graph need not be written first.
GET_GRAPH_IMPLIED_SKILLS_BY_NAMES = """
UNWIND $skill_names AS known_name
MATCH (known:Skill {name: known_name})-[r:SKILL_IMPLIES]->(candidate:Skill)
WHERE NOT candidate.name IN $skill_names
RETURN known_name AS inferred_from, candidate.name AS name,
       candidate.category AS category, r.confidence AS confidence, r.reason AS reason
"""

ADAMIC_ADAR_CANDIDATES_BY_NAMES = """
UNWIND $skill_names AS known_name
MATCH (known:Skill {name: known_name})-[:CO_OCCURS_WITH]-(candidate:Skill)
WHERE NOT candidate.name IN $skill_names
WITH candidate, count(DISTINCT known_name) AS overlap
WHERE overlap >= $min_overlap
RETURN candidate.name AS name, candidate.category AS category, overlap
ORDER BY overlap DESC
LIMIT $limit
"""

MERGE_INFERRED_HAS_SKILL = """
MERGE (s:Skill {name: $name})
ON CREATE SET s.category = $category
WITH s
MATCH (p:Person {person_id: $person_id})
MERGE (p)-[r:HAS_SKILL {source: 'inferred'}]->(s)
ON CREATE SET r.confidence = $confidence, r.source = 'inferred',
              r.inferred_by = $inferred_by, r.reason = $reason
ON MATCH SET  r.confidence = $confidence,
              r.inferred_by = $inferred_by, r.reason = $reason
"""

GET_GRAPH_IMPLIED_SKILLS = """
MATCH (p:Person {person_id: $person_id})-[:HAS_SKILL {source: 'explicit'}]->(known:Skill)
MATCH (known)-[r:SKILL_IMPLIES]->(candidate:Skill)
WHERE NOT (p)-[:HAS_SKILL {source: 'explicit'}]->(candidate)
RETURN known.name AS inferred_from, candidate.name AS name,
       candidate.category AS category, r.confidence AS confidence, r.reason AS reason
"""

MERGE_SKILL_IMPLIES = """
MERGE (s1:Skill {name: $source_skill})
MERGE (s2:Skill {name: $implied_skill})
MERGE (s1)-[r:SKILL_IMPLIES]->(s2)
ON CREATE SET r.confidence = $confidence, r.reason = $reason, r.count = 1
ON MATCH SET  r.confidence = (r.confidence * r.count + $confidence) / (r.count + 1),
              r.count = r.count + 1
"""

GET_TOTAL_EXPERIENCE_MONTHS = """
MATCH (p:Person {person_id: $person_id})-[r:WORKED_AT]->()
RETURN sum(r.months) AS total_months
"""

SET_PERSON_SENIORITY = """
MATCH (p:Person {person_id: $person_id})
SET p.seniority = $seniority, p.total_experience_months = $total_months
"""

ADAMIC_ADAR_CANDIDATES = """
MATCH (p:Person {person_id: $person_id})-[:HAS_SKILL]->(known:Skill)
MATCH (known)-[:CO_OCCURS_WITH]-(candidate:Skill)
WHERE NOT (p)-[:HAS_SKILL]->(candidate)
WITH p, candidate, count(DISTINCT known) AS overlap
WHERE overlap >= $min_overlap
RETURN candidate.name AS name, candidate.category AS category, overlap
ORDER BY overlap DESC
LIMIT $limit
"""

# ── Phase 5: Enrichment queries ───────────────────────────────────────────────

SET_PROJECT_ENRICHMENT = """
MATCH (proj:Project {project_id: $project_id})
SET proj.stars = $stars,
    proj.forks = $forks,
    proj.primary_language = $primary_language,
    proj.last_pushed = $last_pushed,
    proj.description = $description
"""

SET_PROJECT_INSIGHTS = """
MATCH (proj:Project {project_id: $project_id})
SET proj.category                   = $category,
    proj.domain                     = $domain,
    proj.use_case                   = $use_case,
    proj.problem_solved             = $problem_solved,
    proj.customer_type              = $customer_type,
    proj.similar_companies          = $similar_companies,
    proj.transferable_job_relevance = $transferable_job_relevance
"""

MERGE_PINNED_PROJECT = """
MERGE (proj:Project {project_id: $project_id})
ON CREATE SET proj.name = $name,
              proj.description = $description,
              proj.github_url = $github_url,
              proj.stars = $stars,
              proj.forks = $forks,
              proj.primary_language = $primary_language,
              proj.source = 'github_pinned'
ON MATCH SET  proj.stars = $stars,
              proj.forks = $forks,
              proj.primary_language = $primary_language
WITH proj
MATCH (p:Person {person_id: $person_id})
MERGE (p)-[:BUILT]->(proj)
"""

MERGE_PROJECT_TOPIC_SKILL = """
MATCH (proj:Project {project_id: $project_id})
MERGE (s:Skill {name: $name})
ON CREATE SET s.category = $category
MERGE (proj)-[r:USES]->(s)
ON CREATE SET r.confidence = 1.0
"""

SET_COMPANY_ENRICHMENT = """
MATCH (c:Company {name: $name})
SET c.stage = $stage,
    c.industry = $industry,
    c.headcount = $headcount,
    c.founded = $founded,
    c.headquarters = $headquarters,
    c.website = $website,
    c.linkedin_url = $linkedin_url,
    c.description = $description,
    c.business_model = $business_model,
    c.domain = $domain,
    c.customer_type = $customer_type,
    c.company_size = $company_size,
    c.tags = $tags,
    c.total_funding_usd = $total_funding_usd,
    c.last_round_type = $last_round_type,
    c.last_round_amount_usd = $last_round_amount_usd,
    c.last_round_date = $last_round_date,
    c.key_investors = $key_investors,
    c.founders = $founders,
    c.ceo = $ceo
"""

SET_WORKED_AT_INSIGHTS = """
MATCH (p:Person {person_id: $person_id})-[r:WORKED_AT]->(c:Company {name: $company})
WHERE r.start_date = $start_date
SET r.problems_solved         = $problems_solved,
    r.workflows_built         = $workflows_built,
    r.business_functions      = $business_functions,
    r.stakeholders_served     = $stakeholders_served,
    r.domain_expertise        = $domain_expertise,
    r.ai_systems_built        = $ai_systems_built,
    r.transferable_experience = $transferable_experience
"""

# LinkedIn enrichment queries

# Step 1: Try to find an existing resume-sourced WORKED_AT edge at the same company
# within a ±2-month window of the LinkedIn start date, and update it with LinkedIn data.
# Returns updated=1 if a match was found, 0 otherwise.
UPDATE_RESUME_EDGE_WITH_LINKEDIN = """
MATCH (p:Person {person_id: $person_id})-[r:WORKED_AT]->(c:Company {name: $company})
WHERE (r.source IS NULL OR r.source <> 'linkedin')
  AND r.start_date >= $start_lower
  AND r.start_date <= $start_upper
WITH r LIMIT 1
SET r.description = CASE
      WHEN $description <> '' AND (r.description IS NULL OR r.description = '')
      THEN $description
      ELSE r.description
    END,
    r.linkedin_title = $title,
    r.linkedin_start_date = $li_start_date
RETURN count(r) AS updated
"""

# Step 2: Only used when no resume edge was found — creates or merges on start_date.
# source='linkedin' removed from MERGE key: was forcing a new edge on every run
# even when a resume-written edge at the same company+date already existed.
CREATE_LINKEDIN_WORKED_AT = """
MERGE (c:Company {name: $company})
WITH c
MATCH (p:Person {person_id: $person_id})
MERGE (p)-[r:WORKED_AT {start_date: $start_date}]->(c)
ON CREATE SET r.title = $title, r.end_date = $end_date,
              r.is_current = $is_current, r.description = $description,
              r.source = 'linkedin'
ON MATCH SET  r.title      = CASE WHEN $title <> '' THEN $title ELSE r.title END,
              r.end_date   = $end_date, r.is_current = $is_current,
              r.description = CASE WHEN $description <> '' AND (r.description IS NULL OR r.description = '')
                              THEN $description ELSE r.description END
"""

SET_PERSON_LINKEDIN_STATS = """
MATCH (p:Person {person_id: $person_id})
SET p.linkedin_id = $linkedin_id,
    p.linkedin_headline = $headline,
    p.linkedin_connections = $connections,
    p.linkedin_followers = $followers,
    p.linkedin_summary = $summary,
    p.linkedin_open_to_work = $open_to_work,
    p.linkedin_hiring = $hiring,
    p.linkedin_verified = $verified,
    p.linkedin_current_company = $current_company
"""

# Write LinkedIn education as STUDIED_AT.
# Merges on (person, institution, degree) without start_year in the key — null start_year
# is not a valid MERGE property value in Memgraph. On match, only fills in missing data.
MERGE_LINKEDIN_STUDIED_AT = """
MERGE (i:Institution {name: $institution})
WITH i
MATCH (p:Person {person_id: $person_id})
MERGE (p)-[r:STUDIED_AT {degree: $degree}]->(i)
ON CREATE SET r.field = $field, r.start_year = $start_year, r.end_year = $end_year,
              r.source = 'linkedin'
ON MATCH SET  r.field      = CASE WHEN r.field IS NULL OR r.field = '' THEN $field ELSE r.field END,
              r.start_year = CASE WHEN r.start_year IS NULL THEN $start_year ELSE r.start_year END,
              r.end_year   = CASE WHEN r.end_year IS NULL THEN $end_year ELSE r.end_year END
"""

# Stamp per-job LinkedIn skills onto a matching WORKED_AT edge (found by ±2-month window).
UPDATE_WORKED_AT_JOB_SKILLS = """
MATCH (p:Person {person_id: $person_id})-[r:WORKED_AT]->(c:Company {name: $company})
WHERE r.start_date >= $start_lower AND r.start_date <= $start_upper
WITH r LIMIT 1
SET r.linkedin_job_skills = $job_skills
RETURN count(r) AS updated
"""

SET_INSTITUTION_TIER = """
MATCH (i:Institution {name: $name})
SET i.ranking_tier = $ranking_tier
"""

SET_PERSON_GITHUB_STATS = """
MATCH (p:Person {person_id: $person_id})
SET p.github_followers = $followers,
    p.public_repos = $public_repos
"""

# ── Phase 6: Embeddings ───────────────────────────────────────────────────────

SET_PERSON_EMBEDDING = """
MATCH (p:Person {person_id: $person_id})
SET p.embedding = $embedding
"""

SET_PROJECT_EMBEDDING = """
MATCH (proj:Project {project_id: $project_id})
SET proj.embedding = $embedding
"""

GET_PERSON_PROJECTS = """
MATCH (p:Person {person_id: $person_id})-[:BUILT]->(proj:Project)
RETURN proj.project_id AS project_id,
       proj.name AS name,
       proj.description AS description
"""

# ── Career Timeline read queries ─────────────────────────────────────────────

GET_CAREER_WORKED_AT = """
MATCH (p:Person {person_id: $person_id})-[r:WORKED_AT]->(c:Company)
RETURN c.name AS company, r.title AS title,
       r.start_date AS start_date, r.end_date AS end_date,
       r.months AS months, r.is_current AS is_current,
       r.skills_used AS skills_used,
       c.industry AS industry, c.stage AS stage,
       c.headcount AS headcount, c.founded AS founded,
       c.headquarters AS headquarters, c.website AS website,
       c.total_funding_usd AS total_funding_usd,
       c.last_round_type AS last_round_type,
       c.last_round_amount_usd AS last_round_amount_usd,
       c.key_investors AS key_investors,
       c.founders AS founders, c.ceo AS ceo
ORDER BY r.start_date DESC
"""

GET_CAREER_STUDIED_AT = """
MATCH (p:Person {person_id: $person_id})-[r:STUDIED_AT]->(i:Institution)
RETURN i.name AS institution, r.degree AS degree, r.field AS field,
       r.start_year AS start_year, r.end_year AS end_year
ORDER BY toInteger(toString(r.end_year)) DESC NULLS LAST
"""

# ── Phase 8: API read queries ─────────────────────────────────────────────────

GET_PERSON_NODE = """
MATCH (p:Person {person_id: $person_id})
RETURN p.seniority AS seniority,
       p.total_experience_months AS total_months,
       p.github_followers AS github_followers,
       p.public_repos AS public_repos
"""

DELETE_PERSON_AND_RELS = """
MATCH (p:Person {person_id: $person_id})
OPTIONAL MATCH (p)-[:BUILT]->(proj:Project)
DETACH DELETE proj, p
"""

GET_ALL_SKILLS = """
MATCH (p:Person {person_id: $person_id})-[r:HAS_SKILL]->(s:Skill)
RETURN s.name AS name, s.category AS category,
       r.source AS source, r.confidence AS confidence,
       r.inferred_by AS inferred_by, r.reason AS reason
ORDER BY r.source, r.confidence DESC
"""

GET_EGO_GRAPH = """
MATCH (p:Person {person_id: $person_id})-[w:WORKED_AT]->(c:Company)
RETURN labels(p) AS src_labels, properties(p) AS src_props,
       type(w) AS rel_type, properties(w) AS rel_props,
       labels(c) AS tgt_labels, properties(c) AS tgt_props

UNION ALL

MATCH (p:Person {person_id: $person_id})-[:WORKED_AT]->(c:Company)
WITH DISTINCT c
MATCH (c)-[u:USED_SKILL]->(s:Skill)
RETURN labels(c) AS src_labels, properties(c) AS src_props,
       type(u) AS rel_type, properties(u) AS rel_props,
       labels(s) AS tgt_labels, properties(s) AS tgt_props

UNION ALL

MATCH (p:Person {person_id: $person_id})-[b:BUILT]->(proj:Project)
RETURN labels(p) AS src_labels, properties(p) AS src_props,
       type(b) AS rel_type, properties(b) AS rel_props,
       labels(proj) AS tgt_labels, properties(proj) AS tgt_props

UNION ALL

MATCH (p:Person {person_id: $person_id})-[:BUILT]->(proj:Project)-[u:USES]->(s:Skill)
RETURN labels(proj) AS src_labels, properties(proj) AS src_props,
       type(u) AS rel_type, properties(u) AS rel_props,
       labels(s) AS tgt_labels, properties(s) AS tgt_props

UNION ALL

MATCH (p:Person {person_id: $person_id})-[st:STUDIED_AT]->(i:Institution)
RETURN labels(p) AS src_labels, properties(p) AS src_props,
       type(st) AS rel_type, properties(st) AS rel_props,
       labels(i) AS tgt_labels, properties(i) AS tgt_props
"""

GET_SKILL_CONTEXT = """
MATCH (p:Person {person_id: $person_id})

// Layer 1a — Work experience
OPTIONAL MATCH (p)-[w:WORKED_AT]->(c:Company)
WITH p, collect({w:w, c:c}) AS work_pairs

// Layer 1a skills — re-traverse to avoid cartesian product with projects
OPTIONAL MATCH (p)-[:WORKED_AT]->(wc:Company)-[cu:USED_SKILL]->(s_c:Skill)
WITH p, work_pairs, collect({cu:cu, wc:wc, s_c:s_c}) AS comp_skill_pairs

// Layer 1b — Projects
OPTIONAL MATCH (p)-[b:BUILT]->(proj:Project)
WITH p, work_pairs, comp_skill_pairs, collect({b:b, proj:proj}) AS built_pairs

// Layer 1b skills
OPTIONAL MATCH (p)-[:BUILT]->(bp:Project)-[pu:USES]->(s_p:Skill)
WITH p, work_pairs, comp_skill_pairs, built_pairs, collect({pu:pu, bp:bp, s_p:s_p}) AS proj_skill_pairs

// Layer 1c — Education
OPTIONAL MATCH (p)-[st:STUDIED_AT]->(edu:Institution)
WITH p, work_pairs, comp_skill_pairs, built_pairs, proj_skill_pairs,
     collect({st:st, edu:edu}) AS edu_pairs

// Emit one row per relationship — same column contract as the old UNION ALL
UNWIND (
  [x IN work_pairs WHERE x.w IS NOT NULL |
     {src_labels: labels(p),    src_props: properties(p),
      rel_type: 'WORKED_AT',    rel_props: properties(x.w),
      tgt_labels: labels(x.c),  tgt_props: properties(x.c)}] +
  [x IN comp_skill_pairs WHERE x.cu IS NOT NULL |
     {src_labels: labels(x.wc),   src_props: properties(x.wc),
      rel_type: 'USED_SKILL',     rel_props: properties(x.cu),
      tgt_labels: labels(x.s_c), tgt_props: properties(x.s_c)}] +
  [x IN built_pairs WHERE x.b IS NOT NULL |
     {src_labels: labels(p),       src_props: properties(p),
      rel_type: 'BUILT',           rel_props: properties(x.b),
      tgt_labels: labels(x.proj), tgt_props: properties(x.proj)}] +
  [x IN proj_skill_pairs WHERE x.pu IS NOT NULL |
     {src_labels: labels(x.bp),   src_props: properties(x.bp),
      rel_type: 'USES',            rel_props: properties(x.pu),
      tgt_labels: labels(x.s_p), tgt_props: properties(x.s_p)}] +
  [x IN edu_pairs WHERE x.st IS NOT NULL |
     {src_labels: labels(p),       src_props: properties(p),
      rel_type: 'STUDIED_AT',      rel_props: properties(x.st),
      tgt_labels: labels(x.edu), tgt_props: properties(x.edu)}]
) AS row

RETURN row.src_labels AS src_labels, row.src_props AS src_props,
       row.rel_type   AS rel_type,   row.rel_props  AS rel_props,
       row.tgt_labels AS tgt_labels, row.tgt_props  AS tgt_props
"""

GET_PERSON_SKILL_COOCCURRENCE = """
MATCH (p:Person {person_id: $person_id})-[:HAS_SKILL]->(s1:Skill)
MATCH (s1)-[r:CO_OCCURS_WITH]-(s2:Skill)
MATCH (p)-[:HAS_SKILL]->(s2)
RETURN s1.name AS skill1, s2.name AS skill2, r.coOccurrence AS co_occurrence
"""

GET_INFERRED_SKILLS_DETAIL = """
MATCH (p:Person {person_id: $person_id})-[r:HAS_SKILL]->(s:Skill)
WHERE r.source IN ['inferred', 'graph_algo']
RETURN s.name AS name, s.category AS category,
       r.source AS source, r.confidence AS confidence,
       r.inferred_by AS inferred_by, r.reason AS reason
ORDER BY r.confidence DESC
"""

