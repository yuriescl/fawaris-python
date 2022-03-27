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
