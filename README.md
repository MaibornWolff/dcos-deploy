<p align="center"><img src="img/dcos-deploy-logo.png" alt="dcos-deploy" width="256"></p>

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

### Credentials

dcos-deploy has several ways to retrieve connection credentials for your DC/OS cluster:

* dcos-cli: By default dcos-deploy uses the authentication information from the dcos-cli, so make sure you are logged in (verify by running `dcos node`, if it works you should see a list of nodes in your cluster).
* Static token via environment variables: `DCOS_BASE_URL` (set this to the public URL of your master) and `DCOS_AUTH_TOKEN` (set this to a valid auth token). This way is handy for automation situations where you do not want to expose the admin username and password by adding them to your automation tool (e.g. Gitlab CI secrets). Instead you can provide the automation job with short-lived credentials.
* DC/OS serviceaccount secret: If you are running dcos-deploy from inside your DC/OS cluster (e.g. in a metronome job) you can also provide the credentials via a serviceaccount secret. To do that create a serviceaccount with superuser rights and expose its credentials secret to your service/job via the environment variable `DCOS_SERVICE_ACCOUNT_CREDENTIAL`. Also provide the variable `DCOS_BASE_URL` and set it to the internal URL of your master (should be `https://leader.mesos` in most cases).
* Username and Password via environment variables: `DCOS_BASE_URL` (set this to the public URL of your master), `DCOS_USERNAME` (username of a DC/OS admin user) and `DCOS_PASSWORD` (password of a DC/OS admin user).

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

Some variables are automatically provided by `dcos-deploy` based on your cluster. These are:

* `_cluster_version`: The DC/OS version of your cluster, for example `1.12.2`
* `_cluster_variant`: The DC/OS variant of your cluster, for example `enterprise`
* `_cluster_name`: The name of your cluster
* `_num_masters`: The number of masters in your cluster
* `_num_private_agents`: The number of private agents in your cluster (useful if you want to tailor the size of an app or framework node to the cluster size)
* `_num_public_agents`: The number of public agents in your cluster
* `_num_all_agents`: The number of public and private agents in your cluster

During rendering of entity configs some entity specific variables are available. These are:

