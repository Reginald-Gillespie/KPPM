// File run by github workflow to update the ProgramIndex.json file.

// TODO:
// Currently, we don't worry about 429 (ratelimits).
// Hopefully, we won't hit any issues.

const fs = require("fs");
const fetch = require('node-fetch-commonjs');

const toIndex = "4783660036964352";
let queries = []
let runLog = "Run log for " + (new Date()).toGMTString() + "\n";

// We are going to read up until we find a program newer than this.
let lastReadDate = Number(fs.readFileSync("./system/lastReadDate.txt").toString());

// Load in the current index of programs.
let index = JSON.parse(fs.readFileSync("./KPPMIndex.json").toString());

// Index follows this format:
// [
//     "username.package": {
//         file: "filename.py",
//         description: "My cool library",
//         username: "username", // (at creation time)
//         nickname: "My Name",
//         title: "My Program",
//         kaid: "kaid_1234",
//         programID: 1234,
//         votesAtLastIndex: 5,
//         dependsOn: []
//     }
// ]

function sanitize(input) {
    input = String(input);
    input = input.match(/[\x20-\x7e]/g)?.join(""); // space through tilde
    return input?.trim() || "";
}

function limitLen(input, length, dotdotdot=false) {
    input = String(input)
    if (input.length > length) {
        input = dotdotdot ? input.substring(0, length-3) + "..." : input.substring(0, length)
    }
    return input;
}

function log(text) {
    text = String(text)
    console.log(text)
    runLog += text.trim() + "\n";
}

async function KAQuery(queryName, variables={}) {
    const query = queries[queryName];
    const response = await (await fetch("https://www.khanacademy.org/api/internal/graphql/"+queryName, {
        "method": 'POST',
        "body": JSON.stringify({
            "operationName": queryName,
            "query": query,
            "variables": variables
        }) 
    })).json();
    return response
}

async function getSpinOffs(cursor="") {
    const variables = {
        "sort": "RECENT",
        "from": {
            "kind": "PROGRAM",
            "programOrContentId": toIndex
        },
        "pageInfo": {
            "cursor": cursor,
            "itemsPerPage": 30  // I'd like to do more but I want this request to appear standard
        }
    }
    const response = await KAQuery("listTopProgramSpinoffs", variables)
    return response.data.listTopProgramSpinoffs;
}

async function getProgram(id) {
    const variables = {
        "programId": String(id)
    }
    const response = await KAQuery("pythonProgramQuery", variables)
    return response.data.program;
}

