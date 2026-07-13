# Neo4j constraint migration

`constraints.cypher` now describes the active keys used by the loaders and API.
Applying `IF NOT EXISTS` creates missing constraints but does not remove the old
`customer_uid` constraint and must not be used to conceal duplicate data.

For an existing valuable database:

1. Back up the database using the deployment's approved Neo4j backup process.
2. Run these read-only duplicate checks in Neo4j Browser:

   ```cypher
   MATCH (c:Customer)
   WITH c.customer_id AS key, count(*) AS n
   WHERE key IS NULL OR n > 1
   RETURN key, n;

   MATCH (p:Payment)
   WITH p.payment_id AS key, count(*) AS n
   WHERE key IS NULL OR n > 1
   RETURN key, n;

   MATCH (s:Shipment)
   WITH s.order_id AS key, count(*) AS n
   WHERE key IS NULL OR n > 1
   RETURN key, n;
   ```

3. Resolve any returned records through an audited data migration.
4. Apply only the new `CREATE CONSTRAINT ... IF NOT EXISTS` statements.
5. Verify the new constraints with `SHOW CONSTRAINTS`.
6. Drop the obsolete constraint only in a separately approved maintenance step.

The application never drops constraints automatically.