* `_entity_name`: The name of the entity (the key of the yaml definition)
* `_pre_apply_script_hash`, `_pre_delete_script_hash`, `_post_apply_script_hash` and `_post_delete_script_hash`: md5-hashes of pre and post scripts if defined (see [Pre and post script](#pre-and-post-script))

### Global config

To specifiy an attribute for all entities of a specific type you can define it in the global config. The config for a specific entity will be merged with the global config for the corresponding type.

Example:

```yaml
global:
  s3file:
    server:
      endpoint: "{{s3_endpoint}}"
      access_key: "{{s3_access_key}}"
      secret_key: "{{s3_secret_key}}"
```

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
  file: "vault:{{encryption_key}}:servicepasswords.encrypted"
```

You can also specify the encryption key in the global config to avoid writing it for every occurence:
```
variables:
  encryption_key:
    env: ENCRYPTION_KEY
    required: True

global:
  vault:
    key: "{{encryption_key}}"

servicepasswords:
  type: secret
  path: /myservice/passwords
  file: vault::servicepasswords.encrypted
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

```yaml
entityname:
  type: foo
  only:
    var1: foo
  except:
    var2: bar
  state: removed
  dependencies:
    - otherentity
  loop:
    var3:
      - a
      - b
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
* `iam_group`
* `iam_user`
* `marathon_group`

See their respective sections below for details.

`only` and `except` take key/value-pairs of variable names and values. These are evaluated when reading the config file based on all provided and default variables. The entity is excluded if one of the variables in the `only` section does not have the value specified or if one of the variables in the `except` section has the specified value. In the example above the entity is only included if `var1 == foo` and `var2 != bar`. If a variable in the `only` section is not defined (no default value) the condition is treated as false and the entity is ignored.

`state` can be used to define a specific state for an entity. Currently only none (default, option is ignored) and `removed` are supported. By specifying `state: removed` the entity will be deleted if it exists. This can be useful in several ways. For example in air-gapped clusters the normally configured universe repository is not reachable and must be removed before other frameworks can be installed from local universes / package registries. This can be accomplished by defining the universe repo as an entity with `state: removed`.

`dependencies` takes a list of entity names that this entity depends on. Optionally the dependency type can be provided. Currently supported are `create` (default) and `update`. They can be defined by adding a colon after the entity name and then the type (e.g. `otherentity:create`). A `create` dependency is only honored during creation time of an entity and means that the entity will only be created after all its dependencies have been successfully created (e.g. a service account for a framework). An update dependency extends the `create` dependency and is currently only honored by the `marathon` module. If during an apply-operation a dependency of a marathon app is changed (e.g. a secret) and the app has no changes it will be restarted.

`loop` is very useful for describing multiple entities that are very similar. The values of the variables defined under `loop` will be extended into a cross product and for each combination an entity with these extra variables will be created. These extra variables can be used like normal variables to parametrize the entity. By default the entity name will be created by concatenating the given name with the values of all loop variables (in the example above these would be `entityname-a` and `entityname-b`). This can be overridden by using an entityname that has template parameters (for example `{{var3}}-myentity`).

### Pre and post script

In case you have need of more complex orchestrations for entities you can use `pre_script` and `post_script`. With these you can specify python scripts for the `apply` and the `delete` operations that will be executed before or respectively after the entitiy has been created/updated or deleted. They can be specified as follows:

```yaml
variables:
  post_script:
    file:
      path: my_script.py
      render: True

foobar:
  pre_script:
    apply: |
      print("Hello pre apply")
    delete: |
      print("Hello pre delete")
  post_script:
    apply: "{{{post_script}}}"
    delete: |
      print("Hello post delete")
```

If it is just a short snippet you can specify it inline, otherwise you can put the script into a file, read the file into a variable and just reference the variable. You can even use moustache templating in the scripts and dcos-deploy will render the template before executing the script.

The scripts are executed in the context of dcos-deploy, so you can import any dcosdeploy library functions that you need. Additonally during script execution the following globals are provided:

* `entity`: the entity config for the entity in question
* `entity_variables`: A dict of any entity_specific variables
* `variables`: An object that allows access to all defined variables (use `variables.get(name)` to get the value for a variable or `variables.render(text)` to render a moustache template)

**Important**: As the script is executed in the context of dcos-deploy it has access to the entire runtime state, including DC/OS authentication and all (encryped) variables. So only use scripts that you wrote yourself or from completely trusted sources.

If an entity has pre or post scripts defined, hash values for those scripts are provided as entity variables (`_pre_apply_script_hash`, `_pre_delete_script_hash`, `_post_apply_script_hash`, `_post_delete_script_hash`). These can be used to force an update with script execution of the entity whenever the script changes. In marathon apps you can e.g. put the variable in an environment variable or in a framework you can put it into an extra unused config option.


### Marathon app
`type: app` defines a marathon app. It has the following specific options:
* `path`: id of the app. If not specified the `id` field of the marathon app definition is used. Variables can be used.
* `marathon`: path to the marathon app definition json file. Required. Variables can be used in the path and in the json file itsself.
* `extra_vars`: key/value-pairs of of extra variables and values to be used when rendering the app definition file.

If you want to start several apps from the same basic app definition, there is a meta option to allow this:

```yaml
mymultiapp:
  type: app
  _template: marathon.json
  _vars: mymultiapp.yml
```

This option and `loop` can not be used at the same time.

The `marathon.json` file is your normal app definition json file, paramerised with mustache variables. The `mymultiapp.yml` file has the following structure:

```yaml
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

In both the `extra_vars` and the variables in the `instances` you can define dependent variables. The variable name must be in the form `<existing variable name>:<value to compare>`, and the value must be key-value pairs of variables. If `<existing variable name>` has value `<value to compare>` the variables defined under that key will be added to the variables for that entity, otherwise they will be discarded. A simple example:

```yaml
variables:
  env:
    required: True
  foo: something
myapp:
  type: app
  marathon: myapp.json
  extra_vars:
    env:test:
      foo: bar
    env:int:
      foo: baz
```

If `env` has value `test`, the variable `foo` will have value `bar`, if `env` has value `int`, the variable `foo` will have value `baz`, in neither of these cases `foo` will have value `something`.

If not defined marathon will add a number of default fields to an app definition. dcos-deploy tries to detect these defaults and exclude them when checking for changes between the local definition and the one known to marathon. This is rather complex as these default values partly depend on several modes (network, container type, etc.). If you find a case where dcos-deploy falesly reports a change please open an issue at the github project and attach your app definition and the definition reported by marathon (via `dcos marathon app show <app-id>`).

### Framework
`type: framework` defines a DC/OS framework. It has the following specific options:
* `path`: name of the framework. If not specified the `service.name` field of the package options are used. Variables can be used.
* `package`:
  * `name`: name of the package in the DC/OS universe. This is the same as used when installing a package via the cli (`dcos package install <packagename>`). Required. Variables can be used.
  * `version`: version of the package. This is the same as used when installing a package via the cli (`dcos package install <packagename> --package-version=<version>`). Required. Variables can be used.
  * `options`: Path to the json options file to configure the package. Required. Variables can be used in the path and in the json file itsself.

These options correspond to the parameters provided when installing a package via the dcos-cli: `dcos package install <packagename> --package-version=<version> --options=<options.json>`.

During installation of a package dcos-deploy will wait until the framework is installed. If the framework exposes the standard plan API (like all frameworks based on the [Mesosphere SDK](https://github.com/mesosphere/dcos-commons/), e.g. elastic, hdfs or kafka) dcos-deploy will also wait (with a timeout of 10 minutes) until the deploy-plan is complete.
Any change in the options file or in the package version will trigger an update (the same as doing `dcos <framework> update start --package-version=<version> --options=<options.json>`). dcos-deploy will not wait for the completion of the update as it assumes that any updates are done in a rolling-restart fashion.

### Metronome job

`type: job` defines a metronome job. It has the following specific options:

* `path`: id of the job. If not specified the `id` field of the job definition is used. Variables can be used.
* `definition`: path to the metronome job definition json file. Required. Variables can be used in the path and in the json file itsself.

The job definition is expected to be in the format used starting with DC/S 1.13. It is described in the [DC/OS 1.13 release notes](https://docs.d2iq.com/mesosphere/dcos/1.13/release-notes/1.13.0/#using-separate-json-files-for-job-scheduling).

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
* `permissions`: Permissions to give to the account. Dictionary. Key is the name of the permission (rid), value is a list of actions to allow. If a permission does not yet exist, it will be created. Variables can be used.

This entity equates to the steps required to create a serviceaccount for a framework as described in the [DC/OS documentation](https://docs.mesosphere.com/1.12/security/ent/service-auth/custom-service-auth/).
Any groups or permissions not specified in the config are removed from the account during the update process.

Example:

```yaml
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
* `hostnames`: List of hostnames to put in the certificate. Optional.
* `encoding`: Encoding to use for the private key (PEM, DER), default is PEM. Optional.
* `format`: Format to use for the private key (PKCS1, PKCS8), default is PKCS1. Optional.
* `algorithm`: Algorithm to use for the private key (RSA, ECDSA), default is RSA. Optional.
* `key_size`: Key size in bits to use for the private key. Default is 2048 for RSA and 256 for ECDSA. Optional.

One example usecase for this is a service secured with TLS client certificate authentication (e.g. elasticsearch with x-pack or searchguard). You configure the service to accept client certificates signed by the cluster-internal DC/OS CA. Then using the `cert` entity provide appropriate certificates as secrets to your client services. The keys and certificates are securely kept inside the cluster and using the [path restrictions](https://docs.mesosphere.com/1.11/security/ent/#spaces-for-secrets) for secrets can only be accessed by authorized services.

### Package repository
`type: repository` defines a package repository. It has the following specific options:
* `name`: name of the repository. Required. Variables can be used.
* `uri`: uri for the repositroy. Required. Variables can be used.
* `index`: at what index to place the repository in the repository list. 0 for beginning. Do not set for end of list.

With this type you can add additional package repositories to DC/OS. You can for example use it to add the Edge-LB repositories to your EE cluster. Set the repository as a dependency for any frameworks/packages installed from it.

### Edge-LB pool

`type: edgelb` defines an edgelb pool. This can only be used on EE clusters. It has the following specific options:

* `api_server`: path to the edgelb-api server if not installed at default location. Variables can be used. Optional. E.g. if you installed Edge-LB at `infra/edgelb` then use this for `api_server`.
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
  * `ssl_verify`: Set to false to disable ssl verifcation for s3 connection. Defaults to true. Optional.
  * `secure`: Set to false to use insecure http connections for s3 connection. Defaults to true. Optional.
* `source`: path to your file or folder to be uploaded to s3. Should be relative to the `dcos.yml` file. Required. Variables can be used.
* `destination`:
  * `bucket`: name of the bucket to use. Required. Variables can be used.
  * `key`: key to store the file(s) under. Required. Variables can be used.
  * `create_bucket`: Set to true to create bucket if it does not exist. Defaults to false. Optional.
  * `bucket_policy`: S3 bucket policy content. When bucket will be created because of `create_bucket: true` the policy will be applied. Optional.
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

### HttpCall

`type: httpcall` allows to make HTTP calls as part of deployments. This is similar to `taskexec` and can be used to upload configuration to services as part of deployments. It has the following specific options:

* `url`: HTTP(s) URL to call. Required. Variables can be used.
* `method`: HTTP method to use for the call, defaults to `GET`.
* `ignore_errors`: If set to true a non-200 result status code of the call will not be treated as a failure. Defaults to false.
* `body`: Allows to send a request body along. Optional. Has the following sub options:
  * `content`: Specifies the content of the request body.
  * `file`: Contents of this file will be used as request body. Is mutually exclusive with `content`. Variables can be used in the filename.
  * `render`: If set to true the request body from `file` or `content` will be rendered using mustache.
* `headers`: Allows to specify extra headers to send as key-value pairs (e.g. `Content-Type`). Optional. Variables can be used for both keys and values.

If the URL is neither a http nor a https url it wil be treated as a path behind the DC/OS adminrouter. When executing the call dcos-deploy will use its DC/OS credentials to authenticate against the adminrouter. So for example if a DC/OS cluster is reachable under `https://dcos.mycluster` and `url` is defined as `/service/myservice/reload` then dcos-deploy will call the URL `https://dcos.mycluster/service/myservice/reload`.

The same restrictions from `taskexec` in regards to state apply. As such this entity will run every time `apply` is called unless `when` and dependencies are used (see description for `taskexec` above for details).

### IAM Group

`type: iam_group` defines a group in the DC/OS IAM system. It has the following options:

* `name`: Name of the group. Required. Variables can be used.
* `description`: Description of the group. Required. Variables can be used.
* `permissions`: Permissions to give to the group. Dictionary. Key is the name of the permission (rid), value is a list of actions to allow. If a permission does not yet exist, it will be created. Variables can be used. See [Serviceaccount](#Serviceaccount) for an example.

### IAM User

`type: iam_user` defines a user in the DC/OS IAM system. It is similar to the `serviceaccount` but represents a normal user with username and password. It has the following options:

* `name`: Name of the user. Required. Variables can be used.
* `description`: Description of the user. Is represented as `Full name` in the DC/OS Admin UI. Required. Variables can be used.
* `update_password`: Cleartext password to set for the user. Required. Variables can be used.
* `update_password`: If set to true will always overwrite the current user password with the one specified here. Defaults to true.
* `groups`: List of groups the user should be added to. Optional. Variables can be used.
* `permissions`: Permissions to give to the user. Dictionary. Key is the name of the permission (rid), value is a list of actions to allow. If a permission does not yet exist, it will be created. Variables can be used. See [Serviceaccount](#Serviceaccount) for an example.

### Marathon Group

`type: marathon_group` allows to manage groups in marathon. For top-level groups in DC/OS `>=2.0` it can also manage group quotas.

* `name`: Name of the group. Required. Variables can be sued.
* `enforce_role`: Whether to enforce the group quota. Takes effect only for top-level groups. Defaults to False. In the DC/OS Admin UI values are seen as `Use Group Role` (True) and `Use Legacy Role` (False). Optional.
* `quota`: Optional
  * `cpus`: Maximum number of CPUs the role can use. Optional. Defaults to 0.
  * `mem`: Maximum memory the role can use. In MB. Optional. Defaults to 0.
  * `disk`: Maximum disk the role can use. In MB. Optional. Defaults to 0.
  * `gpus`: Maximum number of GPUs the role can use. Optional. Defaults to 0.

Restrictions:

* Removing quotas is currently not supported.
* Quotas are only supported for DC/OS `>=2.0`.

## Deployment process
When running the `apply` command dcos-deploy will first check all entities if they have changed. To do this it will first render all options and files using the provided variables, retrieve the currently running configurations from the DC/OS cluster using the specific APIs (e.g. get the app definition from marathon) and compare them. It will print a list of changes and ask for confirmation (unless `--yes` is used). If an entity needs to be created it will first recursively create any dependencies.
There is no guaranteed order of execution. Only that any defined dependencies will be created before the entity itsself is created.

The deployment process has some specific restrictions:
* Names/paths/ids may not be changed.
* Options files for frameworks, apps and jobs are not verified for structural correctness. If the new file is not accepted by the API an error will be thrown.
* For frameworks dcos-deploy does not verify beforehand if a version update is supported by the framework. If the framework does not accept the new version an error will be thrown.
* An already created `cert` entity will not be changed if the `dn` or `hostnames` fields change.
* Dependencies must be explicitly defined in the `dcos.yml`. Implicit dependencies (like a secret referenced in a marathon app) that are not explicitly stated are not honored by dcos-deploy.

### Deleting entities

dcos-deploy has support for deleting entities. You can use it to delete one or all entities defined (for example to clean up after tests). Do so use the command `dcos-deploy delete`. It will delete all entities defined in your configuration, honoring the dependencies (e.g. deleting a service before deleting the secret associated with it). If you only want to delete a specific entity use `--only <entity-name>`. All entities that have this entity as a dependency will also be deleted (e.g. if you delete a secret a marathon app depending on it will also be deleted). Check the dry-run output to make sure you don't unintentionally delete the wrong entity. The command is idempotent, so deleting an already deleted entity has no effect.
The delete command will not modify your configuration files. So to make sure that the deleted entity will not be recreated during the next `apply`-run, remove the entity definition from your yaml files.  


## Roadmap

* Support for creating and configuring kubernetes clusters
* Add as package to the Mesosphere universe for easy installation as a module for the dcos-cli
* Better and documented plugin support
* Provide some sort of verification for configurations


## Contributing
If you found a bug or have a feature request, please open an issue in Github.
