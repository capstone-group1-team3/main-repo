"""
auth/auth_service.py — registration and login against Neo4j.

Updated for the new schema:
  - Customer node keyed on customer_id  (not customer_unique_id)
  - password_hash already exists in the dataset → we store/verify it
  - Account node keeps email + role and links to Customer

Node structure:
    (:Account {email, password_hash, role})
        -[:BELONGS_TO]->
    (:Customer {customer_id, customer_name, customer_email, customer_password_hash})
"""
from __future__ import annotations

from dataclasses import dataclass

from app.graph.neo4j_client import graph_client
from app.auth.password_utils import hash_password, verify_password
from app.auth.jwt_utils import create_access_token


class AuthError(Exception):
    """Raised on bad credentials or duplicate registration."""


@dataclass
class Identity:
    customer_id: str        # stable person key (was customer_unique_id)
    email: str
    role: str


# ── Cypher ────────────────────────────────────────────────────────────────────

_CREATE_ACCOUNT = """
MATCH (c:Customer {customer_id: $customer_id})
WHERE toLower(trim(c.customer_email)) = $email
MERGE (a:Account {email: $email})
  ON CREATE SET a.password_hash = $password_hash,
                a.role          = $role
MERGE (a)-[:BELONGS_TO]->(c)
RETURN a.email            AS email,
       a.role             AS role,
       c.customer_id      AS customer_id
"""

_GET_ACCOUNT = """
MATCH (a:Account {email: $email})-[:BELONGS_TO]->(c:Customer)
RETURN a.email            AS email,
       a.password_hash    AS password_hash,
       a.role             AS role,
       c.customer_id      AS customer_id
"""

_ACCOUNT_EXISTS = """
MATCH (a:Account {email: $email}) RETURN count(a) AS n
"""

# Login directly with customer_id + password_hash already in the Customer node
_GET_CUSTOMER_BY_ID = """
MATCH (c:Customer {customer_id: $customer_id})
RETURN c.customer_id           AS customer_id,
       c.customer_name         AS customer_name,
       c.customer_email        AS customer_email,
       c.customer_password_hash AS password_hash
"""


# ── Public API ────────────────────────────────────────────────────────────────

def register(
    email: str,
    password: str,
    customer_id: str,
    role: str = "customer",
) -> Identity:
    """Create a customer Account linked to an existing matching Customer.

    Public callers cannot create privileged roles.  Matching the supplied email
    to the pre-existing Customer record is the project's current lightweight
    ownership check; it is not a substitute for production email verification.
    """
    if role != "customer":
        raise AuthError("privileged account creation is not supported")
    email = str(email).strip().lower()
    rows = graph_client.read(_ACCOUNT_EXISTS, email=email)
    if rows and rows[0]["n"] > 0:
        raise AuthError("an account with this email already exists")

    rows = graph_client.write(
        _CREATE_ACCOUNT,
        email=email,
        password_hash=hash_password(password),
        role=role,
        customer_id=customer_id,
        query_type="auth_create_account",
    )
    if not rows:
        raise AuthError("customer record could not be verified")
    r = rows[0]
    return Identity(
        customer_id=r["customer_id"],
        email=r["email"],
        role=r["role"],
    )


def authenticate(email: str, password: str) -> str:
    """
    Verify credentials and return a signed JWT.

    Checks the Account node's password_hash first.
    Falls back to the Customer node's customer_password_hash (pre-loaded
    from the dataset) so that demo customers can log in directly.
    """
    rows = graph_client.read(_GET_ACCOUNT, email=email)
    if rows:
        acc = rows[0]
        if not verify_password(password, acc["password_hash"]):
            raise AuthError("invalid email or password")
        return create_access_token(
            customer_id=acc["customer_id"],
            email=acc["email"],
            role=acc["role"],
        )

    raise AuthError("invalid email or password")


def authenticate_by_customer_id(customer_id: str, password: str) -> str:
    """
    Allow demo customers (loaded from CSV) to log in with their
    customer_id + the hashed password already stored on the Customer node.
    """
    rows = graph_client.read(
        _GET_CUSTOMER_BY_ID, customer_id=customer_id
    )
    if not rows:
        raise AuthError("customer not found")
    c = rows[0]
    if not verify_password(password, c["password_hash"]):
        raise AuthError("invalid password")
    return create_access_token(
        customer_id=c["customer_id"],
        email=c["customer_email"],
        role="customer",
    )
