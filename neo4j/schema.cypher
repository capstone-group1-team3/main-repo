// schema.cypher — reference documentation of the graph model.
// This file is descriptive (comments); constraints.cypher and indexes.cypher
// are the executable parts. Kept here so the schema lives with the code.
//
// ============================ NODES ============================
//
// (:Customer  {customer_unique_id})          the stable PERSON (customer-360 anchor)
// (:Account   {email, password_hash, role})  auth; role in {customer, staff, admin}
// (:Order     {order_id, status,
//              purchase_date, approved_date,
//              delivered_carrier_date,
//              delivered_customer_date,
//              estimated_delivery_date})
// (:Product   {product_id})
// (:Category  {name})                         English category name
// (:Shipment  {order_id, delivered_customer_date, estimated_delivery_date, late})
//                                             derived from Order date columns
// (:Ticket    {ticket_id, category, subject, status, created_at})
// (:ServiceRequest {request_id, type, reason, status, evidence,
//                   created_at, resolved_at})  type in
//                   {refund, return, replacement, warranty}
// (:PaymentIssue {issue_id, issue_type, status, created_at})
//
// ========================= RELATIONSHIPS =======================
//
// (:Account)-[:BELONGS_TO]->(:Customer)
// (:Customer)-[:PLACED]->(:Order)
// (:Order)-[:CONTAINS {quantity, unit_price, freight_value}]->(:Product)
// (:Product)-[:BELONGS_TO]->(:Category)
// (:Order)-[:SHIPPED_AS]->(:Shipment)
// (:Order)-[:PAID_WITH {installments, value, sequential}]->(:Payment)   (optional)
// (:Customer)-[:HAS_TICKET]->(:Ticket)
// (:Order)-[:ABOUT]->(:Ticket)
// (:Customer)-[:HAS_REQUEST]->(:ServiceRequest)
// (:Order)-[:HAS_REQUEST]->(:ServiceRequest)
// (:Order)-[:HAS_ISSUE]->(:PaymentIssue)
//
// Notes:
//  - Customer is keyed on customer_unique_id (the person), so all of a person's
//    orders/tickets/requests aggregate under ONE node (customer-360).
//  - Payments are modeled as a relationship property summary on the order to keep
//    the graph lean; a separate (:Payment) node can be added later if needed.
//  - seller_id and shipping_limit_date from order_items are intentionally ignored.
