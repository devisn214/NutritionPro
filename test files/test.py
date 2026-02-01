from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "bolt://localhost:7687",
    auth=("neo4j", "neo4jabc")
)

with driver.session() as session:
    print(session.run("MATCH (n) RETURN count(n)").single()[0])

driver.close()
