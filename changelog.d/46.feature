Reduce reliance on network in tests. Tests that require a network connection
can now be skipped via "-m 'not requires_network'". Other tests have mocked
connections.
