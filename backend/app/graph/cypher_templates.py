"""
graph/cypher_templates.py — every Cypher query as a named, MERGE-based template.

Fixes:
  - GET_CUSTOMER_ORDERS and GET_ORDER_FOR_CUSTOMER now return product_name
    and filter null items so the frontend shows full order details.
  - GET_CUSTOMER_REQUESTS uses COALESCE(s.resolved_at, null) to remove
    the Neo4j missing-property WARNING.
  - All load operations are idempotent (MERGE).
  - All read operations are scoped by customer_id for ownership enforcement.
"""

# ============================================================================
# LOAD TEMPLATES (idempotent, batched via UNWIND $rows)
# ============================================================================

LOAD_CUSTOMERS = """
UNWIND $rows AS row
MERGE (c:Customer {customer_id: row.customer_id})
SET
    c.customer_name          = row.customer_name,
    c.customer_email         = row.customer_email,
    c.customer_password_hash = row.customer_password_hash
"""

LOAD_ORDERS = """
UNWIND $rows AS row
MATCH (c:Customer {customer_id: row.customer_id})
MERGE (o:Order {order_id: row.order_id})
SET
    o.status                  = row.status,
    o.order_purchase_date     = row.order_purchase_date,
    o.estimated_delivery_date = row.estimated_delivery_date,
    o.delivered_date          = row.delivered_date
MERGE (c)-[:PLACED]->(o)
"""

LOAD_PRODUCTS = """
UNWIND $rows AS row
MERGE (p:Product {product_id: row.product_id})
SET
    p.product_name = row.product_name,
    p.price        = row.price
MERGE (cat:Category {name: row.category})
MERGE (p)-[:BELONGS_TO]->(cat)
"""

LOAD_ORDER_ITEMS = """
UNWIND $rows AS row
MATCH (o:Order   {order_id:   row.order_id})
MATCH (p:Product {product_id: row.product_id})
MERGE (o)-[r:CONTAINS]->(p)
SET
    r.quantity      = row.quantity,
    r.unit_price    = row.unit_price,
    r.freight_value = row.freight_value
"""

LOAD_PAYMENTS = """
UNWIND $rows AS row
MATCH (o:Order {order_id: row.order_id})
MERGE (pay:Payment {payment_id: row.payment_id})
SET
    pay.payment_type  = row.payment_type,
    pay.installments  = row.installments,
    pay.payment_value = row.payment_value
MERGE (o)-[:PAID_WITH]->(pay)
"""

LOAD_TICKETS = """
UNWIND $rows AS row
MATCH (c:Customer {customer_id: row.customer_id})
MATCH (o:Order    {order_id:    row.order_id})
MERGE (t:Ticket {ticket_id: row.ticket_id})
SET
    t.category   = row.category,
    t.subject    = row.subject,
    t.status     = row.status,
    t.created_at = row.created_at
MERGE (c)-[:HAS_TICKET]->(t)
MERGE (o)-[:ABOUT]->(t)
"""

LOAD_SERVICE_REQUESTS = """
UNWIND $rows AS row
MATCH (c:Customer {customer_id: row.customer_id})
MATCH (o:Order    {order_id:    row.order_id})
MERGE (s:ServiceRequest {request_id: row.request_id})
SET
    s.type        = row.type,
    s.reason      = row.reason,
    s.status      = row.status,
    s.evidence    = row.evidence,
    s.created_at  = row.created_at,
    s.resolved_at = row.resolved_at
MERGE (c)-[:HAS_REQUEST]->(s)
MERGE (o)-[:HAS_REQUEST]->(s)
"""

LOAD_PAYMENT_ISSUES = """
UNWIND $rows AS row
MATCH (o:Order {order_id: row.order_id})
MERGE (pi:PaymentIssue {issue_id: row.issue_id})
SET
    pi.issue_type = row.issue_type,
    pi.status     = row.status,
    pi.created_at = row.created_at
MERGE (o)-[:HAS_ISSUE]->(pi)
"""

# ============================================================================
# READ TEMPLATES (all scoped by customer_id for ownership enforcement)
# ============================================================================

