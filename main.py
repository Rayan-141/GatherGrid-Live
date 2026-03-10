from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from starlette_graphene3 import GraphQLApp
from db import seed_db
from schemas import schema
import uvicorn

# ── Seed the database ──
seed_db()

app = FastAPI(title="Event Ticket Booking System")

# ── Add CORS Middleware ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Fixed GraphiQL UI ──
GRAPHIQL_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>GraphiQL</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/graphiql@3.0.6/graphiql.min.css" />
</head>
<body style="margin: 0;">
  <div id="graphiql" style="height: 100vh;"></div>
  <script src="https://cdn.jsdelivr.net/npm/react@18.2.0/umd/react.production.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/react-dom@18.2.0/umd/react-dom.production.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/graphiql@3.0.6/graphiql.min.js"></script>
  <script>
    const fetcher = GraphiQL.createFetcher({ url: '/graphql' });
    const root = ReactDOM.createRoot(document.getElementById('graphiql'));
    root.render(React.createElement(GraphiQL, { fetcher: fetcher }));
  </script>
</body>
</html>
"""

# ── 10000% CORRECT ROUTING ──
# This handler serves our custom HTML for GET requests
async def graphiql_ui_handler(request):
    return HTMLResponse(GRAPHIQL_HTML)

# We register a single route that handles GET (UI) and POST (Data) correctly
app.add_route("/graphql", GraphQLApp(schema=schema, on_get=graphiql_ui_handler))

@app.get("/")
async def root():
    return {"message": "Server Online. Visit http://127.0.0.1:8000/graphql"}

import os

if __name__ == "__main__":
    # Get port from environment variable (for Render/Vercel) or default to 8000
    port = int(os.environ.get("PORT", 8000))
    print(f"\n🚀 SUCCESS! Your API is ready on port {port}.")
    print(f"1. GraphQL Interface: http://0.0.0.0:{port}/graphql")
    print("2. Neo4j Browser: http://localhost:7474 (Pass: password)\n")
    
    # Use 0.0.0.0 to allow connection from outside the container
    uvicorn.run(app, host="0.0.0.0", port=port)
