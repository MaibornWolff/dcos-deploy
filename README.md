# dcos-deploy

dcos-deploy is a command line tool that helps you to deploy and manage groups of services and apps on [DC/OS](https://dcos.io). It acts as an orchestration engine on top of the existing tools and APIs of DC/OS to install, configure and update frameworks, marathon apps and metronome jobs. At its core is a yaml-configuration file that describes the services that you want. It will read this file and execute any changes necessary so that your DC/OS cluster reflects your desired configuration.

For example: To deploy a complete elasticsearch-stack on your cluster you would typically need to install the elastic framework from the universe, a kibana app, expose both to your loadbalancer and add some regular jobs for backups or cleanup. Additionally if you run elasticsearch with x-pack or searchguard installed you also need to create a public-private keypair, service-account and secret for your framework to make it work. This amounts to quite a number of steps. With dcos-deploy you just describe your entire stack in one simple yaml-file and let it do the rest. See the examples folder for more.

(!) This tool is under heavy development and is not yet stable enough for production environments. Use at your own risk.


## Features
* Handles
  - DC/OS packages
  - Marathon apps
  - Metronome jobs
  - secrets
  - servic-eaccounts
  - public-private-keypairs (for use in secrets)
* For packages it handles version updates and configuration changes.
* Handles install and update dependencies between entities (e.g. a framework is only installed after its service-account is created, an app is restarted if an attached secret changes).
* Parameterise your configuration using variables (e.g. to support different instances of a service).
* Stateless: There is no local or remote state. Everything needed is pulled directly from the cluster.
* No backend: dcos-deploy is a client-only tool that directly uses the existing DC/OS APIs to access your DC/OS cluster and does not need its own backend service.
* Uses your installed dcos-cli to figure out how to talk to your cluster. No extra configuration needed.
* dry-run mode: Check which changes would be done.
* Can be extended with extra modules.


### Limitations
* Deleting packages/apps/jobs is not supported: Since dcos-deploy does not keep a state it cannot detect if you remove a service/app/job from its configuration. Therefore you are responsible to delete any no longer wanted entities yourself.
* Can not safely detect changes in marathon apps and metronome jobs: Due do default configuration options being added by marathon/metronome, dcos-deploy can at the moment not predict beforehand if a app/job will be changed.


## Requirements
* Python >= 3.5
* dcos-cli installed and connected to your cluster
* See `requirements.txt` for needed python modules
* Tested with DC/OS 1.11 EE


## Installation
* Clone this github repository to your system.
* Install all requirements (optional: use a virtualenv to keep your system clean)
* Optional: Create a symlink of dcos-deploy to a folder in your exectuable path (e.g. `ln -s $(pwd)/dcos-deploy ~/usr/bin/dcos-deploy`)


## Usage
* Create your `dcos.yml` (start from scratch or use one of the examples)
* Run `dcos-deploy apply`


## Roadmap
* Provide binaries for all plattforms
* Add as package to the Mesosphere universe for easy installation as a module for the dcos-cli
* Support more DC/OS services like Edge-LB
* Better and documented plugin support


## Contributing
If you found a bug or have a feature request, please open an issue in Github.
