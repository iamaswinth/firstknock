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
MERGE (p)-[r:WORKED_AT {title: $title, start_date: $start_date}]->(c)
ON CREATE SET r.end_date = $end_date, r.months = $months, r.is_current = $is_current,
              r.location = $location, r.description = $description, r.skills_used = $skills_used
ON MATCH SET  r.end_date = $end_date, r.months = $months, r.is_current = $is_current,
              r.location = $location, r.description = $description, r.skills_used = $skills_used
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

MERGE_INSTITUTION_AND_STUDIED_AT = """
MERGE (i:Institution {name: $institution})
WITH i
MATCH (p:Person {person_id: $person_id})
MERGE (p)-[r:STUDIED_AT {degree: $degree, start_year: $start_year}]->(i)
ON CREATE SET r.field = $field, r.end_year = $end_year
ON MATCH SET r.field = $field, r.end_year = $end_year
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
