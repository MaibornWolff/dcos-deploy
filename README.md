# dcos-deploy

dcos-deploy is a command line tool that helps you to deploy and manage groups of services and apps on [DC/OS](https://dcos.io). It acts as an orchestration engine on top of the existing DC/OS tools and APIs to install, configure and update frameworks, marathon apps and metronome jobs. It is based on a yaml-configuration file which describes the services that you want. It will read this file and execute any changes necessary so that your DC/OS cluster reflects your desired configuration.

For example: To deploy a complete elasticsearch stack on your cluster you would typically need to install the elasticsearch framework from the DC/OS universe, a kibana app, expose both to your loadbalancer and add some regular jobs for backups and cleanup. Additionally if you run elasticsearch with x-pack or searchguard installed you also need to create a public-private keypair, service-account and secret for your framework. This amounts to quite a number of steps. With dcos-deploy you just describe your entire stack in one simple yaml file and let dcos-deploy do the rest. See the examples folder for more.

(!) This tool is under heavy development. Use in production environments at your own risk.

## Features

* Handles the following "entities":
  * DC/OS packages
  * Marathon apps
  * Metronome jobs
  * secrets
  * serviceaccounts
  * public-private-keypairs (for use in secrets)
  * [Edge-LB](https://docs.mesosphere.com/services/edge-lb/)
  * [S3](https://aws.amazon.com/s3/) files
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
* Frameworks/packages with more complicated update procedures (like Edge-LB) are at the moment not fully supported.


## Requirements
* A DC/OS cluster with version >= 1.11 (for features like secrets an EE cluster is needed)
* dcos-cli installed  and connected to your cluster (to verify it works run `dcos node` and it should display a list of nodes in your cluster)

If you want to run it from source, aditionally you need:
* Python >= 3.5
* Python modules from `requirements.txt`

## Installation
There are several ways to install dcos-deploy:
* Binary
  * Download the binary for your system from the Releases page
  * Make the file executable and copy it into a folder inside your path
* Install from pypi (`pip install dcos-deploy`)
* Run from source
  * Clone this github repository to your system (for a stable release checkout a release tag)
  * Install all requirements from `requirements.txt` (optional: use a virtualenv to keep your system clean)
  * Optional: Create a symlink of `dcos-deploy` to a folder in your exectuable path (e.g. `ln -s $(pwd)/dcos-deploy ~/usr/bin/dcos-deploy`)

## Usage
* Create your `dcos.yml` (start from scratch or use one of the examples). You should separate your stack into groups and create a `dcos.yml` for each of them (e.g. one for all hdfs related services, one for all elastic related and so on) to keep the complexity manageable.
* Run `dcos-deploy apply`.
* See `dcos-deploy apply --help` for all options.

By default dcos-deploy will use the authentication information from the dcos-cli, so make sure you are logged in (verify by running `dcos node`, if it works you should see a list of nodes in your cluster). If you want to run dcos-deploy without the dcos-cli installed, you must provide the necessary information via the environment variables `DCOS_BASE_URL` (set this to the public ur of your master) and `DCOS_AUTH_TOKEN` (set this to a valid auth token).


## Config file syntax
The config file is written as a yaml file. The root level consists of key/value-pairs (a dictionary). Each key represents the unique name for one entity, the value is again a dictionary with all the options for that entity.

### Meta fields
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
  var4:
    env: MY_VAR4  # Variables can also be read from the environment
    required: True
  var5:
    file: myvalue.txt  # The value of the variable will be the content of the file. Can be useful to provide longer values
    encode: base64  # This will encode the value using base64. Some DC/OS frameworks have config options that require base64-encoded values. Using this option the value can be kept in clear-text and will be automatically encoded by dcos-deploy when rendering the options file for the framework.
```

Variables can be used via [Mustache](http://mustache.github.io/) templates in most options and in marathon app definitions and package options. See `examples/elastic` for usage examples. You can not use variables in entity names or outside option strings (ground rule: the yaml file must be syntactically correct without mustache template rendering).

### Encryption
dcos-deploy supports encrypting files so that sensitive information is not stored unencrypted. Files are symmetricly encrypted using [Fernet](https://cryptography.io/en/latest/fernet/) (AES-128) from the python [cryptography](https://cryptography.io/en/latest/) library.
In most places where you provide a filename (at the moment not possible with `s3file`) you can use encrypted files by using the following syntax as filename: `vault:<encryption-key>:<filename-to-encrypted-file>`.
You should use a variable for the encryption key.

Example:
```
variables:
  encryption_key:
    env: ENCRYPTION_KEY
    required: True

servicepasswords:
  type: secret
  path: /myservice/passwords
  file: vault:{{encryption_key}}:servicepasswords.encrypted
```

dcos-deploy has several util commands that help you in creating encrypted files:
* `dcos-deploy vault generate-key`: Generates a new key that you can use for encrypting files
* `dcos-deploy vault encrypt`: Encrypts a file using a given key
* `dcos-deploy vault decrypt`: Decrypts a file using a given key

Example usage:
```
$ echo "supersecret" > servicepasswords
$ dcos-deploy vault generate-key
Your new key: 6htLemxXcEXnahVl1aZI6Aa3TXIHmbE8abtibC2iO6c=
Keep this safe.
$ export ENCRYPTION_KEY="6htLemxXcEXnahVl1aZI6Aa3TXIHmbE8abtibC2iO6c="
$ dcos-deploy vault encrypt -i servicepasswords -o servicepasswords.encrypted -e ENCRYPTION_KEY
$ cat servicepasswords.encrypted
gAAAAABb9rkSdEqT1xn0w5G5ipjPH6Vd5TsUfDLAWnN7I8FXTOPK6t1tMUstm8nA_yiA6SV5B1Blxj1h-xqCl8VqqbH7D7RF9Q==
$ dcos-deploy vault decrypt -i servicepasswords.encrypted -o servicepasswords.clear -e ENCRYPTION_KEY
$ cat servicepasswords.clear
supersecret
```

To use encrypted files with includes make sure that the variable for the encryption key is either defined in the file itsself or in an included file that is read before the encrypted one.


### Entity
Each entity has the same structure and some common options:
```
entityname:
  type: foo
  only:
    var1: foo
  except:
    var2: bar
  dependencies:
    - otherentity
```

`type` defines what kind of entity this is. Currently implemented are
* `app`
* `framework`
* `job`
* `account`
* `secret`
* `cert`
* `repository`
* `edgelb`
* `s3file`
* `taskexec`
See their respective sections below for details.

`only` and `except` take key/value-pairs of variable names and values. These are evaluated when reading the config file based on all provided and default variables. The entity is excluded if one of the variables in the `only` section does not have the value specified or if one of the variables in the `except` section has the specified value. In the example above the entity is only included if `var1 == foo` and `var2 != bar`. If a variable in the `only` section is not defined (no default value) the condition is treated as false and the entity is ignored.

`dependencies` takes a list of entity names that this entity depends on. Optionally the dependency type can be provided. Currently supported are `create` (default) and `update`. They can be defined by adding a colon after the entity name and then the type (e.g. `otherentity:create`). A `create` dependency is only honored during creation time of an entity and means that the entity will only be created after all its dependencies have been successfully created (e.g. a service account for a framework). An update dependency extends the `create` dependency and is currently only honored by the `marathon` module. If during an apply-operation a dependency of a marathon app is changed (e.g. a secret) and the app has no changes it will be restarted.

### Marathon app
`type: app` defines a marathon app. It has the following specific options:
* `path`: id of the app. If not specified the `id` field of the marathon app definition is used. Variables can be used.
* `marathon`: path to the marathon app definition json file. Required. Variables can be used in the path and in the json file itsself.
* `extra_vars`: key/value-pairs of of extra variables and values to be used when rendering the app definition file.

If you want to start several apps from the same basic app definition, there is a meta option to allow this:
```
mymultiapp:
  type: app
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

If not defined marathon will add a number of default fields to an app definition. dcos-deploy tries to detect these defaults and exclude them when checking for changes between the local definition and the one known to marathon. This is rather complex as these default values partly depend on several modes (network, container type, etc.). If you find a case where dcos-deploy falesly reports a change please open an issue at the github project and attach your app definition and the definition reported by marathon (via `dcos marathon app show <app-id>`).

### Framework
`type: framework` defines a DC/OS framework. It has the following specific options:
* `path`: name of the framework. If not specified the `service.name` field of the package options are used. Variables can be used.
* `package`:
  * `name`: name of the package in the DC/OS universe. This is the same as used when installing a package via the cli (`dcos package install <packagename>`). Required. Variables can be used.
  * `version`: version of the package. This is the same as used when installing a package via the cli (`dcos package install <packagename> --package-version=<version>`). Required. Variables can be used.
  * `options`: Path to the json options file to configure the package. Required. Variables can be used in the path and in the json file itsself.

These options correspond to the parameters provided when installing a package via the dcos-cli: `dcos package install <packagename> --package-version=<version> --options=<options.json>`.

During installation of a package dcos-deploy will wait until the service is completely installed (specifically it waits until the service scheduler reports `COMPLETE` for the `deploy` plan). If you are installing Edge-LB waiting is disabled. Instead the pool update will wait until the Edge-LB API is available.
Any change in the options file or in the package version will trigger an update (the same as doing `dcos <framework> update start --package-version=<version> --options=<options.json>`). dcos-deploy will not wait for the completion of the update as it assumes that any updates are done in a rolling-restart fashion.

### Metronome job
`type: job` defines a metronome job. It has the following specific options:
* `path`: id of the job. If not specified the `id` field of the job definition is used. Variables can be used.
* `definition`: path to the metronome job definition json file. Required. Variables can be used in the path and in the json file itsself.

### Secret
`type: secret` defines a secret. This can only be used on EE clusters. It has the following specific options:
* `path`: path for the secret. Required. Variables can be used.
* `value`: Value for the secret. Variables can be used. Either this or `file` is required.
* `file`: Path to a file. The content of the file will be used as value for the secret. Either this or `value` is required.
* `render`: Wether to render the file content with mustache. Use if your file contains variables. Boolean. Defaults to False.

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

### Package repository
`type: repository` defines a package repository. It has the following specific options:
* `name`: name of the repository. Required. Variables can be used.
* `uri`: uri for the repositroy. Required. Variables can be used.
* `index`: at what index to place the repository in the repository list. 0 for beginning. Do not set for end of list.

With this type you can add additional package repositories to DC/OS. You can for example use it to add the Edge-LB repositories to your EE cluster. Set the repository as a dependency for any frameworks/packages installed from it.

### Edge-LB pool
`type: edgelb` defines an edgelb pool. This can only be used on EE clusters. It has the following specific options:
* `name`: name of the pool. Taken from pool config if not present. Variables can be used.
* `pool`: filename to the yaml file for configuring the pool. Required. The filename itsself and the yaml file can contain variables.

For configuring a pool see the [Edge-LB configuration](https://docs.mesosphere.com/services/edge-lb/1.2/pool-configuration/).

For this to work you must have the edgelb package installed via the repository URLs provided by Mesosphere (use the `repository` and `package` types, there is a [complete example](examples/edgelb) available).
At the moment dcos-deploy can not safely detect if the pool config was changed so it will always apply it. Be aware that changing certain options in the pool config (like ports or secrets) will result in a restart of the haproxy instances. Make sure you have a HA setup so that there is no downtime.

### S3 File
`type: s3file` defines a file to be uploaded to S3-compatible storage. If you are not running on AWS you can use [Minio](https://minio.io/) or any other storage service with an s3-compatible interface. This entitiy is designed to provide files for apps / services (via the fetch mechanism) that are either too big or otherwise not suited for storage as secrets (for example plugins for a service). It has the following specific options:
* `server`:
  * `endpoint`: endpoint of your s3-compatible storage. If you use AWS S3 set this to your region endpoint (e.g. `s3.eu-central-1.amazonaws.com`). Required. Variables can be used.
  * `access_key`: your access key. Required. Variables can be used. For security reasons you should provide the value via environment variable. Make sure the iam user associated with these credentials has all rights for retrieving and uploading objects (`s3:Get*` and `s3:Put*`).
  * `secret_key`: your secret access key. Required. Variables can be used. For security reasons you should provide the value via environment variable.
* `source`: path to your file or folder to be uploaded to s3. Should be relative to the `dcos.yml` file. Required. Variables can be used.
* `destination`:
  * `bucket`: name of the bucket to use. Required. Variables can be used.
  * `key`: key to store the file(s) under. Required. Variables can be used.
* `compress`: type of compressed archive to combine the files in. Currently only supported is `zip`. Optional. Variables can be used.

This entity has several modes of operation:

* Upload a single file: `source` points to a file, `compress` is not set. The file is uploaded and `destination.key` is used as name.
* Upload a folder: `source` points to a folder, `compress` is not set. All files and folders under `source` are recursively uploaded. `destination.key` is used as prefix.
* Upload a folder as a zip file: `source` points to a folder, `compress: zip`. The files and folders under `source` are compressed into a zip file and uploaded. `destiation.key` is used as name of the zip file.

Changes to the uploaded files are detected by comparing md5 hashsums, which are stored as metadata with the object in S3. Only changed files will be uploaded. If you try to manage files that were already uploaded some other way, on the first run they will be detected as changed (due to the missing hash value metadata) and reuploaded. For comparing hashsums for files to be uploaded in compressed form the tool will temporarily create the zip file to calculate the hashsum.

For multi-file upload: If `source` does not end in a slash, the last part of the name will be used as base folder: For `source: files/foo` and `destination.key: bar`, all files will under foo be uploaded as `bar/foo/<filename>`. In contrast if `source: files/foo/`, all files will be uploaded as `bar/<filename>`.

To use your S3 bucket to serve files to apps and services you must configure it for anonymous read access. For security reasons you should restrict that access to the IP range of your cluster. See the [AWS S3 documentation](https://docs.aws.amazon.com/AmazonS3/latest/dev/s3-access-control.html) for details.
Creating and configuring the bucket is outside the scope of this tool.

To make sure a marathon app that uses s3 files is made aware of changes to the uploaded files, you should set the `s3file` entity as an `update` dependency to the `app` entity. dcos-deploy will restart the app whenever the uploaded file changes.

If you run `apply` with `--debug` dcosdeploy will download already existing files from s3 and print the differences between the local and remote version in the unified diff format. So only use `--debug` for textual files.

### Task exec
`type: taskexec` allows to execute commands inside tasks. This is primarily meant to trigger configuration reloads on services that can do some sort of hot-reload as to avoid restarting a service. It has the following specific options:
* `task`: task identifier to uniquely identify the task. Can be part of a task name. Required. Variables can be used.
* `command`: command to execute in the task. Required. Variables can be used.
* `print`: boolean. Wether to print the output of the executed command. Optional. Defaults to false.

This has the same effect as running `dcos task exec <task> <command>`.

As dcos-deploy has no state it cannnot detect if this command has been run before. As such it will run this command every time `apply` is called. You must either make the command idempotent so that running it multiple times is possible without changing the result, or (recommended) add dependencies (with `:update`) to it and add `when: dependencies-changed`. That way the command will only be executed when one of its dependencies has been changed.

Example for this is: Uploading configuration files to S3 and triggering a redownload of the files into the service by a command. See [examples](examples/demo) for details.


## Deployment process
When running the `apply` command dcos-deploy will first check all entities if they have changed. To do this it will first render all options and files using the provided variables, retrieve the currently running configurations from the DC/OS cluster using the specific APIs (e.g. get the app definition from marathon) and compare them. It will print a list of changes and ask for confirmation (unless `--yes` is used). If an entity needs to be created it will first recursively create any dependencies.
There is no guaranteed order of execution. Only that any defined dependencies will be created before the entity itsself is created.

The deployment process has some specific restrictions:
* Names/paths/ids may not be changed.
* Options files for frameworks, apps and jobs are not verified for structural correctness. If the new file is not accepted by the API an error will be thrown.
* For frameworks dcos-deploy does not verify beforehand if a version update is supported by the framework. If the framework does not accept the new version an error will be thrown.
* An already created `cert` entity will not be changed if the `dn` or `hostnames` fields change.
* Dependencies must be explicitly defined in the `dcos.yml`. Implicit dependencies (like a secret referenced in a marathon app) that are not explicitly stated are not honored by dcos-deploy.


## Roadmap
* Add as package to the Mesosphere universe for easy installation as a module for the dcos-cli
* Support more DC/OS services like Edge-LB
* Better and documented plugin support
* Provide some sort of verification for configurations


## Contributing
If you found a bug or have a feature request, please open an issue in Github.
