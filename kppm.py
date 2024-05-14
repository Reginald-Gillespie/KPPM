"""
=============================
=Khan Python Package Manager=
=============================
For details: https://www.khanacademy.org/python-program/using-kppm/5200645795266560

This is the single KPPM utilities file needed to publish a library or use kppm.
"""











"""
Technical notes:
The filesystem persists through restarts, so we save json+python files here to minimize requests
At the very least, downloading and searching the KPPM database uses no "bypasses".
Loading other code files requires requesting an proxy service to grab the code and send it to us, 
 since KA's cors blocks us from dirrectly accessing the code ourselves.


"""




import js
from os import listdir
from js import JSON # we'll need this to parse JS json later
import json # and we'll need this to parse json files for python
import re
from math import sqrt
# from js import pyfetch #imported later
# from js import pyJSON #imported later


queries = {}
kppmIndex = {}
fileClaims = { # keep track of file names belonging to libraries to look for conflicts
    "main.py": "local.local"
}
initialized = False

# First, inject my pyfetch code - https://www.khanacademy.org/python-program/pyfetch-v1/5482075651751936
fetchInjector = """
// We need to convert from a python dict to json... in javascript, on a Proxy object... This was a pain.
function dict2Array(proxyDict) {
    // Check if this is a dict object, otherwise we can just return it as normal json
    if (proxyDict?.$$flags == 31) {
        const json = {}
        // debugger
        const keys = Array(...proxyDict.keys().mapping)
        keys.forEach( key => {
            value = proxyDict.get(key);
            // If this is another dict, convert it to an array too
            if (value?.$$flags) {
                // Now we know it's a proxy, it could be an array or json
                if (value.$$flags == 31) {
                    json[key] = dict2Array(value)
                }
                // Otherwise we'll treat it like an array (may need to add more types later, TODO)
                else {
                    json[key] = [...value]
                }
            } else {
                json[key] = value;
            }
        })
        return json;
    } else {
        return proxyDict;
    }
}

function noCorsFetch(url, options) {
    // Modify the URL to ignore cors
    noCorsURL = "https://corsproxy.io/?" + encodeURIComponent(url);

    jsOptions = dict2Array(options);

    return fetch(jsOptions?.disableCorsProxy ? url : noCorsURL, jsOptions);
}

// Add to global scope so we can extract it
this.pyfetch = noCorsFetch


function pyJSONStringify(dict) {
    json = dict2Array(dict);
    return JSON.stringify(json);
}

this.pyJSON = {
    "stringify": pyJSONStringify,
}

"""
js.eval(fetchInjector)

# Extract the new functions
from js import pyfetch
from js import pyJSON


# Now comes the fun stuff

# File utilities
def writeFile(name, content):
    content = str(content)
    file = open(name, "w")
    file.write(content)
    file.close()

def fileExists(name):
    return listdir("/home/pyodide").count(name) > 0

def readFile(name):
    file = open(name, "r")
    content = file.read()
    file.close()
    return content

# Other utilities
def log(message):
    print("\n!! KPPM - " + str(message) + " !!\n")

def jsonToDict(jsJson):
    return json.loads(pyJSON.stringify(jsJson))

def flatten(t):
    result = []
    for item in t:
        if isinstance(item, (tuple, list)):
            result.extend(flatten(item))
        else:
            result.append(item)
    return tuple(result)

def removeSuffixes(text):
    pattern = r'(ed|ing|s|able|or|ful|less|ly|ty)\b'
    words = text.split()
    processed_words = [re.sub(pattern, '', word) for word in words]
    result = ' '.join(processed_words)
    return result

def strictNormalize(query):
    # turned into smth for search queries, getting query and content as close as possible
    query = str(query)
    query = re.sub(r'[^A-Za-z\d]', ' ', query)
    query = re.sub(r'\s+', ' ', query)
    query = query.strip()
    query = query.lower()
    query = removeSuffixes(query)
    return query

async def getQueries():
    global queries
    if (fileExists("queries.json")):
        queries = JSON.parse(readFile("queries.json"))
        return
    request = await pyfetch("https://cdn.jsdelivr.net/gh/bhavjitChauhan/khan-api@safelist/queries.json", {"disableCorsProxy": True})
    queries = await request.json()
    writeFile("queries.json", pyJSON.stringify(queries))

async def getPythonProgramById(id=4893019299561472):
    response = await pyfetch('https://www.khanacademy.org/api/internal/graphql/pythonProgramQuery', { 
        "method": 'POST', 
        "body": pyJSON.stringify(
            { 
                "query": queries.pythonProgramQuery, 
                "variables": { 
                    "programId": id
                } 
            }) 
    })
    pythonProgramQuery = await response.json()
    program = pythonProgramQuery.data.program
    if program is None: print("WARNING - program " + str(id) + " is null")
    return program