// Async function so we can await
(async function main(){
    startTime = Date.now();
    // Boilerplate done

    // First get latest queries
    queries = await (await fetch("https://cdn.jsdelivr.net/gh/bhavjitChauhan/khan-api@safelist/queries.json")).json()
    
    // Store the index we are currently searching
    let cursor = "";

    // Keep track of the newest spinoff we see to record.
    let newestProgram = lastReadDate;

    let indexing = true;
    while (indexing) {
        let response = await getSpinOffs(cursor);
        let programs = response.programs;
        cursor = response.cursor;
        
        // Index each of these programs
        for (var program of programs) {
            try {
                // Parse info from spinoff endpoint
                const kaid = program.authorKaid;
                const id = String(program.id);
                const votes = program.sumVotesIncremented;
                const nickname = sanitize(program.authorNickname);

                // Parse info from program query endpoint
                const programData = await getProgram(id);
                const code = programData.latestRevision.code;
                const createdAt = (new Date(programData.created)).getTime(); //ms
                const title = sanitize(programData.title);
                const profileRoot = programData.author.profileRoot; //ugh why is this the only way to get the username

                // Check if we've finished scanning yet.
                if (createdAt <= lastReadDate) {
                    indexing = false;
                    log("Found program older than last lookup.")
                    break;
                }
            
                // Real quick before we do anything that could throw an error, check if createdAt is after newestProgram
                if (createdAt > newestProgram) {
                    newestProgram = createdAt;
                }

                const username = sanitize(String(profileRoot).split("/")[2]).toLowerCase();
                if (!username || username.length < 2) {
                    log(id + " - User does not have a username");
                    throw Error("Invalid");
                }

                // Parse info from code itself
                const files = JSON.parse(code).files;
                const filesJSON = {}
                for (const file of files) {
                    filesJSON[sanitize(file.filename)] = file.code;
                }
                let mainPy = filesJSON["main.py"]
                mainPy = mainPy.replaceAll(/^\s+/gm, ""); //Remove whitespace from start of lines
                // mainPy = mainPy.replaceAll(/^[^#].*\n?/gm, ""); //Remove non comment lines
                // mainPy = mainPy.replaceAll(/(?<=^#)\s+/gm, ""); //Remove whitespace just after hash
                // mainPy.replaceAll(/\n?^(?!#define).*\n?/gm, ""); //Remove non-metadata lines
                // Maybe levenshtein the fields - but that's slow
                const claimedUsername = sanitize(mainPy.match(/(?<=#\s*define\s+author\s*).{0,40}/)[0]).toLowerCase();
                const packageName = sanitize(mainPy.match(/(?<=#\s*define\s+package\s*).{0,40}/)[0]).toLowerCase();
                const libraryFilename = sanitize(mainPy.match(/(?<=#\s*define\s+file\s*).{0,40}/)[0]).toLowerCase();
                const description = sanitize(limitLen( mainPy.match(/(?<=#\s*define\s+description\s*).{0,501}/)[0], 500, true));
                let dependencies = sanitize(mainPy.match(/(?<=#\s*define\s+dependencies\s*).{0,1000}/)[0]).toLowerCase();

                // Check the claimed username matches the real username
                // This check should be removed if this is ever used to index older libraries
                if (claimedUsername != username) {
                    log(id + ` - Library published under username it does not match (claimed to be ${claimedUsername}, is actually ${username})`);
                    throw Error("Invalid");
                }

                // Check they do have the library file they claim to have
                const libraryFile = filesJSON[libraryFilename];
                if (!libraryFile) {
                    log(id + ` - Program does not have file "${libraryFilename}"`);
                    throw Error("Invalid");
                }

                // Parse dependencies
                dependencies = dependencies.replaceAll(/\s/g, "");
                dependencies = dependencies.split(",");
                dependencies = dependencies.filter(d => d!="")
                dependencies.forEach(dep => {
                    if (dep.split(".").length !== 2) {
                        log(id + " - Invalid dependency, incorrect format")
                        throw Error("Invalid");
                    }
                    if (!dep.match(/^[a-z_\-\.]+$/)) {
                        log(id + " - Invalid dependency, invalid characters")
                        throw Error("Invalid");
                    }
                })
                if (!dependencies) {
                    dependencies = []
                }
                
                // Finally
                const KPPMPackageName = username + "." + packageName;

                // Check if this package already exists
                if (index[KPPMPackageName]) {
                    // If it exists, we can only modify it if it is owned by the same user (same kaid, not username)
                    // (otherwise someone might change usernames to hijack old packages)
                    if (index[KPPMPackageName].kaid != kaid) {
                        log(id + ` - original kaid "${index[KPPMPackageName].kaid} and new kaid ${kaid} do not match."`);
                        throw Error("Invalid")
                    }
                }

                // If we've hit no issues up to this point, we should be good to publish the package
                const KPPMPackageJson = {
                    "file": libraryFilename,
                    "description": description,
                    "username": username, // (at creation time)
                    "nickname": nickname,
                    "title": title,
                    "kaid": kaid,
                    "programID": id,
                    "votesAtLastIndex": +votes,
                    "dependsOn": dependencies
                }

                console.log(`No issues on ${id}, adding to index.`)
                index[KPPMPackageName] = KPPMPackageJson;

            } catch (e) {
                // don't trust KA's API to not be hackable into smth wonky
                log(e);
            }
        }

        // Check if we hit the end of available programs
        if (response.complete) {
            log("Received complete from api.")
            indexing = false
        }

        // If we are still indexing, we've updated the cursor, so we're free to continue te loop to the next cursor.
    }
    log(`---\nThis run took ${(Date.now() - startTime)/1000}ms`)

    // Finally write the updates
    fs.writeFileSync("./KPPMIndex.json", JSON.stringify(index))
    fs.writeFileSync("./system/log.txt", runLog)
    fs.writeFileSync("./system/lastReadDate.txt", String(newestProgram))
})()


