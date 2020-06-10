import setuptools

with open("README.md", "r") as f:
    long_description = f.read()


install_requires = [
    "PyYaml==5.3.1",
    "pystache==0.5.4",
    "click==7.1.2",
    "requests==2.22.0",
    "minio==5.0.10",
    "cryptography==2.9.2",
    "PyJWT==1.7.1",
    "oyaml==0.9",
    "colorama==0.4.3",
]


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
    install_requires=install_requires,
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