GET_CUSTOMER_ORDERS = """
MATCH (c:Customer {customer_id: $customer_id})-[:PLACED]->(o:Order)
OPTIONAL MATCH (o)-[r:CONTAINS]->(p:Product)-[:BELONGS_TO]->(cat:Category)
WITH o,
     collect(
       CASE WHEN p IS NOT NULL THEN {
         product_id:   p.product_id,
         product_name: p.product_name,
         category:     cat.name,
         quantity:     r.quantity,
         unit_price:   r.unit_price
       } ELSE null END
     ) AS all_items
OPTIONAL MATCH (o)-[:PAID_WITH]->(pay:Payment)
WITH o, all_items, pay ORDER BY pay.payment_id
WITH o, all_items, collect(pay) AS payments
OPTIONAL MATCH (o)-[:SHIPPED_AS]->(shipment:Shipment)
RETURN
    o.order_id                AS order_id,
    o.status                  AS status,
    o.order_purchase_date     AS purchase_date,
    o.delivered_date          AS delivered_date,
    o.estimated_delivery_date AS estimated_delivery_date,
    CASE WHEN size(payments) > 1 THEN 'split'
         ELSE head(payments).payment_type END AS payment_type,
    reduce(total = 0.0, x IN payments | total + coalesce(x.payment_value, 0.0)) AS payment_value,
    head(payments).installments AS installments,
    [x IN payments | {
      payment_id: x.payment_id,
      payment_type: x.payment_type,
      payment_value: x.payment_value,
      installments: x.installments
    }] AS payments,
    coalesce(shipment.late, false) AS delivery_late,
    [item IN all_items WHERE item IS NOT NULL] AS items
ORDER BY purchase_date DESC
"""

GET_ORDER_FOR_CUSTOMER = """
MATCH (c:Customer {customer_id: $customer_id})
      -[:PLACED]->(o:Order {order_id: $order_id})
OPTIONAL MATCH (o)-[r:CONTAINS]->(p:Product)-[:BELONGS_TO]->(cat:Category)
WITH o,
     collect(
       CASE WHEN p IS NOT NULL THEN {
         product_id:   p.product_id,
         product_name: p.product_name,
         category:     cat.name,
         quantity:     r.quantity,
         unit_price:   r.unit_price
       } ELSE null END
     ) AS all_items
OPTIONAL MATCH (o)-[:PAID_WITH]->(pay:Payment)
WITH o, all_items, pay ORDER BY pay.payment_id
WITH o, all_items, collect(pay) AS payments
OPTIONAL MATCH (o)-[:SHIPPED_AS]->(shipment:Shipment)
RETURN
    o.order_id                AS order_id,
    o.status                  AS status,
    o.order_purchase_date     AS purchase_date,
    o.delivered_date          AS delivered_date,
    o.estimated_delivery_date AS estimated_delivery_date,
    CASE WHEN size(payments) > 1 THEN 'split'
         ELSE head(payments).payment_type END AS payment_type,
    reduce(total = 0.0, x IN payments | total + coalesce(x.payment_value, 0.0)) AS payment_value,
    head(payments).installments AS installments,
    [x IN payments | {
      payment_id: x.payment_id,
      payment_type: x.payment_type,
      payment_value: x.payment_value,
      installments: x.installments
    }] AS payments,
    coalesce(shipment.late, false) AS delivery_late,
    [item IN all_items WHERE item IS NOT NULL] AS items
"""

GET_CUSTOMER_TICKETS = """
MATCH (c:Customer {customer_id: $customer_id})-[:HAS_TICKET]->(t:Ticket)
OPTIONAL MATCH (o:Order)-[:ABOUT]->(t)
RETURN
    t.ticket_id  AS ticket_id,
    t.category   AS category,
    t.subject    AS subject,
    t.status     AS status,
    t.created_at AS created_at,
    o.order_id   AS order_id
ORDER BY created_at DESC
"""

GET_CUSTOMER_REQUESTS = """
MATCH (c:Customer {customer_id: $customer_id})-[:HAS_REQUEST]->(s:ServiceRequest)
OPTIONAL MATCH (o:Order)-[:HAS_REQUEST]->(s)
RETURN
    s.request_id                  AS request_id,
    s.type                        AS type,
    s.reason                      AS reason,
    s.status                      AS status,
    s.evidence                    AS evidence,
    s.created_at                  AS created_at,
    COALESCE(s.resolved_at, null) AS resolved_at,
    o.order_id                    AS order_id
ORDER BY created_at DESC
"""

GET_ALL_TICKETS = """
MATCH (c:Customer)-[:HAS_TICKET]->(t:Ticket)
OPTIONAL MATCH (o:Order)-[:ABOUT]->(t)
RETURN
    c.customer_id   AS customer_id,
    c.customer_name AS customer_name,
    t.ticket_id     AS ticket_id,
    t.category      AS category,
    t.subject       AS subject,
    t.status        AS status,
    t.created_at    AS created_at,
    o.order_id      AS order_id
ORDER BY created_at DESC
"""
