# KPPM
Khan Python Package Manager. An idea for a python library indexer for https://www.khanacademy.org/computing/intro-to-python-fundamentals, using the API to allow requiring files from other programs.


# Idea
Create a single program who's spin-offs are indexed as libraries, and can be required.

This way, instead of a user specifying  `await require(6536968313421824, "printutils")`, they can use `await require("bimum.printutils")`

Another idea is have something like `await searchPackage("print clear function")`, which will fuzzy search for matching libraries, much like yay, apt, winget, and other package managers (but a little more fuzzy because 13 yo's are bad at naming things).

## Format
Each program will have the following files:
- The standard main.py showing how to use the library
- The library file itself
- PyRequire utilities packaged into a single file to pull in the dependencies specified in the main.py.

No other files should be included, in order to keep things as clean as possible.

The main.py file must have headers akin to the following:
```cpp
#define author <username>
#define description My Cool Library that does cool stuff, yknow.
#define dependencies bimum.printutils, vexcess.zig
```


## PyRequire
I've already designed a program capable of pulling in other programs into the current pyodide pseudo-filesystem, see https://www.khanacademy.org/python-program/pyrequire-v1/5920458708533248
