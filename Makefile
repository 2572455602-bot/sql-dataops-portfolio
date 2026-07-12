SHELL := /bin/bash
PYTHON := .venv/bin/python
STREAMLIT := .venv/bin/streamlit
DATA_DIR ?=
DEMO_USERS ?= 5000
ECOMMERCE_DATA_DIR := $(value DATA_DIR)
ECOMMERCE_DEMO_USERS := $(value DEMO_USERS)
export ECOMMERCE_DATA_DIR ECOMMERCE_DEMO_USERS

.PHONY: bootstrap smoke demo full test dashboard pages package recording-demo clean-runtime

bootstrap:
	./scripts/bootstrap_macos.sh

smoke:
	$(PYTHON) -m ecommerce_dataops.smoke

demo:
	$(PYTHON) -m ecommerce_dataops.cli demo --users "$${ECOMMERCE_DEMO_USERS}"

full:
	@test -n "$${ECOMMERCE_DATA_DIR}" || (echo "DATA_DIR is required. Example: make full DATA_DIR=/absolute/path/dataset" && exit 2)
	$(PYTHON) -m ecommerce_dataops.cli full --data-dir "$${ECOMMERCE_DATA_DIR}"

test:
	$(PYTHON) -m pytest -q --basetemp=.pytest-tmp

dashboard:
	$(STREAMLIT) run dashboard/app.py --server.address=127.0.0.1 --server.port=8501 --browser.gatherUsageStats=false

pages:
	$(PYTHON) scripts/build_pages_site.py

package:
	$(PYTHON) scripts/build_portfolio_zip.py

recording-demo:
	./scripts/recording_demo.sh

clean-runtime:
	rm -rf artifacts spark-warehouse metastore_db derby.log bi_exports/.candidate-* bi_exports/.previous-* bi_exports/.current-link-*
