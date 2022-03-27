**This project is a Work In Progress. First version will be available soon.**

Async framework-agnostic Stellar Anchor interface.  
Each Stellar SEP is implemented as a class with abstract methods to be
overriden by any Anchor-specific implementation.  
This library on itself is not a working Stellar Anchor. It's meant to be
used as a base for Anchors to implement their logic.  

Facts about this library:
- Focused on being fully Async
- Not attached to any web framework
- Not attached to any database
- Requires an implementation on top of it

Who should use this library?
- Anchors looking for a reference on how to implement Stellar SEPs
- Anchors that don't wanna use other implementations (django-polaris, etc)

Implementations of this library:
- [fawaris-fastapi](https://github.com/yuriescl/fawaris-fastapi)

How to setup development environment:
```
poetry env use python3.7
poetry install
poetry shell
python -m unittest discover tests
```

Todo:
    - v1
        - locking
            - operation protection on transactions
            - add documentation regarding database locks
            - add documentation regarding database caching
        - fastapi add logging with transaction id
        - how to make it easy to migrate database?
        - fastapi handle sigint/sigterm
        - fawaris_fastapi handle stellar horizon errors when doing operations
            503
            400
            500
        - pydantic validators
            - prerequesites for each method call
            - stellar addresses
            - decimal places
        - pydantic types checking?
        - docstrings
        - add doc explaining motivations to build this software
        - add logging (use self.log)
        - add tables documentation
        - add API (use JWT + CORS)
            generate jwt similar to sep10
            https://github.com/aekasitt/fastapi-csrf-protect
        - check #TODO in code
    - v2
        - custodial wallet support
        - multisig support
        - SEP-24 validate SEP-10 token account
