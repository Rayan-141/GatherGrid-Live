import os
from neo4j import GraphDatabase

# ── Database Connection ───────────────────────────────────────────
# Use environment variables for security, fallback to your AuraDB details
URI = os.environ.get("NEO4J_URI", "neo4j+ssc://69817a0b.databases.neo4j.io")
USER = os.environ.get("NEO4J_USERNAME", "69817a0b")
PASSWORD = os.environ.get("NEO4J_PASSWORD", "x4VCeSqbiTZUjPoY9iXLwljbHzmTy9U3t2l2GXsyGHY")

driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))

def get_driver():
    return driver

# ── Seed Data ─────────────────────────────────────────────────────
def seed_db():
    with driver.session() as session:
        # ── Just-in-Time (JIT) Presentation Mode ──
        # DETACH DELETE removes everything for a truly clean 0-node start.
        session.run("MATCH (n) DETACH DELETE n")
        print("✅ Presentation Mode: 0 Nodes in Graph. Ready for Just-in-Time creation.")

def close_driver():
    driver.close()
