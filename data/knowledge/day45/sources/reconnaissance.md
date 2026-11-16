# Network reconnaissance

## Concept

Network service discovery seeks to learn which services are available on hosts. Connections to several destination ports can be consistent with discovery, and authorized maintenance can produce a similar pattern. The lab records accepted connections on instrumented services.

## Interpreting the lab evidence

The frozen network rule flags at least two distinct observed destination ports in a fixed 60-second window for the same run, source IP, and target. Repeated connections to one port do not satisfy the distinct port threshold. The lab logs cannot establish which closed ports were probed or whether any service was compromised.
