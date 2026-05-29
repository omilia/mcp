# Add Knowledge to an Agent

Give an existing agent a FAQ-style knowledge base, either by ingesting a URL
through Pathfinder or by attaching an existing knowledge base.

## Path A — From a URL

1. **Make sure a Pathfinder project exists**

   ```
   list_pathfinder_projects(search_term="<name>")
   ```

   If none, create one:

   ```
   create_pathfinder_project(name="<ProjectName>", group="<group>")
   ```

   Keep the project `id` as `pathfinder_project_id`.

2. **Ingest the URL and attach it to the agent**

   ```
   add_faq_to_agent(
       url="https://docs.example.com/faq",
       pathfinder_project_id="<pathfinder_project_id>",
       agent_id="<agent_id>",
   )
   ```

   This ingests the page (one level deep), creates a FAQ vector store, and
   attaches it to the agent as a sub-agent.

3. **Deploy and test**

   ```
   deploy_orc_app(app_id="<app_id>")
   talk_to_app(app_id="<app_id>", message="<question covered by the FAQ>")
   ```

## Path B — Attach an existing knowledge base

1. **Find the knowledge base ID**

   ```
   list_knowledge_bases()
   ```

2. **Attach it**

   ```
   add_knowledge_base_to_agent(
       agent_id="<agent_id>",
       knowledge_base_id="<kb_id>",
   )
   ```

3. **Deploy and test** (same as Path A step 3).

## Common pitfalls

- `add_faq_to_agent` requires `agent_id` (not `component_id`). Use
  `get_agent_from_component_id` if you only have a component ID.
- Pathfinder ingestion is asynchronous. The tool returns once the vector
  store is created, but search quality improves as indexing completes.
- The agent attached via FAQ is named `Pathfinder.<faq_id>` — visible
  inside the Concierge's sub-agent list.
