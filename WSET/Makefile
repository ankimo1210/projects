PYTHON ?= python3
DESTINATION ?= platform=iOS Simulator,name=iPhone 17 Pro
DERIVED_DATA ?= /tmp/wset-derived
XCODEBUILD = xcodebuild -project WSET.xcodeproj -scheme WSET \
	-destination '$(DESTINATION)' -derivedDataPath $(DERIVED_DATA) \
	CODE_SIGNING_ALLOWED=NO -parallel-testing-enabled NO

.PHONY: verify release-check test test-python check-generated test-unit test-ui

verify: test-python check-generated

test-python:
	$(PYTHON) -m unittest \
		scripts.tests.test_build_question_pack \
		scripts.tests.test_build_reference_pack \
		scripts.tests.test_build_written_question_pack \
		scripts.tests.test_build_region_map_pack \
		scripts.tests.test_build_content_review_packet \
		scripts.tests.test_validate_ai_review_fixture \
		scripts.tests.test_validate_free_content_manifest \
		scripts.tests.test_validate_release_readiness

check-generated:
	$(PYTHON) scripts/build_question_pack.py --check
	$(PYTHON) scripts/build_reference_pack.py --check
	$(PYTHON) scripts/build_written_question_pack.py --check
	$(PYTHON) scripts/build_region_map_pack.py --check
	$(PYTHON) scripts/build_content_review_packet.py --check
	$(PYTHON) scripts/validate_ai_review_fixture.py
	$(PYTHON) scripts/validate_free_content_manifest.py

release-check: verify
	$(PYTHON) scripts/validate_release_readiness.py

test-unit:
	$(XCODEBUILD) test -only-testing:WSETTests

test-ui:
	$(XCODEBUILD) test -only-testing:WSETUITests

test: verify test-unit test-ui
