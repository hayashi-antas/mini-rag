ingest:
	op run --env-file=secrets.env.tpl -- env $$(cat config.env | xargs) python -m rag.ingest

chat:
	op run --env-file=secrets.env.tpl -- env $$(cat config.env | xargs) python -m rag.chat
