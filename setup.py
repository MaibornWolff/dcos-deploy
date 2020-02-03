import setuptools

with open("README.md", "r") as f:
    long_description = f.read()


def read_requirements():
    with open("requirements.txt") as req_file:
        lines = req_file.read().split("\n")
    for line in lines:
        if line.startswith("#"):
            continue
        yield line.strip()


setuptools.setup(
    name="dcos-deploy",
    version="0.3.0",
    author="MaibornWolff",
    description="Deploy and orchestrate DC/OS services and apps",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="dcos marathon mesos",
    license='Apache 2.0',
    url="https://github.com/MaibornWolff/dcos-deploy/",
    packages=["dcosdeploy", "dcosdeploy.commands", "dcosdeploy.adapters", "dcosdeploy.modules", "dcosdeploy.config", "dcosdeploy.util"],
    python_requires=">=3.5",
    install_requires=list(read_requirements()),
    classifiers=[
        'License :: OSI Approved :: Apache Software License',
        'Environment :: Console',
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    entry_points={
        'console_scripts': [
            'dcos-deploy = dcosdeploy.commands.all:maingroup',
        ],
    }
)
