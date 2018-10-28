
.PHONY: clean test binary
.DEFAULT_GOAL := test

clean:
	rm -rf build dist
	find . -name '*.pyc' -exec rm --force {} +
	find . -name '__pycache__' -exec rm -rf {} +

test:
	@python3 -m unittest discover -s tests -p "*_test.py"

binary:
	pyinstaller dcos-deploy.py -F -n dcos-deploy \
	--hidden-import dcosdeploy.modules.accounts \
	--hidden-import dcosdeploy.modules.certs \
	--hidden-import dcosdeploy.modules.jobs \
	--hidden-import dcosdeploy.modules.secrets \
	--hidden-import dcosdeploy.modules.services
