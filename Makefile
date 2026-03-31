dev-api:
	PYTHONPATH=packages/newgeo_core uvicorn api.app.main:app --reload

dev-worker:
	PYTHONPATH=packages/newgeo_core python3 -m workers.app.worker

test:
	PYTHONPATH=packages/newgeo_core python3 -m unittest discover -s api/tests -v

seed:
	PYTHONPATH=packages/newgeo_core python3 scripts/seed_demo.py

