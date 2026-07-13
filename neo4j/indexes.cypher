// indexes.cypher — secondary indexes for lookups and admin filters.
// Uniqueness constraints already create backing indexes on key properties;
// these cover the non-unique fields we filter/sort on.

CREATE INDEX order_status IF NOT EXISTS
FOR (o:Order) ON (o.status);

CREATE INDEX ticket_status IF NOT EXISTS
FOR (t:Ticket) ON (t.status);

CREATE INDEX request_type IF NOT EXISTS
FOR (s:ServiceRequest) ON (s.type);

CREATE INDEX request_status IF NOT EXISTS
FOR (s:ServiceRequest) ON (s.status);

CREATE INDEX payment_issue_status IF NOT EXISTS
FOR (pi:PaymentIssue) ON (pi.status);

CREATE INDEX account_role IF NOT EXISTS
FOR (a:Account) ON (a.role);
