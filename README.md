# dcos-deploy

dcos-deploy is a command line tool that helps you to deploy and manage groups of services and apps on [DC/OS](https://dcos.io). It acts as an orchestration engine on top of the existing DC/OS tools and APIs to install, configure and update frameworks, marathon apps and metronome jobs. It is based on a yaml-configuration file which describes the services that you want. It will read this file and execute any changes necessary so that your DC/OS cluster reflects your desired configuration.

For example: To deploy a complete elasticsearch stack on your cluster you would typically need to install the elasticsearch framework from the DC/OS universe, a kibana app, expose both to your loadbalancer and add some regular jobs for backups and cleanup. Additionally if you run elasticsearch with x-pack or searchguard installed you also need to create a public-private keypair, service-account and secret for your framework. This amounts to quite a number of steps. With dcos-deploy you just describe your entire stack in one simple yaml file and let dcos-deploy do the rest. See the examples folder for more.

(!) This tool is under heavy development and is not yet stable enough for production environments. Use at your own risk.

## Features
* Handles the following "entities":
  - DC/OS packages
  - Marathon apps
  - Metronome jobs
  - secrets
  - serviceaccounts
  - public-private-keypairs (for use in secrets)
* For DC/OS packages it supports version updates and configuration changes.
* Handles install and update dependencies between entities (e.g. a framework is only installed after its serviceaccount is created, an app is restarted if an attached secret changes).
* Parameterise your configuration using variables (e.g. to support different instances of a service).
* Stateless / no backend: There is no local or remote state. Everything needed is pulled directly from the cluster: dcos-deploy is a client-only tool that directly uses the existing DC/OS APIs to access your DC/OS cluster and does not need its own backend service.
* Uses your installed dcos-cli to figure out how to talk to your cluster. No extra configuration needed.
* dry-run mode: Check which changes would be done.
* partial deployment: Choose the entities to be deployed.
* Can be extended with extra modules (still in development).


### Limitations
* Deleting packages/apps/jobs is not supported: Since dcos-deploy does not keep a state it cannot detect if you remove a service/app/job from its configuration. Therefore you are responsible to delete any no longer wanted entities yourself.
* Can not safely detect changes in marathon apps: Due do default configuration options being added by marathon, dcos-deploy can at the moment not predict beforehand if an app will be changed.
* Frameworks that require special configuration after installation (like Edge-LB with its pool configuration) are not supported at the moment.


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
* Create your `dcos.yml` (start from scratch or use one of the examples). You should separate your stack into groups and create a `dcos.yml` for each of them (e.g. one for all hdfs related services, one for all elastic related and so on) to keep the complexity manageable.
* Run `dcos-deploy apply`.
* See `dcos-deploy apply --help` for all options.


## Config file syntax
The config file is written as a yaml file. The root level consists of key/value-pairs (a dictionary). Each key represents the unique name for one entity, the value is again a dictionary with all the options for that entity.

### Advanced features / meta fields
There are some meta fields for further configuation:
* `variables`: Define variables to be used in the rest of the file and in app definitions and package options. See the [Variables](#variables) section for more info.
* `includes`: Structure your config further by separating parts into different files and including them. Provide a list of filenames. The include files must be structured the same way as the main file. Each entity name must be unique over the base file and all included files.
* `modules`: Extend the features of dcos-deploy using external modules (still in development, not documented yet).

### Variables
To be more generic with your services you can use variables in certain places. All variables must be defined in the `variables` section of your config file.
```
variables:
  var1:
    required: True  # Required variables must be provided when calling dcos-deploy using the -e option (e.g. -e var1=foo)
  var2:
    required: False
    default: foobar  # If a variable is not provided by the user the default value is used. Variables without a default are treated as empty values
  var3:
    values:  # You can restrict the allowed values for a variable
      - foo
      - bar
      - baz
    default: bar
```

Variables can be used via [Mustache](http://mustache.github.io/) templates in most options and in marathon app definitions and package options. See `examples/elastic` for usage examples. You can not use variables in entity names or outside option strings (ground rule: the yaml file must be syntactically correct without mustache template rendering).

### Entity
Each entity has the same structure and some common options:
```
entityname:
  type: marathon
  only:
    var1: foo
  except:
    var2: bar
  dependencies:
    - otherentity
```

`type` defines what kind of entity this is. Currently implemented are `marathon`, `framework`, `job`, `account`, `secret` and `cert`. See their respective sections below for details.

`only` and `except` take key/value-pairs of variable names and values. These are evaluated when reading the config file based on all provided and default variables. The entity is excluded if one of the variables in the `only` section does not have the value specified or if one of the variables in the `except` section has the specified value. In the example above the entity is only included if `var1 == foo` and `var2 != bar`. If a variable in the `only` section is not defined (no default value) the condition is treated as false and the entity is ignored.

`dependencies` takes a list of entity names that this entity depends on. Optionally the dependency type can be provided. Currently supported are `create` (default) and `update`. They can be defined by adding a colon after the entity name and then the type (e.g. `otherentity:create`). A `create` dependency is only honored during creation time of an entity and means that the entity will only be created after all its dependencies have been successfully created (e.g. a service account for a framework). An update dependency extends the `create` dependency and is currently only honored by the `marathon` module. If during an apply-operation a dependency of a marathon app is changed (e.g. a secret) and the app has no changes it will be restarted.

### Marathon app
`type: marathon` defines a marathon app. It has the following specific options:
* `path`: id of the app. If not specified the `id` field of the marathon app definition is used. Variables can be used.
* `marathon`: path to the marathon app definition json file. Required. Variables can be used in the path and in the json file itsself.
* `extra_vars`: key/value-pairs of of extra variables and values to be used when rendering the app definition file.

If you want to start several apps from the same basic app definition, there is a meta option to allow this:
```
mymultiapp:
  type: marathon
  _template: marathon.json
  _vars: mymultiapp.yml
```

The `marathon.json` file is your normal app definition json file, paramerised with mustache variables. The `mymultiapp.yml` file has the following structure:
```
defaults: # optional, key/value-pairs of variables, can get overwritten in the instances section
  var1: foo
  var2: bar
instances:
  instance1:
    var1: baz
    var3: hello
  instance2:
    var3: world
```
For each key under `instances` dcos-deploy will create a marathon app from the template file specialized with the variables provided.

### Framework
`type: framework` defines a DC/OS framework. It has the following specific options:
* `path`: name of the framework. If not specified the `service.name` field of the package options are used. Variables can be used.
* `package`:
  * `name`: name of the package in the DC/OS universe. This is the same as used when installing a package via the cli (`dcos package install <packagename>`). Required. Variables can be used.
  * `version`: version of the package. This is the same as used when installing a package via the cli (`dcos package install <packagename> --package-version=<version>`). Required. Variables can be used.
  * `options`: Path to the json options file to configure the package. Required. Variables can be used in the path and in the json file itsself.

These options correspond to the parameters provided when installing a package via the dcos-cli: `dcos package install <packagename> --package-version=<version> --options=<options.json>`.

During installation of a package dcos-deploy will wait until the service is completely installed (specifically it waits until the service scheduler reports `COMPLETE` for the `deploy` plan). Any change in the options file or in the package version will trigger an update (the same as doing `dcos <framework> update start --package-version=<version> --options=<options.json>`). dcos-deploy will not wait for the completion of the update as it assumes that any updates are done in a rolling-restart fashion.

### Metronome job
`type: job` defines a metronome job. It has the following specific options:
* `path`: id of the job. If not specified the `id` field of the job definition is used. Variables can be used.
* `definition`: path to the metronome job definition json file. Required. Variables can be used in the path and in the json file itsself.

### Secret
`type: secret` defines a secret. This can only be used on EE clusters. It has the following specific options:
* `path`: path for the secret. Required. Variables can be used.
* `value`: Value for the secret. Variables can be used. Either this or `file` is required.
* `file`: Path to a file. The content of the file will be used as value for the secret. Either this or `value` is required.

### Serviceaccount
`type: serviceaccount` defines a serviceaccount. This can only be used on EE clusters. It has the following specific options:
* `name`: Name of the serviceaccount. Required. Variables can be used.
* `secret`: Path to use for the secret that contains the private key associated with the account. Required. Variables can be used.
* `groups`: List of groups the account should be added to. Optional. Variables can be used.
* `permissions`: Permissions to give to the account. Dictionary. Key is the name of the permission, value is a list of actions to allow. Variables are not supported.

This entity equates to the steps required to create a serviceaccount for a framework as described in the [DC/OS documentation](https://docs.mesosphere.com/1.12/security/ent/service-auth/custom-service-auth/).
Any groups or permissions not specified in the config are removed from the account during the update process.

Example:
```
type: serviceaccount
name: hdfs-service-account
secret: hdfs/serviceaccount-secret
permissions:
  "dcos:mesos:master:framework:role:hdfs-role":
    - create
  "dcos:mesos:master:reservation:role:hdfs-role":
    - create
    - delete
```

### X.509 certificate
`type: cert` is a special type that uses the [DC/OS CA API](https://docs.mesosphere.com/1.11/security/ent/tls-ssl/ca-api/) to create a public-private keypair, sign it with the internal DC/OS CA and provide the key and certificate as secrets. This can only be used on EE clusters. It has the following specific options:
* `cert_secret`: secret path to store the certificate. Required. Variables can be used.
* `key_secret`: secret path to store the key. Required. Variables can be used.
* `dn`: distinguished name to be used for the certificate. Requied. Variables can be used.
* `hostnames`:  List of hostnames to put in the certificate. Optional.

One example usecase for this is a service secured with TLS client certificate authentication (e.g. elasticsearch with x-pack or searchguard). You configure the service to accept client certificates signed by the cluster-internal DC/OS CA. Then using the `secret` entity provide appropriate certificates as secrets to your client services. The keys and certificates are securely kept inside the cluster and using the [path restrictions](https://docs.mesosphere.com/1.11/security/ent/#spaces-for-secrets) for secrets can only be accessed by authorized services.


## Deployment process
When running the `apply` command dcos-deploy will first check all entities if they have changed. To do this it will first render all options and files using the provided variables, retrieve the currently running configurations from the DC/OS cluster using the specific APIs (e.g. get the app definition from marathon) and compare them. It will print a list of changes and ask for confirmation (unless `--yes` is used). If an entity needs to be created it will first recursively create any dependencies.
There is no guaranteed order of execution. Only that any defined dependencies will be created before the entity itsself is created.

The deployment process has some specific restrictions:
* Names/paths/ids may not be changed.
* Options files for frameworks, apps and jobs are not verified for structural correctness. If the new file is not accepted by the API an error will be thrown.
* For marathon apps the change detection currently does not work safely (due to implicit default options from marathon) so it will always apply the new app definition.
* For frameworks dcos-deploy does not verify beforehand if a version update is supported by the framework. If the framework does not accept the new version an error will be thrown.
* An already created `cert` entitiy will not be changed if the `dn` or `hostnames` fields change.
* Dependencies must be explicitly defined in the `dcos.yml`. Implicit dependencies (like a secret referenced in a marathon app) that are not explicitly stated are not honored by dcos-deploy.


## Roadmap
* Provide binaries for all plattforms
* Add as package to the Mesosphere universe for easy installation as a module for the dcos-cli
* Support more DC/OS services like Edge-LB
* Better and documented plugin support
* Provide some sort of verification for configurations


## Contributing
If you found a bug or have a feature request, please open an issue in Github.
