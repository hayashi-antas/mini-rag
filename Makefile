ingest:
	op run --env-file=secrets.env.tpl -- env $$(cat config.env | xargs) python -m rag.ingest

chat:
	op run --env-file=secrets.env.tpl -- env $$(cat config.env | xargs) python -m rag.chat

web:
	op run --env-file=secrets.env.tpl -- env $$(cat config.env | xargs) uvicorn rag.api:app --reload --port 8000

.PHONY: ingest chat web
