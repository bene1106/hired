"""Application services. Business logic that sits between API routes and the
LLM/DB layers. Routes call services; services call ``backend.llm`` and
``backend.db``.
"""
