# KPPM
Khan Python Package Manager. An idea for a python library indexer for https://www.khanacademy.org/computing/intro-to-python-fundamentals, using the API to allow requiring files from other programs.


# Idea
Create a single program who's spin-offs are indexed as libraries, and can be imported/required by name.

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
The username declaration is just to make things easy when someone changes their username.

## Pulling together
The spin-offs of the KPPM program will be automatically indexed for the latest updates by a github workflow.

Programs that update their libraries will have to be republished, as indexing will only pull in the latest libraries. Developing a library should be done as a spin-off of a second python whose spin-offs are not indexed to prevent unfinished libraries from being indexed.

Hopefully, this allows this to use little CPU power so it can all be done with a short github workflow to commit the data here. If it ever becomes too much for a workflow, I'll redesign it or host it myself.

Libraries will be indexed at a set time daily, so users can know what time they should release their library if they want it to be at the top of the HL at the same time it's in KPPM.

I'll probably also accept github commits to index libraries before the script itself runs.

Maybe I should do a bi-weekly scans to update the vote count of libraries?

## PyRequire
I've already designed a program capable of pulling in other programs into the current pyodide pseudo-filesystem, see https://www.khanacademy.org/python-program/pyrequire-v1/5920458708533248
