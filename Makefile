SHELL := /bin/bash
.PHONY: doctor read-gdk audit-gdk build rebuild clean-build up hello demo-mock test verify logs down
doctor:
	./scripts/doctor.sh
read-gdk:
	python3 scripts/gdk_docs.py fetch
audit-gdk:
	python3 scripts/gdk_docs.py audit
build:
	python3 scripts/manage.py build
rebuild clean-build:
	python3 scripts/manage.py clean-build
up:
	python3 scripts/manage.py up
hello:
	python3 scripts/manage.py hello
demo-mock:
	./scripts/verify_mock.sh demo-mock
test:
	python3 scripts/manage.py test
verify:
	./scripts/verify_mock.sh verify
logs:
	python3 scripts/manage.py logs
down:
	python3 scripts/manage.py down

.PHONY: sdk-fetch sdk-inspect build-gdk sdk-smoke verify-software
sdk-fetch:
	python3 scripts/sdk_tools.py fetch
sdk-inspect:
	python3 scripts/sdk_tools.py inspect
build-gdk:
	python3 scripts/sdk_tools.py build
sdk-smoke:
	python3 scripts/sdk_tools.py smoke
verify-software:
	python3 scripts/manage.py test
	python3 scripts/manage.py verify
	python3 scripts/manage.py verify
	python3 scripts/check_runner_cleanup.py --also-launch-checks

.PHONY: sim-doctor fetch-model build-sim rebuild-sim sim-up sim-hello demo-sim test-sim verify-sim record-sim sim-logs sim-down
sim-doctor:
	python3 scripts/sim_manage.py doctor
fetch-model:
	python3 scripts/fetch_g2_model.py $(if $(filter yes,$(ACCEPT_MODEL_LICENSE)),--accept-noncommercial-license,)
build-sim:
	python3 scripts/sim_manage.py build
rebuild-sim:
	python3 scripts/sim_manage.py build --no-cache
sim-up:
	python3 scripts/sim_manage.py up
sim-hello:
	@if [ -f .artifacts/visual-session.json ]; then python3 scripts/ui_manage.py hello; else python3 scripts/sim_manage.py hello; fi
demo-sim:
	python3 scripts/sim_manage.py demo
test-sim:
	python3 scripts/sim_manage.py test
verify-sim:
	python3 scripts/sim_manage.py verify
record-sim:
	python3 scripts/sim_manage.py record
sim-logs:
	python3 scripts/sim_manage.py logs
sim-down:
	python3 scripts/sim_manage.py down

.PHONY: prepare-model model-tools demo-visual ui-info telemetry ui-down record-visual check-visual package-source verify-release
model-tools:
	python3 scripts/prepare_model.py --build-only
prepare-model:
	python3 scripts/prepare_model.py $(if $(filter yes,$(ACCEPT_MODEL_LICENSE)),--accept-noncommercial-license,)
demo-visual:
	python3 scripts/ui_manage.py up
ui-info:
	python3 scripts/ui_manage.py info
telemetry:
	python3 scripts/ui_manage.py telemetry
ui-down:
	python3 scripts/ui_manage.py down
record-visual:
	python3 scripts/ui_manage.py record
check-visual:
	python3 scripts/ui_manage.py check
package-source:
	python3 scripts/release.py package
verify-release:
	python3 scripts/release.py verify --archive "$(ARCHIVE)" $(if $(filter yes,$(ACCEPT_MODEL_LICENSE)),--accept-noncommercial-license,)
