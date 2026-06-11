// Neo4j graph schema for legal document intelligence

// Constraints
CREATE CONSTRAINT document_id IF NOT EXISTS
  FOR (d:Document) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT regulation_code IF NOT EXISTS
  FOR (r:Regulation) REQUIRE r.code IS UNIQUE;

CREATE CONSTRAINT entity_name IF NOT EXISTS
  FOR (e:Entity) REQUIRE e.name IS UNIQUE;

// Indexes
CREATE INDEX document_jurisdiction IF NOT EXISTS
  FOR (d:Document) ON (d.jurisdiction);

CREATE INDEX regulation_effective IF NOT EXISTS
  FOR (r:Regulation) ON (r.effective_date);

// Node schemas
// (:Document {id, title, jurisdiction, doc_type, issued_date, content_hash, embedding_id})
// (:Regulation {code, title, jurisdiction, effective_date, status})
// (:Entity {name, entity_type})  -- law firm | regulator | company

// Relationships
// (:Document)-[:REFERENCES {clause, strength}]->(:Document)
// (:Document)-[:GOVERNED_BY {applicability}]->(:Regulation)
// (:Document)-[:INVOLVES {role}]->(:Entity)
// (:Regulation)-[:SUPERSEDES]->(:Regulation)
// (:Regulation)-[:IMPLEMENTS]->(:Regulation)
