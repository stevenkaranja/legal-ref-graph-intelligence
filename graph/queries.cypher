// Find all regulations referenced by a document chain
MATCH path = (d:Document {id: $doc_id})-[:REFERENCES*1..3]->(ref:Document)
             -[:GOVERNED_BY]->(reg:Regulation)
WHERE reg.status = 'ACTIVE'
RETURN DISTINCT reg.code, reg.title, reg.jurisdiction,
       length(path) AS hops
ORDER BY hops ASC;

// Compliance gap analysis — find documents without active regulation
MATCH (d:Document)
WHERE NOT (d)-[:GOVERNED_BY]->(:Regulation {status: 'ACTIVE'})
  AND d.doc_type IN ['CONTRACT', 'POLICY']
RETURN d.id, d.title, d.jurisdiction, d.issued_date
ORDER BY d.issued_date DESC;

// Regulatory impact: which documents are affected by a regulation change
MATCH (r:Regulation {code: $reg_code})<-[:GOVERNED_BY]-(d:Document)
OPTIONAL MATCH (d)<-[:REFERENCES*1..2]-(upstream:Document)
RETURN DISTINCT d.id, d.title, count(upstream) AS upstream_refs
ORDER BY upstream_refs DESC;

// Entity involvement network
MATCH (e:Entity {name: $entity_name})<-[:INVOLVES]-(d:Document)-[:GOVERNED_BY]->(r:Regulation)
RETURN d.title, r.code, r.jurisdiction, type(relationships(path)[0]) AS role
ORDER BY d.issued_date DESC;

// Optimised: use APOC for parallel traversal at scale
CALL apoc.path.subgraphNodes(startNode, {
  relationshipFilter: 'REFERENCES>',
  maxLevel: 3,
  bfs: true
}) YIELD node
WHERE node:Document
RETURN node.id, node.title;
