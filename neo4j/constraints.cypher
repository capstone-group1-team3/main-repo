// constraints.cypher — uniqueness constraints on every node key.
// Run once before loading. Safe to re-run (IF NOT EXISTS).

CREATE CONSTRAINT customer_id IF NOT EXISTS
FOR (c:Customer) REQUIRE c.customer_id IS UNIQUE;

CREATE CONSTRAINT account_email IF NOT EXISTS
FOR (a:Account) REQUIRE a.email IS UNIQUE;

CREATE CONSTRAINT order_id IF NOT EXISTS
FOR (o:Order) REQUIRE o.order_id IS UNIQUE;

CREATE CONSTRAINT product_id IF NOT EXISTS
FOR (p:Product) REQUIRE p.product_id IS UNIQUE;

CREATE CONSTRAINT category_name IF NOT EXISTS
FOR (c:Category) REQUIRE c.name IS UNIQUE;

CREATE CONSTRAINT ticket_id IF NOT EXISTS
FOR (t:Ticket) REQUIRE t.ticket_id IS UNIQUE;

CREATE CONSTRAINT request_id IF NOT EXISTS
FOR (s:ServiceRequest) REQUIRE s.request_id IS UNIQUE;

CREATE CONSTRAINT payment_issue_id IF NOT EXISTS
FOR (pi:PaymentIssue) REQUIRE pi.issue_id IS UNIQUE;

CREATE CONSTRAINT payment_id IF NOT EXISTS
FOR (p:Payment) REQUIRE p.payment_id IS UNIQUE;

CREATE CONSTRAINT shipment_order_id IF NOT EXISTS
FOR (s:Shipment) REQUIRE s.order_id IS UNIQUE;
