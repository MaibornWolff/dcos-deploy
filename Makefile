
.PHONY: clean test binary dist release-pypi coverage coverage-html
.DEFAULT_GOAL := test

clean:
	rm -rf build dist
	find . -name '*.pyc' -exec rm --force {} +
	find . -name '__pycache__' -exec rm -rf {} +

test:
	@python3 -m unittest discover -s tests -p "*_test.py"

coverage:
	@coverage run --source=dcosdeploy -m unittest discover -s tests -p "*_test.py"
	@coverage report

coverage-html:
	@coverage run --source=dcosdeploy -m unittest discover -s tests -p "*_test.py"
	@coverage html

binary:
	@pyinstaller dcos-deploy -F -n dcos-deploy \
	--hidden-import dcosdeploy.modules.accounts \
	--hidden-import dcosdeploy.modules.secrets \
	--hidden-import dcosdeploy.modules.jobs \
	--hidden-import dcosdeploy.modules.apps \
	--hidden-import dcosdeploy.modules.frameworks \
	--hidden-import dcosdeploy.modules.certs \
	--hidden-import dcosdeploy.modules.repositories \
	--hidden-import dcosdeploy.modules.edgelb \
	--hidden-import dcosdeploy.modules.s3 \
	--hidden-import dcosdeploy.modules.taskexec \
	--hidden-import dcosdeploy.modules.httpcall \
	--hidden-import dcosdeploy.modules.iam_groups \
	--hidden-import dcosdeploy.modules.iam_users \
	--hidden-import dcosdeploy.modules.marathon_groups

dist:
	@python3 setup.py sdist

release-pypi:
	@twine upload -r pypi dist/dcos-deploy-*.tar.gz
