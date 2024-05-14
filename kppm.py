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
Loading the code itself


"""



import js
from os import listdir
from js import JSON # we'll need this to parse JS json later
import json # and we'll need this to parse json files for python
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

def flatten(t):
    result = []
    for item in t:
        if isinstance(item, (tuple, list)):
            result.extend(flatten(item))
        else:
            result.append(item)
    return tuple(result)


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
    kppmIndex = await request.json()
    writeFile("kppmIndex.json", pyJSON.stringify(kppmIndex))

async def loadDefinedDependencies():
    pass

# Initialize is called by require, or by the main.py of libraries
async def initialize(writeIndexToFilesystem=False):
    global fileClaims
    if initialized:
        return
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
    callerGlobals = False
    if (isinstance(args[-1], dict)):
        callerGlobals = args[-1]
        args = args[:-1]

    # Get required library objects from index    
    for requestedLibrary in args:
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
                        print("Library already loaded")
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
                                print(libraryFile)
                                fileClaims[requestedFilename] = str(requestedLibrary)
                                writeFile(requestedFilename, libraryFile)
        
        except Exception as e:
            log("Exception while loading " + str(requestedLibrary))
            print(e)
        # end import single dependency

    # Import the dependencies into globals if we have them

    # Write the fileClaims to filesystem so it persists reloads
    writeFile("fileClaims.json", json.dumps(fileClaims))


