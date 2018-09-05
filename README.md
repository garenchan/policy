# Policy
A Policy library provides support for RBAC policy enforcement.

## Preface

When I used ``Flask`` to write a ``RESTful web service``, I didn't find a suitable extension to handle endpoints' permission control. Because I really like the permission control method of ``OpenStack`` services which based on a policy file. So I want to implement a more generic library similar to ``oslo.policy``.