async def requireByID(id, requiredFiles=None, useCache=True):
    # convert files to list if it isn't one already
    if isinstance(requiredFiles, str):
        requiredFiles = [requiredFiles]

    if requiredFiles is not None and useCache:
        # List the current loaded files
        loadedFiles = listdir("/home/pyodide")
        allFilesLoaded = True
        for file in requiredFiles:
            # if we found a file that is not loaded:
            if loadedFiles.count(file) == 0:
                allFilesLoaded = False
        if allFilesLoaded:
            return
    
    # parse filesnames - we'll add .py unless it already specifies the ending
    requiredFiles = [str(file)+".py" if file.count(".") == 0 else file for file in requiredFiles]
    
    program = await getPythonProgramById(id)
    if program is None: raise LookupError("Required import " + str(id) + " does not exist")

    # tfw a random property is a string instead of json like the rest of the KA api
    files = JSON.parse(program.latestRevision.code).files
    
    for file in files:
        if (requiredFiles is None and file!="main.py") or requiredFiles.count(file.filename) > 0:
            # We found the import file, now we write it to the pseudo filesystem
            output = open("/home/pyodide/"+file.filename, "w")
            output.write(file.code)
            output.close()

async def loadKPPMIndex():
    global kppmIndex
    if (fileExists("kppmIndex.json")):
        kppmIndex = json.loads(readFile("kppmIndex.json"))
        return
    request = await pyfetch("https://raw.githubusercontent.com/Reginald-Gillespie/KPPM/main/KPPMIndex.json", {"disableCorsProxy": True})
    kppmIndex = jsonToDict(await request.json())
    writeFile("kppmIndex.json", pyJSON.stringify(kppmIndex))

async def loadDefinedDependencies():
    # Now, we need to search for the file with #defined dependencies
    files = listdir()
    for file in files:
        fileContents = readFile(file)
        depMatches = re.search(r"^#\s*define\s+dependencies[ \t]*(.*)", fileContents, re.MULTILINE)
        packageNameMatch = re.search(r"^#\s*define\s+package[ \t]*(.*)$", fileContents, re.MULTILINE)  
        if depMatches and packageNameMatch:
            # If we found a file needing dependencies, import those. 
            # This will run on all library files we import but their
            #  files are cached so shouldn't be much overhead.
            dependencies = depMatches.group(1)
            dependencies = re.sub(r"\s+", '', dependencies).strip()
            dependencies = dependencies.split(",")            
            for dep in dependencies:
                if dep and dep != packageNameMatch.group(1): # prevent recursive error if infinitely requiring self
                    await require(dep)
        

# Initialize is called by require, or by the main.py of libraries
async def initialize(writeIndexToFilesystem=False):
    global fileClaims
    global initialized
    if initialized:
        return
    initialized = True
    # Fetch KA's latest queries
    await getQueries()
    # Load which files belong to which libraries
    if fileExists("fileClaims.json"):
        fileClaims = json.loads(readFile("fileClaims.json"))
    # Fetch library index
    await loadKPPMIndex()
    # Load dependencies if this is a library file that declares deps
    await loadDefinedDependencies()

