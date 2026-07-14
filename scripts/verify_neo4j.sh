#!/bin/sh
set -eu

auth=${NEO4J_AUTH:?NEO4J_AUTH is required}
user=${auth%%/*}
password=${auth#*/}
cypher_shell=/var/lib/neo4j/bin/cypher-shell
address=${NEO4J_VERIFY_ADDRESS:-bolt://neo4j:7687}

run_query() {
  "$cypher_shell" -a "$address" -u "$user" -p "$password" "$1"
}

run_query "RETURN 1 AS ok"
run_query "SHOW CONSTRAINTS YIELD labelsOrTypes, properties RETURN labelsOrTypes, properties ORDER BY labelsOrTypes[0]"
run_query "SHOW INDEXES YIELD labelsOrTypes, properties, state RETURN labelsOrTypes, properties, state ORDER BY labelsOrTypes[0]"
run_query "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS count ORDER BY label"
run_query "MATCH (o:Order) WHERE NOT (:Customer)-[:PLACED]->(o) RETURN count(o) AS orders_without_customer"
run_query "MATCH (t:Ticket) WHERE NOT (:Customer)-[:HAS_TICKET]->(t) RETURN count(t) AS tickets_without_customer"
run_query "MATCH (r:ServiceRequest) WHERE NOT (:Customer)-[:HAS_REQUEST]->(r) OR NOT (:Order)-[:HAS_REQUEST]->(r) RETURN count(r) AS invalid_service_requests"
