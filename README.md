# OpenStack Swift grok middleware

Provides a [grok](https://www.elastic.co/guide/en/logstash/current/plugins-filters-grok.html) functionality for reading files from Swift: Instead of receiving the raw files, when grokked the file will be sent as a series of JSONs, one JSON per grokked line.

Text blobs are assumed.

This is mostly useful for semantially reading log files that are stored on Swift.

## Installation

0) Clone this repo (`git clone https://github.com/synhershko/swift-middleware-grok.git`)

1) Run `sudo python setup.py install`

2) Alter your proxy-server.conf pipeline to have the grok middleware: add the `[filter:grok]` section and the grok filter itself as close to the proxy-server as possible

```
[filter:grok]
use = egg:grok#grok

[pipeline:main]
pipeline = catch_errors healthcheck proxy-logging cache grok container_sync bulk tempurl tempauth slo dlo staticweb proxy-logging  proxy-server
```

The relevant config files are in `/etc/swift/proxy-server/proxy-server.conf.d/20_settings.conf` or `/etc/swift/proxy-server.conf`, depending on your installation.

3) Restart proxy-server by running `sudo swift-init proxy-server restart`

4) Verify installation using `curl -XGET 'http://saio:8080/info' | grep grok`

## Quick local installation with vagrant

You can experiment with Swift locally pretty easily using vagrant. Follow the instructions at https://github.com/swiftstack/vagrant-swift-all-in-one. After you have cloned and ran `vagrant up`, do `vagrant ssh` follow the installation intructions above.

## Usage

```
vagrant@saio:~/$ echo "awesome" > test
vagrant@saio:~/$ swift upload test test
vagrant@saio:~/$ swift download test test -o -
awesome
vagrant@saio:~/$ swift download test test --header "grok-pattern":"%{WORD:word}" -o -
{"word": "awesome"}
Error downloading test: md5sum != etag, a2b0bd1d6a929129dd67d67f6ebd414f != 70c1db56f301c9e337b0099bd4174b28
```

The md5sum error is expected, as the file downloaded is a projection of the file being stored on Swift.

## Analysing own logs

A typical line from a Swift log looks something like this:

```
Dec 12 23:35:48 vagrant-ubuntu-trusty-64 proxy-server: 127.0.0.1 127.0.0.1 12/Dec/2015/23/35/48 GET /v1/AUTH_test/sample-log/sample-log HTTP/1.0 200 - python-swiftclient-2.6.1.dev26 AUTH_tk262ff273b... - 71 - tx6398b237474f4a69a9a37-00566caf54 - 0.0057 - - 1449963348.351684093 1449963348.357352018 0
```

The following grok pattern is going to extract the important bits:

```
%{SYSLOGTIMESTAMP:date} %{HOSTNAME:client} %{SYSLOGPROG:program} %{HOSTNAME} %{HOSTNAME} %{NOTSPACE} %{WORD:verb} %{NOTSPACE:request} (?: HTTP/%{NUMBER:httpversion})?|%{DATA:rawrequest}) %{NUMBER:response} - %{QS:agent} %{NOTSPACE} - %{NUMBER:client_etag} - %{NOTSPACE:transaction_id} - {NUMBER} - - {NUMBER:request_start_time} {NUMBER:request_end_time} {NUMBER:policy_index}
```

## Acknowledgments

Dr. Yaron Weinsberg from IBM Haifa Research Lab and Prof. Danny Dolev from the Hebrew University in Jerusalem for the idea and motivation. This middleware is being used in various projects for filtering and analysing client data.

John Dickinson, Director of Technology at SwiftStack and Project Technical Lead for OpenStack Object Storage (Swift), for providing helpful guidance.