async def require(*args):
    if not initialized:
        await initialize()
    # Start by flattening input so that it's just lib1,lib2,lib3,globals
    args = flatten(args)

    # Check if we have globals
    libraryFilenames = [] # for importing later
    callerGlobals = False
    if (isinstance(args[-1], dict)):
        callerGlobals = args[-1]
        args = args[:-1]

    # Get required library objects from index    
    for requestedLibrary in args:
        requestedLibrary = str(requestedLibrary).lower()
        try:
            requestedLibInfo = kppmIndex.get(requestedLibrary, False)
            # Make sure the library exists
            if not requestedLibInfo:
                log("Required library " + str(requestedLibrary) + " not found.")
            else:
                # Check if this library conflicts or is already loaded
                requestedFilename = requestedLibInfo["file"]
                if fileClaims.get(requestedFilename, False):
                    if (fileClaims[requestedFilename] == requestedLibrary):
                        # print("Library already loaded")
                        libraryFilenames.append(requestedFilename)
                        pass # Library is already loaded (by something else in the dependency tree)
                    else:
                        # Library file is taken by another library
                        log("Cannot load " + str(requestedLibrary) + ", conflicts with " + fileClaims[requestedFilename])
    
                else:
                    # No conflicts, continue
                    
                    # Start by importing all dependencies of the library
                    requestedLibDependencies = requestedLibInfo["dependsOn"]
                    # Prevent infinite dependency loop by depending on your own library
                    if requestedLibDependencies.count(requestedLibrary) > 0:
                        requestedLibDependencies.remove(requestedLibrary)
                    for dep in requestedLibDependencies:
                        await require(dep)

                    # That may have erred, we don't care (could still run, not my problem if it doesn't =P)
                    libraryProgramID =  requestedLibInfo["programID"]
                    program = await getPythonProgramById(libraryProgramID)
                    if program is None: 
                        log("Required library " + str(requestedLibrary) + " no longer exists on KA")
                    else:
                        # Program exists
                        libraryProgramFiles = json.loads(program.latestRevision.code)["files"]
                        # Create JSON map of files
                        libraryProgramFilesJSON = {}
                        for file in libraryProgramFiles:
                            libraryProgramFilesJSON[file["filename"]] = file["code"]
                        # Now get the library file from the map
                        libraryFile = libraryProgramFilesJSON[requestedFilename]
                        if not libraryFile:
                            log("File " + str(requestedFilename) + " not found in library " + str(requestedLibrary))

                        else:
                            # Library file exists, should be good to import it if it doesn't conflict with local files
                            localFiles = listdir()
                            if localFiles.count(requestedFilename) > 0:
                                log("Library file for " + str(requestedLibrary) + " conflicts with local file " + str(requestedFilename))

                            else:
                                # Finally time to write the dependency locally
                                fileClaims[requestedFilename] = str(requestedLibrary)
                                writeFile(requestedFilename, libraryFile)
                                libraryFilenames.append(requestedFilename)
        
        except Exception as e:
            log("Exception while loading " + str(requestedLibrary))
            # print(e)
        # end import single dependency

    # Write the fileClaims to filesystem so it persists reloads
    writeFile("fileClaims.json", json.dumps(fileClaims))

    # Import the dependencies into globals if we access
    if callerGlobals:
        libraryFilenames = [(file+" ")[:file.find(".")] for file in libraryFilenames]
        for library in libraryFilenames:
            module = __import__(library)
            callerGlobals[library] = module

async def search(query, minScore=0.01):
    # Needs to be awaiting simply so we can initialize
    if not initialized:
        await initialize()

    # Behind the scenes we'll filter the search and queries down to A-Za-z\d.
    # If you want a different search algorithm, just read kppmIndex.js from the filesystem and search it yourself
    query = set(strictNormalize(query).split())

    allLibraries = list(kppmIndex.keys())
    matches = []
    
    for library in allLibraries:
        libraryInfo = kppmIndex[library]
        description = set(strictNormalize(libraryInfo["description"]).split())

        # Go for text match
        intersection = query.intersection(description)
        union = query.union(description)
        matchScore = len(intersection) / len(union) # between 0 and 1

        # Weight matches by votes a little - we do want to avoid returning matches that only have a lot of votes.
        votesWeight = 0.15 # between 0 and 1
        votes = libraryInfo["votesAtLastIndex"]
        voteScore = votes / sqrt(150 + votes**2) # between 0 and 1
        
        if matchScore >= minScore:
            # we'll add vote weight to total weight only after checking match threshold
            totalScore = votesWeight*voteScore + (1-votesWeight)*matchScore
            matches.append([library, round(totalScore, 3)])

    # sort matches
    matches.sort(key=lambda m: m[1], reverse=True)
    
    return matches

async def lookup(name:str, returnAsJson=False):
    if not initialized:
        await initialize()
        
    package = kppmIndex.get(name, False)
    if not package:
        if returnAsJson:
            return {"not found":name}
        else:
            return "Package \"" + name + "\" was not found."
    else:
        # We found it:
        if returnAsJson:
            return package
        else:
            response = ""
            fields = list(package.keys())
            for field in fields:
                response += field + ": \"" + str(package[field]) + "\"\n"
            return response.strip()

async def shell():
    if not initialized:
        await initialize()
    print("===============")
    print("=KPPM Shell v1=")
    print("===============")
    print("Type HELP for help")
    while True:
        print("____")
        command = input("KPPM> ")
        print("")
        command = command.lower().strip()
        try:
            command = command.split()
            args = " ".join(command[1:])
            
            if len(command) == 0:
                print("Please send a command - type HELP for help")
            elif command[0] == "help":
                print("Available commands:")
                print("SEARCH <query>    - Search for a library")
                print("LOOKUP <library>  - Lookup library info by name")
                print("LOAD <library>    - Load a library file into the filesystem")
            elif len(command) == 1:
                print("Please send arguments with the command - type HELP for help")
            elif command[0] == "search":
                results = (await search(args))[:15] # limit to top 15
                if results:
                    output = ""
                    for result in results:
                        output += "Package: " + result[0] + "\nScore: " + str(result[1]) + "\n"
                    print(output)
                else:
                    print("No packages found for that query.")
            elif command[0] == "lookup":
                results = await lookup(args)
                print(results)
            elif command[0] == "load":
                await require(args)
                print("Attempted to load " + args)
            else:
                print("Unknown command - type HELP for help")
        except Exception as e:
            print(e)
            print("Error - type HELP for help")
    

