import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="dcos-deploy",
    version="0.1.0",
    author="MaibornWolff",
    description="Deploy and orchestrate DC/OS services and apps",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="dcos marathon mesos",
    license='Apache 2.0',
    url="https://github.com/MaibornWolff/dcos-deploy/",
    packages=["dcosdeploy", "dcosdeploy.commands", "dcosdeploy.adapters", "dcosdeploy.modules"],
    python_requires=">=3.5",
    install_requires=[
        "PyYaml>=3.13",
        "pystache>=0.5.4",
        "click>=6.7",
        "requests>=2.20.1",
        "minio>=4.0.6",
        "cryptography>=2.4.2",
    ],
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
